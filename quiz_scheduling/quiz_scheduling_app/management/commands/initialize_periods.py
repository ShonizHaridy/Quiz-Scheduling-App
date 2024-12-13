from django.core.management.base import BaseCommand
from quiz_scheduling_app.models import Period
from datetime import time

class Command(BaseCommand):
    help = 'Initialize period data'

    def handle(self, *args, **options):
        periods = [
            (1, '07:00', '07:50', False),
            (2, '08:00', '08:50', False),
            (3, '09:00', '09:50', False),
            (4, '10:00', '10:50', False),
            (5, '11:00', '11:50', False),
            (6, '12:20', '13:10', False),
            (7, '13:20', '14:10', False),
            (8, '14:20', '15:10', False),
            (9, '15:30', '16:20', True),
            (10, '16:30', '17:20', True),
            (11, '17:30', '18:20', True),
            (12, '18:30', '19:20', True),
            (13, '19:30', '18:20', True),
            (14, '20:30', '19:20', True),
            (15, '21:30', '22:20', True),
            (16, '06:00', '06:50', False),
        ]

        for number, start, end, is_online in periods:
            Period.objects.get_or_create(
                number=number,
                defaults={
                    'start_time': time.fromisoformat(start),
                    'end_time': time.fromisoformat(end),
                    'is_online': is_online
                }
            )

        self.stdout.write(
            self.style.SUCCESS('Successfully initialized periods')
        )