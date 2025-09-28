from django.core.management.base import BaseCommand
import requests
from picks.models import Game

class Command(BaseCommand):
    help = "Update scores for games from ESPN API"

    def add_arguments(self, parser):
        parser.add_argument(
            'week_number',
            type=int,
            help='Week number to update scores for'
        )

    def handle(self, *args, **options):
        week_number = options['week_number']
        year = 2025
        season_type = 2
        url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates={year}&seasontype={season_type}&week={week_number}"

        try:
            response = requests.get(url, timeout=30)
            if response.status_code != 200:
                self.stderr.write(f"❌ ESPN API request failed with status {response.status_code}")
                return

            data = response.json()
            espn_games = data.get('events', [])
            if not espn_games:
                self.stdout.write("⚠️ No ESPN games found for this week")
                return

            db_games = Game.objects.filter(week__number=week_number)
            if not db_games.exists():
                self.stderr.write(f"❌ No games found in database for week {week_number}")
                return

            updated_count = 0

            for db_game in db_games:
                if not db_game.api_id:
                    # Skip games without ESPN ID mapped
                    continue

                espn_game = next((eg for eg in espn_games if eg.get('id') == db_game.api_id), None)
                if not espn_game:
                    self.stdout.write(f"⚠️ No ESPN data found for game {db_game}")
                    continue

                competitions = espn_game.get('competitions', [])
                if not competitions:
                    self.stdout.write(f"⚠️ No competitions found for ESPN game {db_game.api_id}")
                    continue

                competition = competitions[0]

                # NEW: get status from competition, not header
                status_obj = competition.get("status")
                self.stdout.write(f"📝 DEBUG: game {db_game.api_id} status_obj = {status_obj}")

                status_name = None
                status_id = None

                if status_obj:
                    status_type = status_obj.get("type")
                    if status_type and isinstance(status_type, dict):
                        # Use the 'name' or 'description' from the type for display
                        status_name_raw = status_type.get("name") or status_type.get("description") or "UNKNOWN"
                        # Clean the status name by removing any prefix like "STATUS_"
                        status_name = status_name_raw.replace("STATUS_", "").upper()
                        status_id = status_type.get("id")
                    else:
                        status_name = status_obj.get("name") or status_obj.get("description") or "UNKNOWN"
                        status_id = status_obj.get("id")
                else:
                    status_name = "SCHEDULED"
                    status_id = None

                # Mark game as closed if final or canceled
                if status_name in ["FINAL", "CANCELED", "POSTPONED"]:
                    db_game.is_closed = True
                else:
                    db_game.is_closed = False

                # Update scores
                home_score = None
                away_score = None
                competitors = competition.get('competitors', [])
                for comp in competitors:
                    team = comp.get('team', {})
                    score = comp.get('score')
                    if comp.get('homeAway') == 'home':
                        home_score = int(score) if score is not None else None
                    elif comp.get('homeAway') == 'away':
                        away_score = int(score) if score is not None else None

                # Update game object
                db_game.home_score = home_score
                db_game.away_score = away_score

                if status_name:
                    db_game.status = status_name.upper()
                else:
                    db_game.status = 'SCHEDULED'

                # Mark game closed if final or canceled
                if status_name and status_name.upper() in ['FINAL', 'POSTPONED', 'CANCELED']:
                    db_game.is_closed = True
                else:
                    db_game.is_closed = False

                db_game.save()
                updated_count += 1

                self.stdout.write(
                    f"✅ Updated {db_game.away_team.short_name} @ {db_game.home_team.short_name}: "
                    f"{away_score if away_score is not None else 0} - {home_score if home_score is not None else 0} "
                    f"({db_game.status})"
                )

            self.stdout.write(f"\n🎉 Updated scores for {updated_count} games in Week {week_number}")

        except Exception as e:
            self.stderr.write(f"❌ Exception occurred: {e}")
            import traceback
            traceback.print_exc()
