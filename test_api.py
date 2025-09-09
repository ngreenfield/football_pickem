import requests
import json
from datetime import datetime

# Your API configuration
API_KEY = 'de9f5a7aa8b048539b69351e35e40dc9'
YEAR = 2025
API_URL = f"https://api.sportsdata.io/v3/nfl/scores/json/Schedules/{YEAR}"

def test_api_connection():
    """Test the API connection and show response structure"""
    print("Testing SportsData.io API connection...")
    print(f"URL: {API_URL}")
    print(f"Year: {YEAR}")
    print("-" * 50)
    
    headers = {'Ocp-Apim-Subscription-Key': API_KEY}
    
    try:
        response = requests.get(API_URL, headers=headers, timeout=30)
        
        print(f"Response Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print("-" * 50)
        
        if response.status_code != 200:
            print(f"ERROR: API request failed")
            print(f"Response text: {response.text}")
            return
            
        data = response.json()
        print(f"Total games found: {len(data)}")
        
        if not data:
            print("No games returned from API!")
            return
            
        # Show first game structure
        print("\n=== FIRST GAME STRUCTURE ===")
        first_game = data[0]
        for key, value in sorted(first_game.items()):
            print(f"{key:20}: {value}")
        
        # Look for games with scores
        games_with_scores = [g for g in data if g.get('HomeScore') is not None]
        print(f"\n=== GAMES WITH SCORES ===")
        print(f"Games with scores: {len(games_with_scores)}")
        
        if games_with_scores:
            print("\nFirst 5 games with scores:")
            for i, game in enumerate(games_with_scores[:5]):
                week = game.get('Week', 'Unknown')
                home_team = game.get('HomeTeam', 'Unknown')
                away_team = game.get('AwayTeam', 'Unknown')
                home_score = game.get('HomeScore', 'N/A')
                away_score = game.get('AwayScore', 'N/A')
                status = game.get('Status', 'Unknown')
                is_closed = game.get('IsClosed', 'Unknown')
                game_key = game.get('GameKey', 'Unknown')
                
                print(f"  {i+1}. Week {week}: {away_team} @ {home_team}")
                print(f"     Score: {away_score} - {home_score}")
                print(f"     Status: {status}, Closed: {is_closed}")
                print(f"     GameKey: {game_key}")
                print()
        else:
            print("No games with scores found!")
            
        # Check for recent games
        print("=== RECENT GAMES (Last 10) ===")
        # Sort by date if available
        try:
            sorted_games = sorted(data, key=lambda x: x.get('Date') or x.get('DateTime') or '', reverse=True)
            recent_games = sorted_games[:10]
            
            for i, game in enumerate(recent_games):
                date = game.get('Date') or game.get('DateTime') or 'Unknown'
                week = game.get('Week', 'Unknown')
                home_team = game.get('HomeTeam', 'Unknown')
                away_team = game.get('AwayTeam', 'Unknown')
                status = game.get('Status', 'Unknown')
                
                print(f"  {i+1}. Week {week} - {date}")
                print(f"     {away_team} @ {home_team} ({status})")
        except Exception as e:
            print(f"Error sorting games: {e}")
        
        # Check specific week if you want
        week_to_check = 1  # Change this to check a specific week
        week_games = [g for g in data if g.get('Week') == week_to_check]
        print(f"\n=== WEEK {week_to_check} GAMES ===")
        print(f"Games in week {week_to_check}: {len(week_games)}")
        
        for game in week_games:
            home_team = game.get('HomeTeam', 'Unknown')
            away_team = game.get('AwayTeam', 'Unknown')
            home_score = game.get('HomeScore')
            away_score = game.get('AwayScore')
            status = game.get('Status', 'Unknown')
            date = game.get('Date') or game.get('DateTime') or 'Unknown'
            
            score_str = f"{away_score}-{home_score}" if home_score is not None else "No score"
            print(f"  {away_team} @ {home_team}: {score_str} ({status}) - {date}")
        
    except requests.RequestException as e:
        print(f"Network error: {e}")
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        print(f"Response content: {response.text[:1000]}")
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_api_connection()