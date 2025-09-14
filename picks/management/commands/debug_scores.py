from django.core.management.base import BaseCommand
import requests
import json

API_KEY = '6f3556c6beb94c71a62b02d1f0960704'
YEAR = 2025


class Command(BaseCommand):
    help = "Debug API response to see what's wrong with the scores"

    def add_arguments(self, parser):
        parser.add_argument(
            'week_number',
            nargs='?',
            type=int,
            default=2,
            help='Week number to check'
        )
        
    def handle(self, *args, **options):
        week_number = options['week_number']
        
        url = f"https://api.sportsdata.io/v3/nfl/scores/json/ScoresByWeek/{YEAR}/{week_number}"
        headers = {'Ocp-Apim-Subscription-Key': API_KEY}
        
        self.stdout.write(f"🔍 Debugging API response for Week {week_number}, Year {YEAR}")
        self.stdout.write(f"URL: {url}")
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                self.stderr.write(f"❌ API request failed with status {response.status_code}")
                self.stderr.write(f"Response: {response.text}")
                return
            
            data = response.json()
            self.stdout.write(f"✅ API returned {len(data)} games")
            
            # Show the raw JSON for first few games
            self.stdout.write(f"\n🔍 RAW API DATA (first 3 games):")
            self.stdout.write("=" * 80)
            
            for i, game in enumerate(data[:3]):
                self.stdout.write(f"\n--- Game {i+1} ---")
                self.stdout.write(json.dumps(game, indent=2))
            
            # Show all scores in a clean format
            self.stdout.write(f"\n📊 ALL SCORES FOR WEEK {week_number}:")
            self.stdout.write("=" * 80)
            
            for game in data:
                away_team = game.get('AwayTeam', 'UNK')
                home_team = game.get('HomeTeam', 'UNK')
                away_score = game.get('AwayScore')
                home_score = game.get('HomeScore')
                status = game.get('Status', 'UNK')
                date_time = game.get('DateTime', 'UNK')
                game_key = game.get('GameKey', 'UNK')
                
                self.stdout.write(f"{away_team} @ {home_team}: {away_score}-{home_score} [{status}]")
                self.stdout.write(f"  GameKey: {game_key}")
                self.stdout.write(f"  DateTime: {date_time}")
                self.stdout.write()
            
            # Check if we're getting the right year/week
            self.stdout.write(f"\n🚨 POTENTIAL ISSUES:")
            
            if any(game.get('HomeScore', 0) > 60 for game in data if game.get('HomeScore')):
                self.stdout.write("❌ Scores are unrealistically high (>60) - might be wrong data")
            
            # Check dates
            game_dates = [game.get('DateTime') for game in data if game.get('DateTime')]
            if game_dates:
                self.stdout.write(f"📅 Game dates in response: {set(str(d)[:10] for d in game_dates)}")
            
            # Check if this is actually 2024 data instead of 2025
            self.stdout.write(f"\n🔄 Let's also try 2024 data to compare...")
            
            url_2024 = f"https://api.sportsdata.io/v3/nfl/scores/json/ScoresByWeek/2024/{week_number}"
            response_2024 = requests.get(url_2024, headers=headers, timeout=30)
            
            if response_2024.status_code == 200:
                data_2024 = response_2024.json()
                self.stdout.write(f"✅ 2024 Week {week_number} returned {len(data_2024)} games")
                
                self.stdout.write(f"\n📊 2024 SCORES FOR COMPARISON:")
                for game in data_2024[:5]:  # Just first 5
                    away_team = game.get('AwayTeam', 'UNK')
                    home_team = game.get('HomeTeam', 'UNK')
                    away_score = game.get('AwayScore')
                    home_score = game.get('HomeScore')
                    status = game.get('Status', 'UNK')
                    
                    self.stdout.write(f"{away_team} @ {home_team}: {away_score}-{home_score} [{status}]")
            else:
                self.stdout.write(f"❌ 2024 request failed: {response_2024.status_code}")
                
        except Exception as e:
            self.stderr.write(f"❌ Error: {e}")
            import traceback
            self.stderr.write(traceback.format_exc())