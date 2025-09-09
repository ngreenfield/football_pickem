from django.core.management.base import BaseCommand
import requests
from picks.models import Game
import sys

API_KEY = 'de9f5a7aa8b048539b69351e35e40dc9'
YEAR = 2025


class Command(BaseCommand):
    help = "Update NFL scores"

    def add_arguments(self, parser):
        parser.add_argument(
            'week_number',
            nargs='?',           # Make it optional
            type=int,
            default=1,           # Default week number if none provided
            help='Week number to update scores for'
        )
        
    def handle(self, *args, **options):
        week_number = options['week_number']
        self.stdout.write(f"Updating scores for week {week_number}...")

        url = f"https://api.sportsdata.io/v3/nfl/scores/json/ScoresByWeek/{YEAR}/{week_number}"
        headers = {'Ocp-Apim-Subscription-Key': API_KEY}

        try:
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code != 200:
                self.stderr.write(f"API Error: {response.status_code}")
                self.stderr.write(response.text)
                return

            data = response.json()
            self.stdout.write(f"Found {len(data)} games for Week {week_number}")

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
                    game = Game.objects.get(api_id=game_key)
                    updated = False

                    if game.home_score != home_score:
                        game.home_score = home_score
                        updated = True

                    if game.away_score != away_score:
                        game.away_score = away_score
                        updated = True

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
                            self.stdout.write(f"✓ Updated: {game.away_team.short_name} @ {game.home_team.short_name} "
                                              f"-> {away_score}-{home_score} ({winner}) [{mapped_status}]")
                        else:
                            self.stdout.write(f"✓ Updated status: {game} -> {mapped_status}")

                except Game.DoesNotExist:
                    self.stderr.write(f"⚠ Game {game_key} not found in database")
                    continue

            self.stdout.write(f"\nUpdated {updated_count} games for Week {week_number}")

        except Exception as e:
            self.stderr.write(f"Error: {e}")
