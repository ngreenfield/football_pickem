from django.core.management.base import BaseCommand
import requests
from picks.models import Game

API_KEY = '6f3556c6beb94c71a62b02d1f0960704'
YEAR = 2025


class Command(BaseCommand):
    help = "Update NFL scores"

    def add_arguments(self, parser):
        parser.add_argument(
            'week_number',
            nargs='?',           # Make it optional
            type=int,
            default=1,           # Default week number if none provided
            help='Week number to update scores for'
        )
        
    def handle(self, *args, **options):
        week_number = options['week_number']
        self.stdout.write(f"Updating scores for week {week_number}...")
        
        # Debug info
        self.stdout.write(f"API Key (first 8 chars): {API_KEY[:8]}...")
        self.stdout.write(f"API Key length: {len(API_KEY)}")
        self.stdout.write(f"Year: {YEAR}")

        url = f"https://api.sportsdata.io/v3/nfl/scores/json/ScoresByWeek/{YEAR}/{week_number}"
        
        # Try multiple header approaches
        header_options = [
            {'Ocp-Apim-Subscription-Key': API_KEY},
            {'X-API-Key': API_KEY},
            {'Authorization': f'Bearer {API_KEY}'},
            {'apikey': API_KEY},
        ]
        
        for i, headers in enumerate(header_options, 1):
            self.stdout.write(f"\n--- Attempt {i}: {list(headers.keys())[0]} ---")
            self.stdout.write(f"URL: {url}")
            self.stdout.write(f"Headers: {headers}")
            
            try:
                response = requests.get(url, headers=headers, timeout=30)
                self.stdout.write(f"Status Code: {response.status_code}")
                
                if response.status_code == 200:
                    self.stdout.write("✅ SUCCESS! This header format works!")
                    data = response.json()
                    self.stdout.write(f"Found {len(data)} games")
                    
                    # Continue with your original logic here...
                    updated_count = 0
                    for item in data:
                        game_key = item.get('GameKey')
                        home_score = item.get('HomeScore')
                        away_score = item.get('AwayScore')
                        status = item.get('Status', 'Scheduled')
                        is_closed = item.get('IsClosed', False)

                        if not game_key:
                            continue

                        try:
                            game = Game.objects.get(api_id=game_key)
                            updated = False

                            if game.home_score != home_score:
                                game.home_score = home_score
                                updated = True

                            if game.away_score != away_score:
                                game.away_score = away_score
                                updated = True

                            status_mapping = {
                                'Scheduled': 'SCHEDULED',
                                'InProgress': 'INPROGRESS',
                                'In Progress': 'INPROGRESS',
                                'Final': 'FINAL',
                                'F': 'FINAL',
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

                                if home_score is not None and away_score is not None:
                                    winner = "TIE" if home_score == away_score else (
                                        game.home_team.short_name if home_score > away_score 
                                        else game.away_team.short_name
                                    )
                                    self.stdout.write(f"✓ Updated: {game.away_team.short_name} @ {game.home_team.short_name} "
                                                      f"-> {away_score}-{home_score} ({winner}) [{mapped_status}]")
                                else:
                                    self.stdout.write(f"✓ Updated status: {game} -> {mapped_status}")

                        except Game.DoesNotExist:
                            self.stderr.write(f"⚠ Game {game_key} not found in database")
                            continue

                    self.stdout.write(f"\nUpdated {updated_count} games for Week {week_number}")
                    return  # Exit after successful attempt
                    
                else:
                    self.stdout.write(f"❌ Failed with status {response.status_code}")
                    self.stdout.write(f"Response text: {response.text[:500]}")  # First 500 chars
                    
            except Exception as e:
                self.stdout.write(f"❌ Exception: {e}")
        
        # Also try with query parameter
        self.stdout.write(f"\n--- Query Parameter Attempt ---")
        query_url = f"{url}?key={API_KEY}"
        self.stdout.write(f"URL: {query_url}")
        
        try:
            response = requests.get(query_url, timeout=30)
            self.stdout.write(f"Status Code: {response.status_code}")
            if response.status_code == 200:
                self.stdout.write("✅ SUCCESS! Query parameter works!")
            else:
                self.stdout.write(f"❌ Failed: {response.text[:500]}")
        except Exception as e:
            self.stdout.write(f"❌ Exception: {e}")
        
        self.stdout.write("\n🔍 If none worked, the issue might be:")
        self.stdout.write("1. API key is actually invalid despite what they said")
        self.stdout.write("2. Your IP/Heroku's IP is blocked")
        self.stdout.write("3. Different endpoint URL needed")
        self.stdout.write("4. API key needs to be activated or has expired")
        self.stdout.write(f"Full API Key: {API_KEY}")