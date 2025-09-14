from django.core.management.base import BaseCommand
import requests
from picks.models import Game
from datetime import datetime, timezone

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
        
        self.stdout.write(f"Updating scores for week {week_number}...")
        
        if debug:
            self.stdout.write(f"API Key (first 8 chars): {API_KEY[:8]}...")
            self.stdout.write(f"Year: {YEAR}")

        # Use the working header format (you'll need to determine which one worked)
        url = f"https://api.sportsdata.io/v3/nfl/scores/json/ScoresByWeek/{YEAR}/{week_number}"
        headers = {'Ocp-Apim-Subscription-Key': API_KEY}  # Adjust based on what worked
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                self.stderr.write(f"API request failed with status {response.status_code}")
                self.stderr.write(f"Response: {response.text}")
                return
            
            data = response.json()
            self.stdout.write(f"Found {len(data)} games from API")
            
            # Debug: Show sample API data structure
            if debug and data:
                self.stdout.write(f"\nSample API data for first game:")
                sample_game = data[0]
                for key, value in sample_game.items():
                    self.stdout.write(f"  {key}: {value}")
            
            updated_count = 0
            errors = []
            
            for item in data:
                try:
                    game_key = item.get('GameKey')
                    
                    # Check for different possible score field names
                    home_score = item.get('HomeScore') or item.get('HomeTeamScore') or item.get('HomePoints')
                    away_score = item.get('AwayScore') or item.get('AwayTeamScore') or item.get('AwayPoints')
                    
                    status = item.get('Status', 'Scheduled')
                    is_closed = item.get('IsClosed', False)
                    
                    # Additional fields that might be useful
                    quarter = item.get('Quarter')
                    time_remaining = item.get('TimeRemainingDisplay') or item.get('TimeRemaining')
                    date_time = item.get('DateTime') or item.get('Date')
                    
                    if not game_key:
                        self.stderr.write(f"⚠ Skipping game with no GameKey")
                        continue

                    try:
                        game = Game.objects.get(api_id=game_key)
                        updated = False
                        old_values = {}

                        # Store old values for comparison
                        old_values['home_score'] = game.home_score
                        old_values['away_score'] = game.away_score
                        old_values['status'] = game.status
                        old_values['is_closed'] = game.is_closed

                        # Update home score (handle None values properly)
                        if home_score is not None and game.home_score != home_score:
                            game.home_score = home_score
                            updated = True

                        # Update away score (handle None values properly)
                        if away_score is not None and game.away_score != away_score:
                            game.away_score = away_score
                            updated = True

                        # Enhanced status mapping
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
                            game.status = mapped_status
                            updated = True

                        if game.is_closed != is_closed:
                            game.is_closed = is_closed
                            updated = True

                        if updated:
                            game.save()
                            updated_count += 1

                            # Detailed logging of what changed
                            changes = []
                            if old_values['home_score'] != game.home_score:
                                changes.append(f"Home: {old_values['home_score']} → {game.home_score}")
                            if old_values['away_score'] != game.away_score:
                                changes.append(f"Away: {old_values['away_score']} → {game.away_score}")
                            if old_values['status'] != game.status:
                                changes.append(f"Status: {old_values['status']} → {game.status}")
                            if old_values['is_closed'] != game.is_closed:
                                changes.append(f"Closed: {old_values['is_closed']} → {game.is_closed}")

                            change_summary = ", ".join(changes)
                            
                            if home_score is not None and away_score is not None:
                                winner = "TIE" if home_score == away_score else (
                                    game.home_team.short_name if home_score > away_score 
                                    else game.away_team.short_name
                                )
                                self.stdout.write(
                                    f"✓ Updated: {game.away_team.short_name} @ {game.home_team.short_name} "
                                    f"-> {away_score}-{home_score} ({winner}) [{mapped_status}]"
                                )
                                if debug:
                                    self.stdout.write(f"   Changes: {change_summary}")
                                    if quarter:
                                        self.stdout.write(f"   Quarter: {quarter}, Time: {time_remaining}")
                            else:
                                self.stdout.write(f"✓ Updated: {game} -> {change_summary}")
                        
                        elif debug:
                            # Show games that didn't need updates
                            self.stdout.write(f"- No update needed: {game.away_team.short_name} @ {game.home_team.short_name} "
                                            f"({away_score}-{home_score}) [{mapped_status}]")

                    except Game.DoesNotExist:
                        error_msg = f"Game {game_key} not found in database"
                        errors.append(error_msg)
                        self.stderr.write(f"⚠ {error_msg}")
                        continue
                        
                except Exception as e:
                    error_msg = f"Error processing game {item.get('GameKey', 'unknown')}: {e}"
                    errors.append(error_msg)
                    self.stderr.write(f"❌ {error_msg}")
                    if debug:
                        import traceback
                        self.stderr.write(traceback.format_exc())

            # Summary
            self.stdout.write(f"\n📊 Summary for Week {week_number}:")
            self.stdout.write(f"   • Total games from API: {len(data)}")
            self.stdout.write(f"   • Games updated: {updated_count}")
            self.stdout.write(f"   • Errors: {len(errors)}")
            
            if errors and debug:
                self.stdout.write(f"\n❌ Errors encountered:")
                for error in errors:
                    self.stdout.write(f"   • {error}")
                    
        except requests.RequestException as e:
            self.stderr.write(f"❌ API request failed: {e}")
        except Exception as e:
            self.stderr.write(f"❌ Unexpected error: {e}")
            if debug:
                import traceback
                self.stderr.write(traceback.format_exc())