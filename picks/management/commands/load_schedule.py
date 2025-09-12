import requests
from dateutil import parser
from django.core.management.base import BaseCommand
from picks.models import Game, Team, Week
from django.utils.timezone import make_aware

API_KEY = '6f3556c6beb94c71a62b02d1f0960704'
YEAR = 2025
API_URL = f"https://api.sportsdata.io/v3/nfl/scores/json/Schedules/{YEAR}"

class Command(BaseCommand):
    help = "Loads the football schedule and updates scores from the API"

    def add_arguments(self, parser):
        parser.add_argument(
            '--scores-only',
            action='store_true',
            help='Only update scores for existing games, don\'t create new games',
        )
        parser.add_argument(
            '--week',
            type=int,
            help='Only update games for a specific week number',
        )

    def handle(self, *args, **options):
        self.stdout.write("Fetching data from API...")
        
        headers = {'Ocp-Apim-Subscription-Key': API_KEY}
        response = requests.get(API_URL, headers=headers)
        
        if response.status_code != 200:
            self.stdout.write(
                self.style.ERROR(f"API request failed: {response.status_code}")
            )
            return
            
        data = response.json()
        self.stdout.write(f"Found {len(data)} games in API response")
        
        # Filter by week if specified
        if options['week']:
            data = [game for game in data if game.get('Week') == options['week']]
            self.stdout.write(f"Filtered to {len(data)} games for week {options['week']}")
        
        games_created = 0
        games_updated = 0
        scores_updated = 0
        bye_weeks_skipped = 0
        
        for item in data:
            try:
                game_key = item.get('GameKey')
                week_number = item.get('Week')
                home_team_code = item.get('HomeTeam')
                away_team_code = item.get('AwayTeam')
                
                # Skip bye week games - these aren't real games
                if (away_team_code == 'BYE' or 
                    home_team_code == 'BYE' or 
                    not game_key or 
                    not week_number or
                    item.get('GlobalGameID') == 0):
                    
                    if away_team_code == 'BYE' or home_team_code == 'BYE':
                        bye_weeks_skipped += 1
                        self.stdout.write(
                            self.style.WARNING(f"Skipping bye week for {home_team_code}")
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(f"Skipping game with missing essential data: {item}")
                        )
                    continue
                
                # Get or create teams
                home_team, _ = Team.objects.get_or_create(
                    short_name=home_team_code,
                    defaults={'name': item.get('HomeTeamName', home_team_code)}
                )
                away_team, _ = Team.objects.get_or_create(
                    short_name=away_team_code,
                    defaults={'name': item.get('AwayTeamName', away_team_code)}
                )

                # Parse game date
                date_str = item.get('Date') or item.get('DateTime')
                if not date_str:
                    self.stdout.write(
                        self.style.WARNING(f"Missing date for game {game_key}")
                    )
                    continue
                    
                game_date = parser.parse(date_str)
                if game_date.tzinfo is None:
                    game_date = make_aware(game_date)

                # Get or create week
                week, _ = Week.objects.get_or_create(number=week_number)

                # Map API status to our status choices
                api_status = item.get('Status', 'Scheduled')
                status_mapping = {
                    'Scheduled': 'SCHEDULED',
                    'InProgress': 'INPROGRESS', 
                    'Final': 'FINAL',
                    'F': 'FINAL',  # Sometimes it's just 'F'
                    'Postponed': 'POSTPONED',
                    'Canceled': 'CANCELED',
                    'Cancelled': 'CANCELED',
                }
                status = status_mapping.get(api_status, 'SCHEDULED')
                
                # Get scores (will be None if not available)
                home_score = item.get('HomeScore')
                away_score = item.get('AwayScore')
                
                # Handle is_closed - ensure it's never None for database constraint
                is_closed = item.get('IsClosed')
                if is_closed is None:
                    is_closed = status == 'FINAL'  # Default based on game status
                
                # Skip creating/updating if scores-only mode and this is a new game
                if options['scores_only']:
                    try:
                        game = Game.objects.get(api_id=game_key)
                        # Update existing game
                        updated = False
                        if game.home_score != home_score or game.away_score != away_score:
                            game.home_score = home_score
                            game.away_score = away_score
                            updated = True
                        if game.status != status:
                            game.status = status
                            updated = True
                        if game.is_closed != is_closed:
                            game.is_closed = is_closed
                            updated = True
                            
                        if updated:
                            game.save()
                            games_updated += 1
                            if home_score is not None and away_score is not None:
                                scores_updated += 1
                                winner = "TIE" if home_score == away_score else (
                                    home_team.short_name if home_score > away_score else away_team.short_name
                                )
                                self.stdout.write(f"Updated scores: {game} -> {away_score}-{home_score} ({winner})")
                        
                    except Game.DoesNotExist:
                        # Skip if game doesn't exist and we're in scores-only mode
                        continue
                else:
                    # Create or update game (normal mode)
                    game, created = Game.objects.update_or_create(
                        api_id=game_key,
                        defaults={
                            'home_team': home_team,
                            'away_team': away_team,
                            'game_date': game_date,
                            'week': week,
                            'home_score': home_score,
                            'away_score': away_score,
                            'status': status,
                            'is_closed': is_closed,
                        }
                    )
                    
                    if created:
                        games_created += 1
                        self.stdout.write(f"Created: {game}")
                    else:
                        games_updated += 1
                        # Check if scores were updated
                        if home_score is not None and away_score is not None:
                            scores_updated += 1
                            winner = "TIE" if home_score == away_score else (
                                home_team.short_name if home_score > away_score else away_team.short_name
                            )
                            self.stdout.write(f"Updated scores: {game} -> {away_score}-{home_score} ({winner})")
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error processing game {item.get('GameKey', 'Unknown')}: {e}")
                )
                continue

        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f"\nSummary:\n"
                f"  Games created: {games_created}\n"
                f"  Games updated: {games_updated}\n"
                f"  Scores updated: {scores_updated}\n"
                f"  Bye weeks skipped: {bye_weeks_skipped}\n"
                f"  Total processed: {games_created + games_updated}"
            )
        )