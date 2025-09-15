from django.core.management.base import BaseCommand
import requests
from picks.models import Game

API_KEY = '6f3556c6beb94c71a62b02d1f0960704'


class Command(BaseCommand):
    help = "Fix NFL scores for Week 1"

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
        self.stdout.write("Fixing Week 1 scores...")
        
        # Get Week 1 scores using the CORRECT endpoint
        url = "https://api.sportsdata.io/v3/nfl/scores/json/ScoresByWeek/2025/1"
        headers = {'Ocp-Apim-Subscription-Key': API_KEY}
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                self.stderr.write(f"API Error: {response.status_code}")
                self.stderr.write(response.text)
                return
                
            data = response.json()
            self.stdout.write(f"Found {len(data)} games")
            
            updated_count = 0
            
            # Update your games
            for item in data:
                game_key = item.get('GameKey')
                home_score = item.get('HomeScore')
                away_score = item.get('AwayScore')
                
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
                        
                    # Update status
                    new_status = 'FINAL' if item.get('Status') == 'Final' else game.status
                    if game.status != new_status:
                        game.status = new_status
                        updated = True
                        
                    # Update is_closed
                    is_closed = item.get('IsClosed', False)
                    if game.is_closed != is_closed:
                        game.is_closed = is_closed
                        updated = True
                    
                    if updated:
                        game.save()
                        updated_count += 1
                        self.stdout.write(f"✓ Updated: {game} -> {away_score}-{home_score}")
                        
                except Game.DoesNotExist:
                    self.stderr.write(f"⚠ Game {game_key} not found")
                    
            self.stdout.write(f"\nUpdated {updated_count} games")
            
        except Exception as e:
            self.stderr.write(f"Error: {e}")