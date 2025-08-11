from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Team(models.Model):
    name = models.CharField(max_length=100)
    short_name = models.CharField(max_length=10, unique=True)

    def __str__(self):
        return self.name
    

class Week(models.Model):
    number = models.IntegerField()
    
    def __str__(self):
        return f"Week {self.number}"
    

class Game(models.Model):
    api_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    week = models.ForeignKey(Week, on_delete=models.CASCADE, null=True, blank=True)
    home_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='home_team')
    away_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='away_team')
    game_date = models.DateTimeField()
    home_score = models.IntegerField(null=True, blank=True)
    away_score = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.away_team} @ {self.home_team} (Week {self.week.number})"


class Pick(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    selected_team =  models.ForeignKey(Team, on_delete=models.CASCADE)
    confidence_poitns = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('user', 'game')]
        constraints = [
            models.UniqueConstraint(fields=['user', 'game'], name='unique_user_game_pick'),
        ]

    def __str__(self):
        return f"{self.user.username}'s pick for {self.game}: {self.selected_team} ({self.confidence_poitns} pts)"