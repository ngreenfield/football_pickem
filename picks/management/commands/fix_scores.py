from django.core.management.base import BaseCommand
import requests
from picks.models import Game

API_KEY = '6f3556c6beb94c71a62b02d1f0960704'


class Command(BaseCommand):
    help = "Fix NFL scores for a given week"

    def add_arguments(self, parser):
        parser.add_argument(
            'week_number',
            nargs='?',
            type=int,
            default=1,
            help='Week number to update scores for'
        )
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Enable detailed debugging output'
        )

    def handle(self, *args, **options):
        week = options['week_number']
        debug = options['debug']
        self.stdout.write(f"Fetching NFL scores for Week {week}...")

        url = f"https://api.sportsdata.io/v3/nfl/scores/json/ScoresByWeek/2025/{week}"
        headers = {'Ocp-Apim-Subscription-Key': API_KEY}

        if debug:
            self.stdout.write(f"DEBUG: Request URL = {url}")

        try:
            response = requests.get(url, headers=headers, timeout=30)

            if response.status_code != 200:
                self.stderr.write(f"API Error: {response.status_code}")
                self.stderr.write(response.text)
                return

            data = response.json()
            self.stdout.write(f"✓ Found {len(data)} games from API.")

            updated_count = 0

            for item in data:
                game_key = item.get('GameKey')
                home_score = item.get('HomeScore')
                away_score = item.get('AwayScore')
                home_team = item.get('HomeTeam')
                away_team = item.get('AwayTeam')
                status = item.get('Status')
                is_closed = item.get('IsClosed', False)

                if not game_key:
                    if debug:
                        self.stderr.write("⚠ Skipping item with no GameKey")
                    continue

                if debug:
                    self.stdout.write(f"DEBUG: Processing {away_team} @ {home_team} (GameKey: {game_key})")

                try:
                    game = Game.objects.get(api_id=game_key)
                    updated = False

                    if game.home_score != home_score:
                        game.home_score = home_score
                        updated = True

                    if game.away_score != away_score:
                        game.away_score = away_score
                        updated = True

                    new_status = 'FINAL' if status == 'Final' else game.status
                    if game.status != new_status:
                        game.status = new_status
                        updated = True

                    if game.is_closed != is_closed:
                        game.is_closed = is_closed
                        updated = True

                    if updated:
                        game.save()
                        updated_count += 1
                        self.stdout.write(f"✓ Updated: {away_team} @ {home_team} — {away_score}-{home_score}")

                except Game.DoesNotExist:
                    self.stderr.write(f"⚠ Game not found in DB: {away_team} @ {home_team} (GameKey: {game_key})")

            self.stdout.write(f"\n✅ Finished updating Week {week}.")
            self.stdout.write(f"✓ Total games fetched: {len(data)}")
            self.stdout.write(f"✓ Total games updated: {updated_count}")

        except Exception as e:
            self.stderr.write(f"❌ Error during update: {e}")
