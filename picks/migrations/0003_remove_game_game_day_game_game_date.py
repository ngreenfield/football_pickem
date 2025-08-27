from django.db import migrations, models
import django.utils.timezone

class Migration(migrations.Migration):

    dependencies = [
        ('picks', '0002_team_short_name'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='game',
            name='game_day',
        ),
        migrations.AddField(
            model_name='game',
            name='game_date',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]