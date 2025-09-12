import requests

API_KEY = '6f3556c6beb94c71a62b02d1f0960704'
url = "https://api.sportsdata.io/v3/nfl/scores/json/AreGamesInProgress"
headers = {'Ocp-Apim-Subscription-Key': API_KEY}

response = requests.get(url, headers=headers)
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")