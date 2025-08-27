from django.core.management.base import BaseCommand
from django.core.management import call_command

class Command(BaseCommand):
    help = "Quick command to update scores only (alias for load_schedule --scores-only)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--week',
            type=int,
            help='Only update scores for a specific week number',
        )

    def handle(self, *args, **options):
        self.stdout.write("Updating scores from API...")
        
        # Call the main load_schedule command with scores-only flag
        call_command_args = ['load_schedule', '--scores-only']
        if options['week']:
            call_command_args.extend(['--week', str(options['week'])])
            
        call_command(*call_command_args)