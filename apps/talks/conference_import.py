import csv
from datetime import date

from .models import Conference


def _parse_date(value):
    return date.fromisoformat(value) if value else None


def import_conferences(csv_file):
    created = 0
    updated = 0
    reader = csv.DictReader(csv_file)
    required = {'inspire_id', 'title', 'start_date', 'end_date', 'url'}
    if not reader.fieldnames or not required.issubset(reader.fieldnames):
        raise ValueError(f'CSV columns must include: {", ".join(sorted(required))}')

    for row in reader:
        inspire_id = row['inspire_id'].strip()
        title = row['title'].strip()
        if not inspire_id or not title:
            raise ValueError('Every conference row requires inspire_id and title.')

        _, was_created = Conference.objects.update_or_create(
            inspire_id=inspire_id,
            defaults={
                'title': title,
                'start_date': _parse_date(row['start_date'].strip()),
                'end_date': _parse_date(row['end_date'].strip()),
                'url': row['url'].strip(),
            },
        )
        created += int(was_created)
        updated += int(not was_created)

    return created, updated
