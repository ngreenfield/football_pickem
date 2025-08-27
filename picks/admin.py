from django.contrib import admin
from .models import Team, Week, Game, Pick

# Register your models here.
admin.site.register(Team)
admin.site.register(Week)
admin.site.register(Game)
admin.site.register(Pick)