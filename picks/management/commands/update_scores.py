#!/usr/bin/env python
"""
Quick script to update NFL scores using the correct SportsData.io endpoint
"""
import os
import sys
import django
import requests
from dateutil import parser

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from picks.models import Game, Team, Week
from django.utils.timezone import make_aware

API_KEY = 'de9f5a7aa8b048539b69351e35e40dc9'
YEAR = 2025

def update_week_scores(week_number):
    """Update scores for a specific week"""
    print(f"Updating scores for Week {week_number}...")
    
    # Use the ScoresByWeek endpoint that actually has scores
    url = f"https://api.sportsdata.io/v3/nfl/scores/json/ScoresByWeek/{YEAR}/{week_number}"
    headers = {'Ocp-Apim-Subscription-Key': API_KEY}
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"API Error: {response.status_code}")
            print(response.text)
            return
        
        data = response.json()
        print(f"Found {len(data)} games for Week {week_number}")
        
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
                # Find the game in our database
                game = Game.objects.get(api_id=game_key)
                
                # Update if scores have changed or game status changed
                updated = False
                if game.home_score != home_score:
                    game.home_score = home_score
                    updated = True
                    
                if game.away_score != away_score:
                    game.away_score = away_score  
                    updated = True
                
                # Map status
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
                        print(f"✓ Updated: {game.away_team.short_name} @ {game.home_team.short_name} "
                              f"-> {away_score}-{home_score} ({winner}) [{mapped_status}]")
                    else:
                        print(f"✓ Updated status: {game} -> {mapped_status}")
                
            except Game.DoesNotExist:
                print(f"⚠ Game {game_key} not found in database")
                continue
        
        print(f"\nUpdated {updated_count} games for Week {week_number}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

def main():
    if len(sys.argv) > 1:
        try:
            week = int(sys.argv[1])
            update_week_scores(week)
        except ValueError:
            print("Usage: python quick_score_update.py <week_number>")
            print("Example: python quick_score_update.py 1")
    else:
        print("Usage: python quick_score_update.py <week_number>")
        print("Example: python quick_score_update.py 1")

if __name__ == "__main__":
    main()