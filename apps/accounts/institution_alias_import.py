import csv
import io

from django.db import transaction

from .models import Institution, InstitutionAlias, normalize_institution_alias


class InstitutionAliasImportError(ValueError):
    pass


def _decode_upload(upload):
    try:
        return upload.read().decode('utf-8-sig')
    except UnicodeDecodeError as exc:
        raise InstitutionAliasImportError('Alias CSV must be UTF-8 encoded.') from exc


def _institution_for_name(name):
    name = str(name or '').strip()
    if not name:
        return None
    exact = Institution.objects.filter(name__iexact=name).first()
    if exact:
        return exact
    normalized = normalize_institution_alias(name)
    for institution in Institution.objects.all():
        if normalize_institution_alias(institution.name) == normalized:
            return institution
    return None


@transaction.atomic
def import_institution_aliases(upload):
    reader = csv.DictReader(io.StringIO(_decode_upload(upload)))
    headers = {header.strip().lower() for header in (reader.fieldnames or [])}
    if 'alias' not in headers or 'institution_name' not in headers:
        raise InstitutionAliasImportError('Alias CSV requires alias and institution_name columns.')

    counts = {'created': 0, 'updated': 0, 'skipped': 0}
    for line_number, row in enumerate(reader, start=2):
        alias = (row.get('alias') or row.get('Alias') or '').strip()
        institution_name = (
            row.get('institution_name')
            or row.get('Institution Name')
            or row.get('institution')
            or row.get('Institution')
            or ''
        ).strip()
        if not alias:
            counts['skipped'] += 1
            continue
        institution = _institution_for_name(institution_name)
        if not institution:
            raise InstitutionAliasImportError(
                f'Row {line_number}: institution "{institution_name}" was not found for alias "{alias}".'
            )
        defaults = {
            'institution': institution,
            'notes': (row.get('notes') or row.get('Notes') or '').strip(),
            'is_active': (row.get('is_active') or row.get('Is Active') or 'true').strip().lower()
            not in {'0', 'false', 'no', 'n'},
        }
        _, created = InstitutionAlias.objects.update_or_create(
            normalized_alias=normalize_institution_alias(alias),
            defaults={'alias': alias, **defaults},
        )
        counts['created' if created else 'updated'] += 1
    return counts
