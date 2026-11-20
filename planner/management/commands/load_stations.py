from django.core.management.base import BaseCommand

from planner.services.stations import ingest_stations


class Command(BaseCommand):
    help = "Load US truck stops from the fuel-price CSV and geocode them via the city gazetteer."

    def handle(self, *args, **options):
        stats = ingest_stations()
        self.stdout.write(
            self.style.SUCCESS(
                f"Loaded {stats['loaded']} stations "
                f"({stats['csv_us_unique']} unique US rows, "
                f"{stats['unmatched_cities']} unmatched cities skipped)."
            )
        )
