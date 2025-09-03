from django import forms
from .models import Pick, Team, Game

class PickForm(forms.ModelForm):
    class Meta:
        model = Pick
        fields = ['selected_team', 'confidence_points']
        widgets = {
            'selected_team': forms.Select(attrs={'class': 'form-select'}),
            'confidence_points': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 16
            })
        }
    
    def __init__(self, *args, game=None, **kwargs):
        super().__init__(*args, **kwargs)
        if game:
            # Limit team choices to only the teams playing in this game
            self.fields['selected_team'].queryset = Team.objects.filter(
                models.Q(home_team=game) | models.Q(away_team=game)
            )
            self.fields['selected_team'].choices = [
                ('', 'Select a team'),
                (game.home_team.id, f'{game.home_team.name} (Home)'),
                (game.away_team.id, f'{game.away_team.name} (Away)')
            ]

class WeekPicksForm(forms.Form):
    """Dynamic form for all picks in a week"""
    
    def __init__(self, *args, games=None, existing_picks=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.games = games or []
        self.existing_picks = existing_picks or {}
        
        # Create fields for each game
        for game in self.games:
            # Team selection field
            team_field_name = f'game_{game.id}_team'
            self.fields[team_field_name] = forms.ChoiceField(
                label=f'{game.away_team.short_name} @ {game.home_team.short_name}',
                choices=[
                    ('', 'Select winner'),
                    (game.away_team.id, f'{game.away_team.name} (Away)'),
                    (game.home_team.id, f'{game.home_team.name} (Home)')
                ],
                widget=forms.Select(attrs={'class': 'form-select team-select'}),
                required=True
            )
            
            # Confidence points field
            confidence_field_name = f'game_{game.id}_confidence'
            self.fields[confidence_field_name] = forms.IntegerField(
                label='Confidence',
                min_value=1,
                max_value=len(self.games),
                widget=forms.NumberInput(attrs={
                    'class': 'form-control confidence-input',
                    'min': 1,
                    'max': len(self.games)
                }),
                required=True
            )
            
            # Set initial values if pick exists
            if game.id in self.existing_picks:
                pick = self.existing_picks[game.id]
                self.fields[team_field_name].initial = pick.selected_team.id
                self.fields[confidence_field_name].initial = pick.confidence_points
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Collect confidence points to check for duplicates
        confidence_points = []
        games_count = len(self.games)
        
        for game in self.games:
            confidence_field = f'game_{game.id}_confidence'
            if confidence_field in cleaned_data:
                points = cleaned_data[confidence_field]
                if points in confidence_points:
                    raise forms.ValidationError(
                        f'Confidence point {points} is used multiple times. Each game must have a unique confidence value.'
                    )
                confidence_points.append(points)
        
        # Check that all confidence points from 1 to games_count are used
        expected_points = set(range(1, games_count + 1))
        actual_points = set(confidence_points)
        
        if actual_points != expected_points:
            missing = expected_points - actual_points
            extra = actual_points - expected_points
            error_msg = []
            if missing:
                error_msg.append(f'Missing confidence points: {sorted(missing)}')
            if extra:
                error_msg.append(f'Invalid confidence points: {sorted(extra)}')
            
            raise forms.ValidationError(
                f'You must use each confidence point from 1 to {games_count} exactly once. {" ".join(error_msg)}'
            )
        
        return cleaned_data

class QuickPickForm(forms.Form):
    """Simple form for making a quick pick on a single game"""
    selected_team = forms.ModelChoiceField(
        queryset=Team.objects.none(),
        widget=forms.RadioSelect,
        empty_label=None
    )
    confidence_points = forms.IntegerField(
        min_value=1,
        max_value=16,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confidence (1-16)'
        })
    )
    
    def __init__(self, *args, game=None, **kwargs):
        super().__init__(*args, **kwargs)
        if game:
            self.fields['selected_team'].queryset = Team.objects.filter(
                models.Q(pk=game.home_team.pk) | models.Q(pk=game.away_team.pk)
            )
            
            # Create custom choices with team names and home/away designation
            self.fields['selected_team'].choices = [
                (game.away_team.id, f'{game.away_team.name} (Away)'),
                (game.home_team.id, f'{game.home_team.name} (Home)')
            ]