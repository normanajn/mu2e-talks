import csv
from datetime import date
from pathlib import Path

from django.db import migrations


def seed_inspire_conferences(apps, schema_editor):
    Conference = apps.get_model('talks', 'Conference')
    csv_path = (
        Path(__file__).resolve().parent.parent
        / 'data'
        / 'inspire_upcoming_experiment_hep_conferences.csv'
    )
    with csv_path.open(newline='', encoding='utf-8-sig') as handle:
        for row in csv.DictReader(handle):
            Conference.objects.update_or_create(
                inspire_id=row['inspire_id'].strip(),
                defaults={
                    'title': row['title'].strip(),
                    'start_date': date.fromisoformat(row['start_date']) if row['start_date'] else None,
                    'end_date': date.fromisoformat(row['end_date']) if row['end_date'] else None,
                    'url': row['url'].strip(),
                },
            )


class Migration(migrations.Migration):

    dependencies = [
        ('talks', '0004_conference_inspire_id'),
    ]

    operations = [
        migrations.RunPython(seed_inspire_conferences, migrations.RunPython.noop),
    ]
