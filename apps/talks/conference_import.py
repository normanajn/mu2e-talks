import csv
from datetime import date
from io import StringIO

from .models import Conference


class ConferenceImportError(ValueError):
    pass


def _parse_date(value):
    value = value.strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ConferenceImportError(f'Invalid date "{value}". Expected YYYY-MM-DD.') from exc


def import_conferences(upload):
    raw = upload.read()
    if isinstance(raw, bytes):
        try:
            text = raw.decode('utf-8-sig')
        except UnicodeDecodeError as exc:
            raise ConferenceImportError('The uploaded file must be a UTF-8 CSV file.') from exc
    else:
        text = raw

    reader = csv.DictReader(StringIO(text, newline=''))
    required = {'inspire_id', 'title', 'start_date', 'end_date', 'url'}
    missing = required - set(reader.fieldnames or [])
    if missing:
        raise ConferenceImportError(
            f'Missing required columns: {", ".join(sorted(missing))}.'
        )

    created = updated = 0
    for line_number, row in enumerate(reader, start=2):
        inspire_id = row['inspire_id'].strip()
        title = row['title'].strip()
        if not inspire_id or not title:
            raise ConferenceImportError(
                f'Row {line_number}: inspire_id and title are required.'
            )
        _, was_created = Conference.objects.update_or_create(
            inspire_id=inspire_id,
            defaults={
                'title': title,
                'start_date': _parse_date(row['start_date']),
                'end_date': _parse_date(row['end_date']),
                'url': row['url'].strip(),
            },
        )
        created += int(was_created)
        updated += int(not was_created)

    return created, updated
