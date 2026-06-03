from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.talks.spreadsheet_import import (
    TalkSpreadsheetImportError,
    import_talk_records,
    records_from_json,
    workbook_to_records,
)


class Command(BaseCommand):
    help = 'Import Mu2e talk records from a spreadsheet .xlsx file or normalized JSON file.'

    def add_arguments(self, parser):
        parser.add_argument('input_file', type=Path)
        parser.add_argument(
            '--created-by',
            default='mu2e-admin',
            help='Username or email to use as the created_by user for imported talks.',
        )

    def handle(self, *args, **options):
        input_file = options['input_file']
        User = get_user_model()
        created_by = (
            User.objects.filter(username=options['created_by']).first()
            or User.objects.filter(email=options['created_by']).first()
            or User.objects.filter(is_superuser=True).first()
            or User.objects.first()
        )
        if not created_by:
            raise CommandError('No user exists to assign as created_by for imported talks.')

        try:
            with input_file.open('rb') as handle:
                records = records_from_json(handle) if input_file.suffix.lower() == '.json' else workbook_to_records(handle)
            counts = import_talk_records(records, created_by=created_by)
        except (OSError, TalkSpreadsheetImportError) as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.SUCCESS(
            'Talk import complete: '
            f'{counts["created"]} created, {counts["updated"]} updated, '
            f'{counts["matched_users"]} speakers matched, {counts["unmatched_users"]} speakers unmatched, '
            f'{counts["matched_institutions"]} institutions matched, '
            f'{counts["unmatched_institutions"]} institutions unmatched.'
        ))
