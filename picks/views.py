from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.db import models
from .models import Game, Pick, Week, Team
from .forms import WeekPicksForm

def game_list(request):
    """Display games grouped by week"""
    weeks = Week.objects.prefetch_related(
        'game_set__home_team',
        'game_set__away_team'
    ).order_by('number')
    
    # Annotate games with user's picks if authenticated
    if request.user.is_authenticated:
        for week in weeks:
            for game in week.game_set.all():
                try:
                    user_pick = Pick.objects.get(user=request.user, game=game)
                    game.user_pick = user_pick
                except Pick.DoesNotExist:
                    game.user_pick = None
    
    context = {
        'weeks': weeks,
    }
    return render(request, 'picks/game_list.html', context)

def game_detail(request, pk):
    """Display individual game details"""
    game = get_object_or_404(Game, pk=pk)
    
    # Get user's pick for this game if authenticated
    user_pick = None
    if request.user.is_authenticated:
        try:
            user_pick = Pick.objects.get(user=request.user, game=game)
        except Pick.DoesNotExist:
            pass
    
    context = {
        'game': game,
        'user_pick': user_pick,
    }
    return render(request, 'picks/game_detail.html', context)

@login_required
def week_picks(request, week_number):
    """Display and handle picks for a specific week"""
    week = get_object_or_404(Week, number=week_number)
    games = Game.objects.filter(week=week).select_related(
        'home_team', 'away_team'
    ).order_by('game_date')
    
    if not games.exists():
        messages.warning(request, f'No games found for Week {week_number}')
        return redirect('game_list')
    
    # Get existing picks for this user and week
    existing_picks = Pick.objects.filter(
        user=request.user, 
        game__week=week
    ).select_related('game', 'selected_team')
    picks_dict = {pick.game.id: pick for pick in existing_picks}
    
    if request.method == 'POST':
        return handle_week_picks_submission(request, week, games, picks_dict)
    
    context = {
        'week': week,
        'games': games,
        'picks_dict': picks_dict,
        'games_count': games.count(),
    }
    return render(request, 'picks/week_picks.html', context)

@transaction.atomic
def handle_week_picks_submission(request, week, games, existing_picks):
    """Handle the submission of picks for a week"""
    picks_data = []
    confidence_points_used = []
    
    # Collect all pick data from POST
    for game in games:
        team_key = f'game_{game.id}_team'
        confidence_key = f'game_{game.id}_confidence'
        
        selected_team_id = request.POST.get(team_key)
        confidence_points = request.POST.get(confidence_key)
        
        if selected_team_id and confidence_points:
            try:
                selected_team = Team.objects.get(id=selected_team_id)
                confidence_points = int(confidence_points)
                
                # Validate that the selected team is playing in this game
                if selected_team not in [game.home_team, game.away_team]:
                    messages.error(request, f'Invalid team selection for {game}')
                    return redirect('week_picks', week_number=week.number)
                
                # Check for duplicate confidence points
                if confidence_points in confidence_points_used:
                    messages.error(request, f'Confidence point {confidence_points} used multiple times')
                    return redirect('week_picks', week_number=week.number)
                
                confidence_points_used.append(confidence_points)
                picks_data.append({
                    'game': game,
                    'selected_team': selected_team,
                    'confidence_points': confidence_points
                })
                
            except (Team.DoesNotExist, ValueError) as e:
                messages.error(request, f'Invalid pick data for {game}')
                return redirect('week_picks', week_number=week.number)
    
    # Validate confidence points range
    expected_points = list(range(1, len(games) + 1))
    confidence_points_used.sort()
    
    if confidence_points_used != expected_points:
        messages.error(request, f'You must use confidence points 1-{len(games)} exactly once each')
        return redirect('week_picks', week_number=week.number)
    
    # Save all picks
    for pick_data in picks_data:
        Pick.objects.update_or_create(
            user=request.user,
            game=pick_data['game'],
            defaults={
                'selected_team': pick_data['selected_team'],
                'confidence_points': pick_data['confidence_points']
            }
        )
    
    messages.success(request, f'Successfully saved {len(picks_data)} picks for Week {week.number}!')
    return redirect('week_picks', week_number=week.number)

@login_required
def make_pick(request, game_id):
    """AJAX endpoint for making individual picks"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    game = get_object_or_404(Game, id=game_id)
    
    # Check if game is still open for picks
    if game.status != 'SCHEDULED':
        return JsonResponse({'error': 'Game is no longer open for picks'}, status=400)
    
    selected_team_id = request.POST.get('selected_team')
    confidence_points = request.POST.get('confidence_points')
    
    try:
        selected_team = Team.objects.get(id=selected_team_id)
        confidence_points = int(confidence_points)
        
        # Validate team plays in this game
        if selected_team not in [game.home_team, game.away_team]:
            return JsonResponse({'error': 'Invalid team selection'}, status=400)
        
        # Validate confidence points
        if confidence_points < 1 or confidence_points > 16:
            return JsonResponse({'error': 'Confidence points must be between 1 and 16'}, status=400)
        
        # Create or update pick
        pick, created = Pick.objects.update_or_create(
            user=request.user,
            game=game,
            defaults={
                'selected_team': selected_team,
                'confidence_points': confidence_points
            }
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Pick {"created" if created else "updated"} successfully',
            'pick': {
                'selected_team': selected_team.short_name,
                'confidence_points': confidence_points
            }
        })
        
    except (Team.DoesNotExist, ValueError) as e:
        return JsonResponse({'error': 'Invalid pick data'}, status=400)

@login_required
def my_picks(request):
    """Display all user's picks organized by week"""
    picks = Pick.objects.filter(user=request.user).select_related(
        'game', 'selected_team', 'game__home_team', 'game__away_team', 'game__week'
    ).order_by('-game__week__number', '-game__game_date')
    
    # Group picks by week
    picks_by_week = {}
    for pick in picks:
        week_num = pick.game.week.number if pick.game.week else 0
        if week_num not in picks_by_week:
            picks_by_week[week_num] = []
        picks_by_week[week_num].append(pick)
    
    # Calculate stats
    total_picks = picks.count()
    correct_picks = sum(1 for pick in picks if pick.is_correct and pick.game.is_finished)
    total_points = sum(pick.points_earned for pick in picks if pick.game.is_finished)
    completed_games = picks.filter(game__status='FINAL').count()
    win_percentage = (correct_picks / completed_games * 100) if completed_games > 0 else 0
    
    context = {
        'picks_by_week': dict(sorted(picks_by_week.items(), reverse=True)),
        'total_picks': total_picks,
        'correct_picks': correct_picks,
        'total_points': total_points,
        'win_percentage': round(win_percentage, 1),
        'completed_games': completed_games,
    }
    
    return render(request, 'picks/my_picks.html', context)

def leaderboard(request):
    """Display leaderboard of all users"""
    from django.contrib.auth.models import User
    from django.db.models import Count, Sum, Case, When, IntegerField
    
    # Get all users with their pick stats
    users = User.objects.annotate(
        total_picks=Count('pick'),
        total_points=Sum(
            Case(
                When(
                    pick__game__status='FINAL',
                    pick__selected_team=Case(
                        When(pick__game__home_score__gt=models.F('pick__game__away_score'), 
                             then='pick__game__home_team'),
                        When(pick__game__away_score__gt=models.F('pick__game__home_score'), 
                             then='pick__game__away_team'),
                        default=None
                    ),
                    then='pick__confidence_points'
                ),
                default=0,
                output_field=IntegerField()
            )
        )
    ).order_by('-total_points')
    
    context = {
        'users': users,
    }
    return render(request, 'picks/leaderboard.html', context)