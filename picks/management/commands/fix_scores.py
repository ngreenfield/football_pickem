import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import requests
from picks.models import Game

API_KEY = 'de9f5a7aa8b048539b69351e35e40dc9'

# Get Week 1 scores using the CORRECT endpoint
url = "https://api.sportsdata.io/v3/nfl/scores/json/ScoresByWeek/2025/1"
headers = {'Ocp-Apim-Subscription-Key': API_KEY}
response = requests.get(url, headers=headers)
data = response.json()

# Update your games
for item in data:
    game_key = item.get('GameKey')
    home_score = item.get('HomeScore')
    away_score = item.get('AwayScore')
    
    try:
        game = Game.objects.get(api_id=game_key)
        game.home_score = home_score
        game.away_score = away_score
        game.status = 'FINAL' if item.get('Status') == 'Final' else game.status
        game.is_closed = item.get('IsClosed', False)
        game.save()
        print(f"Updated: {game} -> {away_score}-{home_score}")
    except Game.DoesNotExist:
        print(f"Game {game_key} not found")