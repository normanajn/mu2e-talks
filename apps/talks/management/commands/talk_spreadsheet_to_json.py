from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.talks.spreadsheet_import import TalkSpreadsheetImportError, workbook_path_to_json


class Command(BaseCommand):
    help = 'Convert a Mu2e talk spreadsheet .xlsx file into normalized JSON import records.'

    def add_arguments(self, parser):
        parser.add_argument('input_file', type=Path)
        parser.add_argument('output_file', type=Path)

    def handle(self, *args, **options):
        try:
            count = workbook_path_to_json(options['input_file'], options['output_file'])
        except (OSError, TalkSpreadsheetImportError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(
            f'Wrote {count} normalized talk records to {options["output_file"]}.'
        ))
