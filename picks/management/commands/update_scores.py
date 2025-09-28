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

    def get_score(self, *score_values):
        """Convert API score to integer, trying multiple values in order"""
        for score_value in score_values:
            if score_value is not None and score_value != '' and score_value != 'null':
                try:
                    # Handle both string and numeric types
                    score = float(str(score_value))
                    return int(score) if score >= 0 else 0
                except (ValueError, TypeError):
                    continue
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
                if debug:
                    self.stderr.write(f"Response: {response.text}")
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
                    self.stdout.write(f"Full sample data: {json.dumps(sample, indent=2)}")

            updated_count = 0
            skipped_count = 0
            not_found_count = 0

            # Enhanced status mapping
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
                'OT': 'INPROGRESS',
                'Final': 'FINAL',
                'F': 'FINAL', 
                'Final OT': 'FINAL',
                'F/OT': 'FINAL',
                'Cancelled': 'CANCELLED',
                'Postponed': 'POSTPONED',
                'Suspended': 'POSTPONED',
            }

            for item in data:
                try:
                    game_key = item.get('GameKey')
                    if not game_key:
                        if debug:
                            self.stdout.write(f"⚠️ Skipping item with no GameKey: {item}")
                        continue

                    status = item.get('Status', 'Scheduled')
                    is_closed = bool(item.get('IsClosed', False))
                    
                    # Skip non-final games if requested
                    if final_only and not is_closed:
                        skipped_count += 1
                        if debug:
                            self.stdout.write(f"⏭️ Skipping non-final game: {game_key}")
                        continue

                    # Try multiple score fields in order of preference
                    home_score = self.get_score(
                        item.get('HomeTeamScore'),
                        item.get('HomeScore'), 
                        item.get('HomeTeamMoneyLine'),
                        item.get('HomePointsScored')
                    )
                    
                    away_score = self.get_score(
                        item.get('AwayTeamScore'),
                        item.get('AwayScore'),
                        item.get('AwayTeamMoneyLine'), 
                        item.get('AwayPointsScored')
                    )

                    if debug:
                        self.stdout.write(f"\n🔍 {game_key} Score Analysis:")
                        self.stdout.write(f"   HomeTeamScore: {item.get('HomeTeamScore')}")
                        self.stdout.write(f"   HomeScore: {item.get('HomeScore')}")
                        self.stdout.write(f"   AwayTeamScore: {item.get('AwayTeamScore')}")
                        self.stdout.write(f"   AwayScore: {item.get('AwayScore')}")
                        self.stdout.write(f"   Final parsed - Home: {home_score}, Away: {away_score}")
                        self.stdout.write(f"   Status: {status}, IsClosed: {is_closed}")

                    try:
                        game = Game.objects.get(api_id=game_key)
                    except Game.DoesNotExist:
                        if debug:
                            self.stdout.write(f"⚠️ Game {game_key} not found in database")
                        not_found_count += 1
                        continue

                    # Map status with fallback
                    mapped_status = status_mapping.get(status, 'SCHEDULED')
                    
                    # For closed games, ensure status is FINAL
                    if is_closed and mapped_status != 'CANCELLED' and mapped_status != 'POSTPONED':
                        mapped_status = 'FINAL'

                    # Check if updates are needed
                    needs_update = (
                        game.home_score != home_score or 
                        game.away_score != away_score or
                        game.status != mapped_status or
                        game.is_closed != is_closed
                    )

                    if debug or updated_count + not_found_count < 5:
                        self.stdout.write(f"🔍 {game.away_team.short_name} @ {game.home_team.short_name}")
                        self.stdout.write(f"   DB: {game.away_score}-{game.home_score} [{game.status}] Closed: {game.is_closed}")
                        self.stdout.write(f"   API: {away_score}-{home_score} [{mapped_status}] Closed: {is_closed}")
                        self.stdout.write(f"   Update needed: {needs_update}")

                    if needs_update:
                        old_home = game.home_score
                        old_away = game.away_score
                        old_status = game.status
                        
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
                            f"✅ {game.away_team.short_name} @ {game.home_team.short_name}"
                        )
                        self.stdout.write(
                            f"   {old_away}-{old_home} [{old_status}] → {away_score}-{home_score} [{mapped_status}] | {winner} {status_icon}"
                        )
                        
                        if debug:
                            self.stdout.write(f"   Game saved with ID: {game.id}")

                except Exception as e:
                    self.stderr.write(f"❌ Error processing {item.get('GameKey', 'unknown')}: {e}")
                    if debug:
                        import traceback
                        self.stderr.write(traceback.format_exc())

            # Summary
            summary = f"\n📊 Summary: {updated_count} updated, {not_found_count} not found in DB"
            if final_only:
                summary += f", {skipped_count} skipped (non-final)"
            self.stdout.write(summary)
            
            if not_found_count > 0:
                self.stdout.write("💡 Tip: Run with --debug to see which games weren't found")

        except requests.RequestException as e:
            self.stderr.write(f"❌ API request failed: {e}")
            if debug:
                import traceback
                self.stderr.write(traceback.format_exc())
        except Exception as e:
            self.stderr.write(f"❌ Unexpected error: {e}")
            if debug:
                import traceback
                self.stderr.write(traceback.format_exc())