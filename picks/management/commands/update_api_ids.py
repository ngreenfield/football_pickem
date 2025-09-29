from django.core.management.base import BaseCommand
import requests
from picks.models import Game

class Command(BaseCommand):
    help = "Update Game.api_id by matching teams with ESPN API game IDs for a given week"

    def add_arguments(self, parser):
        parser.add_argument(
            'week_number',
            type=int,
            help='Week number to update API IDs for'
        )

    def handle(self, *args, **options):
        week_number = options['week_number']
        year = 2025
        season_type = 2  # Regular season

        url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates={year}&seasontype={season_type}&week={week_number}"

        # Map full ESPN team names to your DB abbreviations (add more as needed)
        full_name_to_abbr = {
            "Washington Commanders": "WAS",
            # Add other mappings here if you find mismatches
        }

        try:
            response = requests.get(url, timeout=30)
            if response.status_code != 200:
                self.stderr.write(f"❌ ESPN API request failed with status {response.status_code}")
                return

            data = response.json()
            espn_games = data.get('events', [])
            if not espn_games:
                self.stdout.write("⚠️ No ESPN games found for this week")
                return

            db_games = Game.objects.filter(week__number=week_number)
            if not db_games.exists():
                self.stderr.write(f"❌ No games found in database for week {week_number}")
                return

            espn_game_map = {}  # Key: (away_short, home_short), Value: espn_game_id

            def get_team_abbr(team_data):
                abbr = team_data['team'].get('abbreviation')
                if abbr:
                    return abbr.upper()
                full_name = team_data['team'].get('displayName') or team_data['team'].get('shortDisplayName')
                return full_name_to_abbr.get(full_name, full_name.upper())

            for eg in espn_games:
                competition = eg.get('competitions', [])[0]
                competitors = competition.get('competitors', [])

                away_team = next((c for c in competitors if c['homeAway'] == 'away'), None)
                home_team = next((c for c in competitors if c['homeAway'] == 'home'), None)

                if not away_team or not home_team:
                    continue

                away_short = get_team_abbr(away_team)
                home_short = get_team_abbr(home_team)

                espn_game_map[(away_short, home_short)] = eg['id']

            updated_count = 0

            for game in db_games:
                key = (game.away_team.short_name.upper(), game.home_team.short_name.upper())

                if key in espn_game_map:
                    espn_id = espn_game_map[key]
                    if game.api_id != espn_id:
                        game.api_id = espn_id
                        game.save()
                        updated_count += 1
                        self.stdout.write(f"✅ Updated API ID for {game.away_team} @ {game.home_team} to {espn_id}")
                else:
                    self.stdout.write(f"⚠️ No ESPN match found for {game.away_team} @ {game.home_team}")

            self.stdout.write(f"\n🎉 Updated API IDs for {updated_count} games in Week {week_number}")
