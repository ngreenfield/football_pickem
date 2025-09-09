import requests
import json

API_KEY = 'de9f5a7aa8b048539b69351e35e40dc9'
YEAR = 2025

# Different endpoints to try
endpoints = {
    'Schedules': f"https://api.sportsdata.io/v3/nfl/scores/json/Schedules/{YEAR}",
    'Scores by Week 1': f"https://api.sportsdata.io/v3/nfl/scores/json/ScoresByWeek/{YEAR}/1",
    'Games by Week 1': f"https://api.sportsdata.io/v3/nfl/scores/json/GamesByWeek/{YEAR}/1",
    'Current Season Scores': f"https://api.sportsdata.io/v3/nfl/scores/json/Scores/{YEAR}",
    'Live Scores': f"https://api.sportsdata.io/v3/nfl/scores/json/ScoresLive",
    'Completed Games': f"https://api.sportsdata.io/v3/nfl/scores/json/GamesByDate/{YEAR}-09-07",  # Date of week 1 games
}

def test_endpoint(name, url):
    """Test a specific endpoint"""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"URL: {url}")
    print('='*60)
    
    headers = {'Ocp-Apim-Subscription-Key': API_KEY}
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Total items: {len(data) if isinstance(data, list) else 'Not a list'}")
            
            if isinstance(data, list) and data:
                # Show first item structure
                first_item = data[0]
                print("\nFirst item keys:")
                for key in sorted(first_item.keys()):
                    value = first_item[key]
                    if isinstance(value, str) and len(value) > 50:
                        value = value[:50] + "..."
                    print(f"  {key}: {value}")
                
                # Look for games with scores
                games_with_scores = [item for item in data 
                                   if item.get('HomeScore') is not None or 
                                      item.get('AwayScore') is not None]
                
                print(f"\nItems with scores: {len(games_with_scores)}")
                
                if games_with_scores:
                    print("First few items with scores:")
                    for i, game in enumerate(games_with_scores[:3]):
                        home_team = game.get('HomeTeam', 'Unknown')
                        away_team = game.get('AwayTeam', 'Unknown')
                        home_score = game.get('HomeScore', 'N/A')
                        away_score = game.get('AwayScore', 'N/A')
                        status = game.get('Status', 'Unknown')
                        week = game.get('Week', 'Unknown')
                        
                        print(f"  {i+1}. Week {week}: {away_team} @ {home_team}")
                        print(f"     Score: {away_score} - {home_score} ({status})")
                
            elif isinstance(data, dict):
                print("Response is a dictionary, not a list")
                print("Keys:", list(data.keys()))
                
        elif response.status_code == 401:
            print("ERROR: Unauthorized - Check your API key")
        elif response.status_code == 403:
            print("ERROR: Forbidden - Your plan may not include this endpoint")
        elif response.status_code == 404:
            print("ERROR: Not Found - Endpoint may not exist or no data available")
        else:
            print(f"ERROR: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            
    except requests.RequestException as e:
        print(f"Network error: {e}")
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

def main():
    print("Testing different SportsData.io endpoints to find scores...")
    print(f"Using API Key: {API_KEY[:10]}...")
    
    for name, url in endpoints.items():
        test_endpoint(name, url)
    
    print(f"\n{'='*60}")
    print("SUMMARY")
    print('='*60)
    print("Check which endpoints returned data with scores.")
    print("If none have scores, it might be:")
    print("1. API plan limitations")
    print("2. Scores not yet available from the provider")
    print("3. Need different endpoint or parameters")

if __name__ == "__main__":
    main()