from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.talks.conference_import import import_conferences


class Command(BaseCommand):
    help = 'Import or update conferences from a CSV file.'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=Path)

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        try:
            with csv_file.open(newline='', encoding='utf-8-sig') as handle:
                created, updated = import_conferences(handle)
        except (OSError, ValueError) as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.SUCCESS(
            f'Conference import complete: {created} created, {updated} updated.'
        ))
