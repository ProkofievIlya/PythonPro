from datetime import timedelta

from django.core.management.base import BaseCommand

from catalog.checkout import cancel_stale_orders


class Command(BaseCommand):
    help = "Скасовує неоплачені замовлення, старші за N годин, і повертає книги на склад."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--hours", type=int, default=24)

    def handle(self, *args, hours: int, **options) -> None:
        count = cancel_stale_orders(timedelta(hours=hours))
        self.stdout.write(self.style.SUCCESS(f"Скасовано замовлень: {count}"))
