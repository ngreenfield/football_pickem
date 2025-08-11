import requests
from dateutil import parser
from django.core.management.base import BaseCommand
from picks.models import Game, Team, Week
from django.utils.timezone import make_aware

API_KEY = 'de9f5a7aa8b048539b69351e35e40dc9'
YEAR = 2025
API_URL = f"https://api.sportsdata.io/v3/nfl/scores/json/Schedules/{YEAR}"

class Command(BaseCommand):
    help = "Loads the football schedule into the database"

    def handle(self, *args, **kwargs):
        headers = {'Ocp-Apim-Subscription-Key': API_KEY}
        response = requests.get(API_URL, headers=headers)
        data = response.json()

        for item in data:
            home_team, _ = Team.objects.get_or_create(
                short_name=item['HomeTeam'],
                defaults={'name': item['HomeTeam']}
            )
            away_team, _ = Team.objects.get_or_create(
                short_name=item['AwayTeam'],
                defaults={'name': item['AwayTeam']}
            )

            date_str = item.get('Date')
            if not date_str:
                self.stdout.write(self.style.WARNING(f"Missing date for game {item.get('GameKey')}"))
                continue
            game_date = parser.parse(date_str)

            if game_date.tzinfo is None:
                game_date = make_aware(game_date)

            week_number = item.get('Week')
            week = None
            if week_number:
                week, _ = Week.objects.get_or_create(number=week_number)

            Game.objects.update_or_create(
                home_team=home_team,
                away_team=away_team,
                game_date=game_date,
                defaults={'week': week}
            )

        self.stdout.write(self.style.SUCCESS("Schedule loaded successfully"))