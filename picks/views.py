from django.shortcuts import render,  get_object_or_404
from .models import Game

# Create your views here.
def game_list(request):
    games = Game.objects.order_by('game_date')
    return render(request, 'picks/game_list.html', {'games': games})

def game_detail(request, pk):
    game = get_object_or_404(Game, pk=pk)
    return render(request, 'picks/game_detail.html', {'game': game})