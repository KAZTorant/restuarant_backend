from django.core.management.base import BaseCommand

from apps.orders.models import Statistics


class Command(BaseCommand):
    help = 'Açıq növbələri yalnız öz restoranının sifarişləri ilə yenidən sayır.'

    def handle(self, *args, **options):
        shifts = Statistics.objects.filter(is_closed=False, title='till_now')
        updated = 0
        for shift in shifts:
            Statistics.objects.calculate_till_now(shift.started_by)
            shift.refresh_from_db()
            self.stdout.write(
                f"Növbə {shift.id} restoran={shift.restaurant_id} "
                f"nağd={shift.cash_total} kart={shift.card_total} digər={shift.other_total}"
            )
            updated += 1
        self.stdout.write(self.style.SUCCESS(f'{updated} açıq növbə yeniləndi.'))
