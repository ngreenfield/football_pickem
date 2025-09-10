from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from picks.models import Pick, Game

def signup_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}! You can now log in.')
            login(request, user)
            return redirect('root')
    else:
        form = UserCreationForm()
    return render(request, 'users/signup.html' , {'form': form})

@login_required
def profile_view(request):
    # Get user's picks with related game data
    user_picks = Pick.objects.filter(user=request.user).select_related(
        'game', 'selected_team', 'game__home_team', 'game__away_team', 'game__week'
    ).order_by('-game__game_date')
    
    # Get some basic stats
    total_picks = user_picks.count()
    
    # Count correct picks and calculate points
    correct_picks = 0
    total_points = 0
    completed_games = 0
    
    for pick in user_picks:
        if pick.game.is_finished:
            completed_games += 1
            if pick.is_correct:
                correct_picks += 1
                total_points += pick.confidence_points  
    
    # Calculate win percentage
    win_percentage = (correct_picks / completed_games * 100) if completed_games > 0 else 0
    
    context = {
        'user_picks': user_picks[:10],  # Show last 10 picks
        'total_picks': total_picks,
        'correct_picks': correct_picks,
        'total_points': total_points,
        'win_percentage': round(win_percentage, 1),
        'completed_games': completed_games,
    }
    
    return render(request, 'users/profile.html', context)

def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect('users:login')  