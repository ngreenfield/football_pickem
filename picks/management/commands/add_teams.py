import requests
from django.core.management.base import BaseCommand
from picks.models import Team

API_KEY = 'de9f5a7aa8b048539b69351e35e40dc9'
TEAMS_API_URL = 'https://api.sportsdata.io/v3/nfl/scores/json/Teams'

class Command(BaseCommand):
    help = "Fetches all NFL teams from the API and adds/updates them in the database"

    def handle(self, *args, **options):
        self.stdout.write("Fetching teams from API...")
        
        headers = {'Ocp-Apim-Subscription-Key': API_KEY}
        response = requests.get(TEAMS_API_URL, headers=headers)
        
        if response.status_code != 200:
            self.stdout.write(self.style.ERROR(f"API request failed with status {response.status_code}"))
            return
        
        teams_data = response.json()
        self.stdout.write(f"Found {len(teams_data)} teams in API response")
        
        teams_created = 0
        teams_updated = 0
        
        for item in teams_data:
            try:
                short_name = item.get('Key')
                full_name = item.get('FullName') or item.get('Name') or short_name
                
                if not short_name:
                    self.stdout.write(self.style.WARNING(f"Skipping team with missing key: {item}"))
                    continue
                
                team, created = Team.objects.update_or_create(
                    short_name=short_name,
                    defaults={'name': full_name}
                )
                
                if created:
                    teams_created += 1
                    self.stdout.write(f"Created team: {team}")
                else:
                    teams_updated += 1
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing team {item}: {e}"))
                continue
        
        self.stdout.write(
            self.style.SUCCESS(
                f"\nSummary:\n"
                f"  Teams created: {teams_created}\n"
                f"  Teams updated: {teams_updated}\n"
                f"  Total processed: {teams_created + teams_updated}"
            )
        )
