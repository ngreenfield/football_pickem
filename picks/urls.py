from django.urls import path
from . import views

app_name = 'picks'

urlpatterns = [
    # Game views
    path('games/', views.game_list, name='game_list'),
    path('games/<int:pk>/', views.game_detail, name='game_detail'),
    
    # Pick views
    path('week/<int:week_number>/', views.week_picks, name='week_picks'),
    path('my-picks/', views.my_picks, name='my_picks'),
    path('make-pick/<int:game_id>/', views.make_pick, name='make_pick'),
    path('all-picks/', views.all_picks, name='all_picks'),
    
    # Leaderboard
    path('leaderboard/', views.leaderboard, name='leaderboard'),
]