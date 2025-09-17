from django.core.management.base import BaseCommand
import requests
from picks.models import Game
from datetime import datetime
import json

API_KEY = '6f3556c6beb94c71a62b02d1f0960704'
YEAR = 2025


class Command(BaseCommand):
    help = "Update NFL scores"

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
        parser.add_argument(
            '--final-only',
            action='store_true',
            help='Only update scores for final/closed games (original behavior)'
        )
        parser.add_argument(
            '--show-raw-api',
            action='store_true',
            help='Show raw API response for debugging'
        )

    def get_valid_score(self, primary_field, fallback_field, game_status, is_closed, debug=False):
        """
        Get a valid score with better fallback logic
        """
        def convert_score(score_value, field_name=""):
            if debug:
                self.stdout.write(f"      Converting {field_name}: {score_value} (type: {type(score_value).__name__})")
            
            if score_value is None:
                return None
            if score_value == '' or score_value == 'null':
                return 0 if is_closed else None
            try:
                converted = int(float(str(score_value)))
                if debug:
                    self.stdout.write(f"      Successfully converted to: {converted}")
                return converted
            except (ValueError, TypeError):
                if debug:
                    self.stdout.write(f"      Failed to convert, returning 0 for closed games")
                return 0 if is_closed else None
        
        # Try primary field first
        if debug:
            self.stdout.write(f"    Trying primary field...")
        score = convert_score(primary_field, "primary")
        if score is not None:
            return score
        
        # Try fallback field
        if debug:
            self.stdout.write(f"    Trying fallback field...")
        score = convert_score(fallback_field, "fallback")
        if score is not None:
            return score
        
        # If both are None/invalid, return 0 for closed games, None for others
        final_score = 0 if is_closed else None
        if debug:
            self.stdout.write(f"    Both fields invalid, returning: {final_score}")
        return final_score

    def handle(self, *args, **options):
        week_number = options['week_number']
        debug = options.get('debug', False)
        final_only = options.get('final_only', False)
        show_raw_api = options.get('show_raw_api', False)

        self.stdout.write(f"📡 Updating scores for Week {week_number} (Year {YEAR})")
        if final_only:
            self.stdout.write("🔒 Only updating final/closed games")
        else:
            self.stdout.write("🔄 Updating all games with current scores")

        url = f"https://api.sportsdata.io/v3/nfl/scores/json/ScoresByWeek/{YEAR}/{week_number}"
        headers = {'Ocp-Apim-Subscription-Key': API_KEY}

        # Debug: Show what we have in the database for this week
        if debug:
            self.stdout.write(f"\n🔍 Database games for Week {week_number}:")
            try:
                db_games = Game.objects.filter(week=week_number).order_by('game_date')
                if not db_games.exists():
                    self.stdout.write("   ⚠️ No games found in database for this week!")
                for game in db_games:
                    self.stdout.write(f"   • {game.api_id}: {game.away_team.short_name} @ {game.home_team.short_name} "
                                    f"({game.away_score}-{game.home_score}) [{game.status}]")
            except Exception as e:
                self.stdout.write(f"   ❌ Error querying database: {e}")

        try:
            self.stdout.write(f"\n🌐 Making API request to: {url}")
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                self.stderr.write(f"❌ API request failed with status {response.status_code}")
                self.stderr.write(f"Response: {response.text}")
                return

            data = response.json()
            self.stdout.write(f"✅ Found {len(data)} games from API")

            if not data:
                self.stdout.write("⚠️ No games returned from API - check week number and year")
                return

            # Show raw API data if requested
            if show_raw_api and data:
                self.stdout.write(f"\n🔍 Raw API Response (first game):")
                self.stdout.write(json.dumps(data[0], indent=2))

            # Enhanced debugging for score analysis
            if debug:
                self.stdout.write(f"\n🔍 DETAILED SCORE ANALYSIS FOR WEEK {week_number}:")
                for i, item in enumerate(data):
                    game_key = item.get('GameKey', 'NO_KEY')
                    home_team = item.get('HomeTeam', 'NO_HOME')
                    away_team = item.get('AwayTeam', 'NO_AWAY')
                    status = item.get('Status', 'NO_STATUS')
                    is_closed = item.get('IsClosed', False)
                    
                    # Check ALL possible score fields and their types
                    score_analysis = {
                        'HomeTeamScore': {
                            'value': item.get('HomeTeamScore'),
                            'type': type(item.get('HomeTeamScore')).__name__,
                            'is_none': item.get('HomeTeamScore') is None,
                            'is_empty_str': item.get('HomeTeamScore') == '',
                        },
                        'HomeScore': {
                            'value': item.get('HomeScore'),
                            'type': type(item.get('HomeScore')).__name__,
                            'is_none': item.get('HomeScore') is None,
                            'is_empty_str': item.get('HomeScore') == '',
                        },
                        'AwayTeamScore': {
                            'value': item.get('AwayTeamScore'),
                            'type': type(item.get('AwayTeamScore')).__name__,
                            'is_none': item.get('AwayTeamScore') is None,
                            'is_empty_str': item.get('AwayTeamScore') == '',
                        },
                        'AwayScore': {
                            'value': item.get('AwayScore'),
                            'type': type(item.get('AwayScore')).__name__,
                            'is_none': item.get('AwayScore') is None,
                            'is_empty_str': item.get('AwayScore') == '',
                        }
                    }
                    
                    self.stdout.write(f"\n   Game {i+1}: {game_key} - {away_team} @ {home_team}")
                    self.stdout.write(f"   Status: {status} | Closed: {is_closed}")
                    
                    for field_name, analysis in score_analysis.items():
                        self.stdout.write(f"   {field_name}: {analysis['value']} "
                                        f"({analysis['type']}) "
                                        f"[None: {analysis['is_none']}, Empty: {analysis['is_empty_str']}]")
                    
                    # Also check for any other score-related fields
                    other_fields = {k: v for k, v in item.items() if 'score' in k.lower() or 'point' in k.lower()}
                    if other_fields:
                        self.stdout.write(f"   OTHER SCORE FIELDS: {other_fields}")

            if debug and data:
                self.stdout.write(f"\n🔍 API games summary:")
                for i, item in enumerate(data):
                    game_key = item.get('GameKey', 'NO_KEY')
                    home_team = item.get('HomeTeam', 'NO_HOME')
                    away_team = item.get('AwayTeam', 'NO_AWAY')
                    home_score = item.get('HomeTeamScore') or item.get('HomeScore')
                    away_score = item.get('AwayTeamScore') or item.get('AwayScore')
                    status = item.get('Status', 'NO_STATUS')
                    is_closed = item.get('IsClosed', False)
                    
                    self.stdout.write(f"   {i+1}. {game_key}: {away_team} @ {home_team} "
                                    f"({away_score}-{home_score}) [{status}] Closed:{is_closed}")

            updated_count = 0
            skipped_count = 0
            not_found_count = 0
            errors = []

            for item in data:
                try:
                    game_key = item.get('GameKey')
                    if not game_key:
                        self.stderr.write("⚠ Skipping game with no GameKey")
                        continue

                    home_team_api = item.get('HomeTeam')
                    away_team_api = item.get('AwayTeam')
                    status = item.get('Status', 'Scheduled')
                    is_closed = item.get('IsClosed', False)
                    last_updated = item.get('Updated') or item.get('LastUpdated')

                    # Use improved score extraction
                    home_score = self.get_valid_score(
                        item.get('HomeTeamScore'), 
                        item.get('HomeScore'), 
                        status, 
                        is_closed,
                        debug
                    )

                    away_score = self.get_valid_score(
                        item.get('AwayTeamScore'), 
                        item.get('AwayScore'), 
                        status, 
                        is_closed,
                        debug
                    )

                    if debug:
                        self.stdout.write(f"\n  🔍 Score extraction for {game_key}:")
                        self.stdout.write(f"    Raw HomeTeamScore: {item.get('HomeTeamScore')}")
                        self.stdout.write(f"    Raw HomeScore: {item.get('HomeScore')}")
                        self.stdout.write(f"    Raw AwayTeamScore: {item.get('AwayTeamScore')}")
                        self.stdout.write(f"    Raw AwayScore: {item.get('AwayScore')}")
                        self.stdout.write(f"    FINAL EXTRACTED SCORES: Away={away_score}, Home={home_score}")

                    # Only skip non-final games if final_only flag is set
                    if final_only and (not is_closed or status not in ['Final', 'Final OT', 'F', 'F/OT']):
                        if debug:
                            self.stdout.write(f"⏭ Skipping non-final game {game_key} — status: {status}, is_closed: {is_closed}")
                        skipped_count += 1
                        continue

                    try:
                        game = Game.objects.get(api_id=game_key)
                    except Game.DoesNotExist:
                        self.stderr.write(f"⚠ Game {game_key} not found in DB — API match: {away_team_api} @ {home_team_api}")
                        not_found_count += 1
                        
                        # Try to find by team names as fallback
                        if debug:
                            try:
                                from picks.models import Team
                                home_team_obj = Team.objects.filter(short_name=home_team_api).first()
                                away_team_obj = Team.objects.filter(short_name=away_team_api).first()
                                if home_team_obj and away_team_obj:
                                    possible_game = Game.objects.filter(
                                        home_team=home_team_obj,
                                        away_team=away_team_obj,
                                        week=week_number
                                    ).first()
                                    if possible_game:
                                        self.stdout.write(f"   💡 Found possible match by teams: {possible_game.api_id}")
                            except Exception as e:
                                self.stdout.write(f"   🔍 Team lookup failed: {e}")
                        continue

                    # Sanity check
                    if debug:
                        self.stdout.write(f"\n🔄 Processing: {game_key}")
                        self.stdout.write(f"   API: {away_team_api} @ {home_team_api} ({away_score}-{home_score})")
                        self.stdout.write(f"   DB:  {game.away_team.short_name} @ {game.home_team.short_name} ({game.away_score}-{game.home_score})")
                        if last_updated:
                            self.stdout.write(f"   Last updated: {last_updated}")

                    updated = False
                    changes = []

                    # Score updates - only update if we have valid data
                    if home_score is not None and home_score != game.home_score:
                        changes.append(f"Home: {game.home_score} → {home_score}")
                        game.home_score = home_score
                        updated = True

                    if away_score is not None and away_score != game.away_score:
                        changes.append(f"Away: {game.away_score} → {away_score}")
                        game.away_score = away_score
                        updated = True

                    # Enhanced status mapping
                    status_mapping = {
                        'Scheduled': 'SCHEDULED',
                        'InProgress': 'INPROGRESS', 
                        'In Progress': 'INPROGRESS',
                        'Halftime': 'INPROGRESS',
                        '1st Quarter': 'INPROGRESS',
                        '2nd Quarter': 'INPROGRESS', 
                        '3rd Quarter': 'INPROGRESS',
                        '4th Quarter': 'INPROGRESS',
                        'Overtime': 'INPROGRESS',
                        'Final': 'FINAL',
                        'F': 'FINAL', 
                        'Final OT': 'FINAL',
                        'F/OT': 'FINAL',
                        'Cancelled': 'CANCELLED',
                        'Canceled': 'CANCELLED',
                        'Postponed': 'POSTPONED',
                        'Suspended': 'SUSPENDED',
                    }
                    mapped_status = status_mapping.get(status, 'SCHEDULED')

                    if game.status != mapped_status:
                        changes.append(f"Status: {game.status} → {mapped_status}")
                        game.status = mapped_status
                        updated = True

                    if game.is_closed != is_closed:
                        changes.append(f"Closed: {game.is_closed} → {is_closed}")
                        game.is_closed = is_closed
                        updated = True

                    if updated:
                        game.save()
                        updated_count += 1

                        winner = "TIE"
                        if home_score is not None and away_score is not None:
                            if home_score > away_score:
                                winner = game.home_team.short_name
                            elif away_score > home_score:
                                winner = game.away_team.short_name

                        # Show different status indicators based on game state
                        status_icon = "🏁" if is_closed else ("⏱️" if mapped_status == 'INPROGRESS' else "📅")
                        
                        self.stdout.write(
                            f"✅ Updated: {game.away_team.short_name} @ {game.home_team.short_name} "
                            f"→ {away_score}-{home_score} | Winner: {winner} [{mapped_status}] {status_icon}"
                        )
                        if debug and changes:
                            self.stdout.write(f"   ↳ Changes: {', '.join(changes)}")
                    elif debug:
                        status_icon = "🏁" if is_closed else ("⏱️" if mapped_status == 'INPROGRESS' else "📅")
                        self.stdout.write(
                            f"🔍 No update needed: {game.away_team.short_name} @ {game.home_team.short_name} "
                            f"({away_score}-{home_score}) [{mapped_status}] {status_icon}"
                        )

                except Exception as e:
                    error_msg = f"❌ Error processing game {item.get('GameKey', 'unknown')}: {e}"
                    errors.append(error_msg)
                    self.stderr.write(error_msg)
                    if debug:
                        import traceback
                        self.stderr.write(traceback.format_exc())

            # Enhanced Summary
            self.stdout.write("\n📊 Update Summary:")
            self.stdout.write(f" • Total API games: {len(data)}")
            self.stdout.write(f" • Games updated: {updated_count}")
            self.stdout.write(f" • Games not found in DB: {not_found_count}")
            if final_only:
                self.stdout.write(f" • Games skipped (not final): {skipped_count}")
            self.stdout.write(f" • Errors: {len(errors)}")

            if not_found_count > 0:
                self.stdout.write(f"\n⚠️ {not_found_count} games from API were not found in your database.")
                self.stdout.write("   This could mean:")
                self.stdout.write("   • Your database is missing some games for this week")
                self.stdout.write("   • The API GameKey format doesn't match your api_id values")
                self.stdout.write("   • There's a mismatch in team abbreviations")

            if debug and errors:
                self.stdout.write("\n❌ Errors encountered:")
                for err in errors:
                    self.stdout.write(f" • {err}")

        except requests.RequestException as e:
            self.stderr.write(f"❌ API request failed: {e}")

        except Exception as e:
            self.stderr.write(f"❌ Unexpected error: {e}")
            if debug:
                import traceback
                self.stderr.write(traceback.format_exc())