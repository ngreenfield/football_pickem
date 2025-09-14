from django.core.management.base import BaseCommand
import requests
from picks.models import Game
from datetime import datetime
import json

API_KEY = '6f3556c6beb94c71a62b02d1f0960704'
YEAR = 2025


class Command(BaseCommand):
    help = "Update NFL scores"

    def add_arguments(self, parser):
        parser.add_argument(
            'week_number',
            nargs='?',
            type=int,
            default=1,
            help='Week number to update scores for'
        )
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Enable detailed debugging output'
        )

    def handle(self, *args, **options):
        week_number = options['week_number']
        debug = options.get('debug', False)

        self.stdout.write(f"📡 Updating scores for Week {week_number} (Year {YEAR})")

        url = f"https://api.sportsdata.io/v3/nfl/scores/json/ScoresByWeek/{YEAR}/{week_number}"
        headers = {'Ocp-Apim-Subscription-Key': API_KEY}

        try:
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code != 200:
                self.stderr.write(f"❌ API request failed with status {response.status_code}")
                self.stderr.write(f"Response: {response.text}")
                return

            data = response.json()
            self.stdout.write(f"✅ Found {len(data)} games from API")

            if debug and data:
                self.stdout.write(f"🔍 Sample game data:")
                self.stdout.write(json.dumps(data[0], indent=2))

            updated_count = 0
            errors = []

            for item in data:
                try:
                    game_key = item.get('GameKey')
                    if not game_key:
                        self.stderr.write("⚠ Skipping game with no GameKey")
                        continue

                    # Prefer the most accurate score fields
                    home_score = item.get('HomeTeamScore') or item.get('HomeScore')
                    away_score = item.get('AwayTeamScore') or item.get('AwayScore')

                    home_team_api = item.get('HomeTeam')
                    away_team_api = item.get('AwayTeam')

                    status = item.get('Status', 'Scheduled')
                    is_closed = item.get('IsClosed', False)
                    last_updated = item.get('Updated') or item.get('LastUpdated')

                    # Skip non-final games
                    if not is_closed or status not in ['Final', 'Final OT', 'F', 'F/OT']:
                        if debug:
                            self.stdout.write(f"⏭ Skipping non-final game {game_key} — status: {status}, is_closed: {is_closed}")
                        continue

                    try:
                        game = Game.objects.get(api_id=game_key)
                    except Game.DoesNotExist:
                        self.stderr.write(f"⚠ Game {game_key} not found in DB — API match: {away_team_api} @ {home_team_api}")
                        continue

                    # Sanity check
                    if debug:
                        self.stdout.write(f"🔄 Matching: API: {away_team_api} @ {home_team_api} | DB: {game.away_team.short_name} @ {game.home_team.short_name}")
                        if last_updated:
                            self.stdout.write(f"   ↳ LastUpdated: {last_updated}")

                    updated = False
                    changes = []

                    # Score updates
                    if home_score is not None and home_score != game.home_score:
                        changes.append(f"Home: {game.home_score} → {home_score}")
                        game.home_score = home_score
                        updated = True

                    if away_score is not None and away_score != game.away_score:
                        changes.append(f"Away: {game.away_score} → {away_score}")
                        game.away_score = away_score
                        updated = True

                    # Status mapping
                    status_mapping = {
                        'Scheduled': 'SCHEDULED',
                        'InProgress': 'INPROGRESS',
                        'In Progress': 'INPROGRESS',
                        'Halftime': 'INPROGRESS',
                        'Final': 'FINAL',
                        'F': 'FINAL',
                        'Final OT': 'FINAL',
                        'F/OT': 'FINAL',
                        'Cancelled': 'CANCELLED',
                        'Postponed': 'POSTPONED',
                        'Suspended': 'SUSPENDED',
                    }
                    mapped_status = status_mapping.get(status, 'SCHEDULED')

                    if game.status != mapped_status:
                        changes.append(f"Status: {game.status} → {mapped_status}")
                        game.status = mapped_status
                        updated = True

                    if game.is_closed != is_closed:
                        changes.append(f"Closed: {game.is_closed} → {is_closed}")
                        game.is_closed = is_closed
                        updated = True

                    if updated:
                        game.save()
                        updated_count += 1

                        winner = "TIE"
                        if home_score is not None and away_score is not None:
                            if home_score > away_score:
                                winner = game.home_team.short_name
                            elif away_score > home_score:
                                winner = game.away_team.short_name

                        self.stdout.write(
                            f"✅ Updated: {game.away_team.short_name} @ {game.home_team.short_name} "
                            f"→ {away_score}-{home_score} | Winner: {winner} [{mapped_status}]"
                        )
                        if debug and changes:
                            self.stdout.write(f"   ↳ Changes: {', '.join(changes)}")
                    elif debug:
                        self.stdout.write(
                            f"🔍 No update needed: {game.away_team.short_name} @ {game.home_team.short_name} "
                            f"({away_score}-{home_score}) [{mapped_status}]"
                        )

                except Exception as e:
                    error_msg = f"❌ Error processing game {item.get('GameKey', 'unknown')}: {e}"
                    errors.append(error_msg)
                    self.stderr.write(error_msg)
                    if debug:
                        import traceback
                        self.stderr.write(traceback.format_exc())

            # Summary
            self.stdout.write("\n📊 Update Summary:")
            self.stdout.write(f" • Games processed: {len(data)}")
            self.stdout.write(f" • Games updated: {updated_count}")
            self.stdout.write(f" • Errors: {len(errors)}")

            if debug and errors:
                self.stdout.write("\n❌ Errors encountered:")
                for err in errors:
                    self.stdout.write(f" • {err}")

        except requests.RequestException as e:
            self.stderr.write(f"❌ API request failed: {e}")

        except Exception as e:
            self.stderr.write(f"❌ Unexpected error: {e}")
            if debug:
                import traceback
                self.stderr.write(traceback.format_exc())
