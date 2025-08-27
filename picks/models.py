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
    STATUS_CHOICES = [
        ('SCHEDULED', 'Scheduled'),
        ('INPROGRESS', 'In Progress'),
        ('FINAL', 'Final'),
        ('POSTPONED', 'Postponed'),
        ('CANCELED', 'Canceled'),
    ]
    
    api_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    week = models.ForeignKey(Week, on_delete=models.CASCADE, null=True, blank=True)
    home_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='home_team')
    away_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='away_team')
    game_date = models.DateTimeField()
    home_score = models.IntegerField(null=True, blank=True)
    away_score = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SCHEDULED')
    is_closed = models.BooleanField(default=False)  # True when game is completely finished

    def __str__(self):
        return f"{self.away_team} @ {self.home_team} (Week {self.week.number if self.week else 'TBD'})"
    
    @property
    def winner(self):
        """Returns the winning team or None if tie/not finished"""
        if self.home_score is not None and self.away_score is not None:
            if self.home_score > self.away_score:
                return self.home_team
            elif self.away_score > self.home_score:
                return self.away_team
        return None  # Tie or game not finished
    
    @property
    def is_finished(self):
        """Returns True if game is completed"""
        return self.status == 'FINAL' and self.is_closed


class Pick(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    selected_team = models.ForeignKey(Team, on_delete=models.CASCADE)
    confidence_points = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('user', 'game')]
        constraints = [
            models.UniqueConstraint(fields=['user', 'game'], name='unique_user_game_pick'),
        ]

    def __str__(self):
        return f"{self.user.username}'s pick for {self.game}: {self.selected_team} ({self.confidence_points} pts)"
    
    @property
    def is_correct(self):
        """Returns True if the pick was correct"""
        return self.game.winner == self.selected_team
    
    @property
    def points_earned(self):
        """Returns points earned for this pick"""
        return self.confidence_points if self.is_correct else 0