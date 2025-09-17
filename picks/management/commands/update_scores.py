from django.core.management.base import BaseCommand
import requests
from picks.models import Game
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
            dest='debug',
            help='Enable debugging output'
        )
        parser.add_argument(
            '--final-only',
            action='store_true',
            dest='final_only',
            help='Only update final/closed games'
        )

    def get_score(self, score_value):
        """Convert API score to integer, handling None/empty values"""
        if score_value is None or score_value == '' or score_value == 'null':
            return 0
        try:
            return int(float(str(score_value)))
        except (ValueError, TypeError):
            return 0

    def handle(self, *args, **options):
        week_number = options['week_number']
        debug = options.get('debug', False)
        final_only = options.get('final_only', False)

        self.stdout.write(f"📡 Updating scores for Week {week_number}")
        
        url = f"https://api.sportsdata.io/v3/nfl/scores/json/ScoresByWeek/{YEAR}/{week_number}"
        headers = {'Ocp-Apim-Subscription-Key': API_KEY}

        try:
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                self.stderr.write(f"❌ API request failed: {response.status_code}")
                return

            data = response.json()
            if not data:
                self.stdout.write("⚠️ No games returned from API")
                return

            self.stdout.write(f"✅ Found {len(data)} games from API")
            
            if debug:
                self.stdout.write("\n🔍 API Response Sample:")
                if data:
                    sample = data[0]
                    self.stdout.write(f"GameKey: {sample.get('GameKey')}")
                    self.stdout.write(f"HomeTeam: {sample.get('HomeTeam')} - Score: {sample.get('HomeTeamScore')}")
                    self.stdout.write(f"AwayTeam: {sample.get('AwayTeam')} - Score: {sample.get('AwayTeamScore')}")
                    self.stdout.write(f"Status: {sample.get('Status')} - IsClosed: {sample.get('IsClosed')}")

            updated_count = 0
            skipped_count = 0
            not_found_count = 0

            # Status mapping for consistency
            status_mapping = {
                'Scheduled': 'SCHEDULED',
                'InProgress': 'INPROGRESS', 
                'In Progress': 'INPROGRESS',
                'Halftime': 'INPROGRESS',
                '1st Quarter': 'INPROGRESS',
                '2nd Quarter': 'INPROGRESS', 
                '3rd Quarter': 'INPROGRESS',
                '4th Quarter': 'INPROGRESS',
                'Overtime': 'INPROGRESS',
                'Final': 'FINAL',
                'F': 'FINAL', 
                'Final OT': 'FINAL',
                'F/OT': 'FINAL',
                'Cancelled': 'CANCELLED',
                'Postponed': 'POSTPONED',
            }

            for item in data:
                try:
                    game_key = item.get('GameKey')
                    if not game_key:
                        continue

                    status = item.get('Status', 'Scheduled')
                    is_closed = item.get('IsClosed', False)
                    
                    # Skip non-final games if requested
                    if final_only and not is_closed:
                        skipped_count += 1
                        continue

                    # Extract scores - try primary fields first
                    home_score = self.get_score(item.get('HomeTeamScore'))
                    away_score = self.get_score(item.get('AwayTeamScore'))
                    
                    # Fallback to secondary fields if primary are zero/null
                    if home_score == 0 and item.get('HomeScore') is not None:
                        home_score = self.get_score(item.get('HomeScore'))
                    if away_score == 0 and item.get('AwayScore') is not None:
                        away_score = self.get_score(item.get('AwayScore'))

                    if debug:
                        self.stdout.write(f"\n🔍 {game_key}: Raw scores - Home: {item.get('HomeTeamScore')}, Away: {item.get('AwayTeamScore')}")
                        self.stdout.write(f"   Final scores - Home: {home_score}, Away: {away_score}")

                    try:
                        game = Game.objects.get(api_id=game_key)
                        
                        # Always show first few games for debugging
                        if updated_count + not_found_count < 3 and not debug:
                            self.stdout.write(f"🔍 Found game: {game.away_team.short_name} @ {game.home_team.short_name} ({game.away_score}-{game.home_score})")
                            self.stdout.write(f"   API scores: {away_score}-{home_score}, Status: {status}")
                            
                    except Game.DoesNotExist:
                        if debug:
                            self.stdout.write(f"⚠️ Game {game_key} not found in database")
                        not_found_count += 1
                        continue

                    # Check if updates are needed
                    mapped_status = status_mapping.get(status, 'SCHEDULED')
                    
                    needs_update = (
                        game.home_score != home_score or 
                        game.away_score != away_score or
                        game.status != mapped_status or
                        game.is_closed != is_closed
                    )

                    if needs_update:
                        game.home_score = home_score
                        game.away_score = away_score
                        game.status = mapped_status
                        game.is_closed = is_closed
                        game.save()
                        
                        updated_count += 1
                        
                        # Determine winner
                        if home_score > away_score:
                            winner = game.home_team.short_name
                        elif away_score > home_score:
                            winner = game.away_team.short_name
                        else:
                            winner = "TIE"
                        
                        status_icon = "🏁" if is_closed else ("⏱️" if mapped_status == 'INPROGRESS' else "📅")
                        self.stdout.write(
                            f"✅ {game.away_team.short_name} @ {game.home_team.short_name} "
                            f"→ {away_score}-{home_score} | {winner} [{mapped_status}] {status_icon}"
                        )
                    elif debug:
                        self.stdout.write(f"🔍 No update needed: {game.away_team.short_name} @ {game.home_team.short_name}")

                except Exception as e:
                    self.stderr.write(f"❌ Error processing {item.get('GameKey', 'unknown')}: {e}")

            # Summary
            summary = f"\n📊 Summary: {updated_count} updated, {not_found_count} not found"
            if final_only:
                summary += f", {skipped_count} skipped"
            self.stdout.write(summary)

        except requests.RequestException as e:
            self.stderr.write(f"❌ API request failed: {e}")
        except Exception as e:
            self.stderr.write(f"❌ Unexpected error: {e}")