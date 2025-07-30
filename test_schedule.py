import requests

API_KEY = 'de9f5a7aa8b048539b69351e35e40dc9'
YEAR = 2025

url = f"https://api.sportsdata.io/v3/nfl/scores/json/Schedules/{YEAR}"
headers = {'Ocp-Apim-Subscription-Key': API_KEY}

response = requests.get(url, headers=headers)

if response.status_code == 200:
    schedule = response.json()
    for game in schedule[:5]:  # Show the first 5 games
        print(f"Week {game['Week']}: {game['AwayTeam']} @ {game['HomeTeam']} on {game['Date']}")
else:
    print("Error:", response.status_code)
    print(response.text)
