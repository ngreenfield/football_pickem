import requests
from dateutil import parser
from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware

from picks.models import Game, Team, Week


SEASON = 2026
API_URL = (
    "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
)


class Command(BaseCommand):
    help = "Loads the NFL regular-season schedule and updates scores from ESPN"

    def add_arguments(self, parser):
        parser.add_argument(
            "--scores-only",
            action="store_true",
            help="Only update scores and game status for existing games",
        )
        parser.add_argument(
            "--week",
            type=int,
            help="Only load/update a specific regular-season week",
        )

    def handle(self, *args, **options):
        scores_only = options["scores_only"]
        requested_week = options.get("week")

        if requested_week:
            weeks = [requested_week]
        else:
            weeks = range(1, 19)

        created_count = 0
        updated_count = 0

        for week_number in weeks:
            params = {
                "dates": SEASON,
                "limit": 1000,
                "seasontype": 2,
                "week": week_number,
            }

            self.stdout.write(
                f"Fetching {SEASON} NFL regular-season Week "
                f"{week_number} from ESPN..."
            )

            try:
                response = requests.get(
                    API_URL,
                    params=params,
                    timeout=30,
                )
                response.raise_for_status()
                data = response.json()
            except requests.RequestException as exc:
                self.stderr.write(
                    self.style.ERROR(
                        f"Error fetching Week {week_number}: {exc}"
                    )
                )
                continue

            events = data.get("events", [])

            self.stdout.write(
                f"ESPN returned {len(events)} events for Week {week_number}."
            )

            for event in events:
                season_info = event.get("season", {})

                if season_info.get("year") != SEASON:
                    continue

                if season_info.get("type") != 2:
                    continue

                week_info = event.get("week", {})
                current_week = week_info.get("number")

                if not current_week:
                    continue

                competition = event.get("competitions", [{}])[0]
                competitors = competition.get("competitors", [])

                if len(competitors) != 2:
                    continue

                home_team_data = next(
                    (
                        team
                        for team in competitors
                        if team.get("homeAway") == "home"
                    ),
                    None,
                )

                away_team_data = next(
                    (
                        team
                        for team in competitors
                        if team.get("homeAway") == "away"
                    ),
                    None,
                )

                if not home_team_data or not away_team_data:
                    continue

                home_team_info = home_team_data.get("team", {})
                away_team_info = away_team_data.get("team", {})

                home_team_code = home_team_info.get("abbreviation")
                away_team_code = away_team_info.get("abbreviation")

                home_team_name = home_team_info.get("displayName")
                away_team_name = away_team_info.get("displayName")

                if not home_team_code or not away_team_code:
                    continue

                home_team, _ = Team.objects.get_or_create(
                    short_name=home_team_code,
                    defaults={
                        "name": home_team_name or home_team_code
                    },
                )

                away_team, _ = Team.objects.get_or_create(
                    short_name=away_team_code,
                    defaults={
                        "name": away_team_name or away_team_code
                    },
                )

                week, _ = Week.objects.get_or_create(
                    season=SEASON,
                    number=current_week,
                )

                game_date = parser.parse(event["date"])

                if game_date.tzinfo is None:
                    game_date = make_aware(game_date)

                status_info = (
                    competition
                    .get("status", {})
                    .get("type", {})
                )

                status_state = status_info.get("state")
                status_name = status_info.get("name", "")
                completed = status_info.get("completed", False)

                if "CANCELED" in status_name.upper():
                    status = "CANCELED"
                elif "POSTPONED" in status_name.upper():
                    status = "POSTPONED"
                elif status_state == "in":
                    status = "INPROGRESS"
                elif completed or status_state == "post":
                    status = "FINAL"
                else:
                    status = "SCHEDULED"

                home_score = home_team_data.get("score")
                away_score = away_team_data.get("score")

                if home_score is not None:
                    try:
                        home_score = int(home_score)
                    except (TypeError, ValueError):
                        home_score = None

                if away_score is not None:
                    try:
                        away_score = int(away_score)
                    except (TypeError, ValueError):
                        away_score = None

                is_closed = completed
                game_id = event.get("id")

                if not game_id:
                    continue

                if scores_only:
                    try:
                        game = Game.objects.get(api_id=game_id)
                    except Game.DoesNotExist:
                        continue

                    game.home_score = home_score
                    game.away_score = away_score
                    game.status = status
                    game.is_closed = is_closed

                    game.save(
                        update_fields=[
                            "home_score",
                            "away_score",
                            "status",
                            "is_closed",
                        ]
                    )

                    updated_count += 1

                else:
                    game, created = Game.objects.update_or_create(
                        api_id=game_id,
                        defaults={
                            "home_team": home_team,
                            "away_team": away_team,
                            "game_date": game_date,
                            "week": week,
                            "home_score": home_score,
                            "away_score": away_score,
                            "status": status,
                            "is_closed": is_closed,
                        },
                    )

                    if created:
                        created_count += 1
                    else:
                        updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Finished. Created {created_count} games, "
                f"updated {updated_count} games."
            )
        )
