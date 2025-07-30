import os
import django

# Point Django to your settings module before importing anything else
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Set up Django
django.setup()

# Now import your models

from picks.models import Team

teams = [
    ("Arizona Cardinals", "ARI"),
    ("Atlanta Falcons", "ATL"),
    ("Baltimore Ravens", "BAL"),
    ("Buffalo Bills", "BUF"),
    ("Carolina Panthers", "CAR"),
    ("Chicago Bears", "CHI"),
    ("Cincinnati Bengals", "CIN"),
    ("Cleveland Browns", "CLE"),
    ("Dallas Cowboys", "DAL"),
    ("Denver Broncos", "DEN"),
    ("Detroit Lions", "DET"),
    ("Green Bay Packers", "GB"),
    ("Houston Texans", "HOU"),
    ("Indianapolis Colts", "IND"),
    ("Jacksonville Jaguars", "JAX"),
    ("Kansas City Chiefs", "KC"),
    ("Las Vegas Raiders", "LV"),
    ("Los Angeles Chargers", "LAC"),
    ("Los Angeles Rams", "LAR"),
    ("Miami Dolphins", "MIA"),
    ("Minnesota Vikings", "MIN"),
    ("New England Patriots", "NE"),
    ("New Orleans Saints", "NO"),
    ("New York Giants", "NYG"),
    ("New York Jets", "NYJ"),
    ("Philadelphia Eagles", "PHI"),
    ("Pittsburgh Steelers", "PIT"),
    ("San Francisco 49ers", "SF"),
    ("Seattle Seahawks", "SEA"),
    ("Tampa Bay Buccaneers", "TB"),
    ("Tennessee Titans", "TEN"),
    ("Washington Commanders", "WAS"),
]

for name, short in teams:
    Team.objects.get_or_create(name=name, short_name=short)