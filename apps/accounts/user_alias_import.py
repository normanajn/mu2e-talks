import csv
import io

from django.db import transaction

from .institution_alias_import import _institution_for_name
from .models import User, UserAlias, normalize_user_alias_name


class UserAliasImportError(ValueError):
    pass


def _decode_upload(upload):
    try:
        return upload.read().decode('utf-8-sig')
    except UnicodeDecodeError as exc:
        raise UserAliasImportError('User alias CSV must be UTF-8 encoded.') from exc


def _value(row, *keys):
    for key in keys:
        if key in row and row[key] is not None:
            return row[key].strip()
    return ''


def _user_for_row(row):
    email = _value(row, 'user_email', 'email', 'login_email', 'Login Email')
    if email:
        user = User.objects.filter(email__iexact=email).first() or User.objects.filter(contact_email__iexact=email).first()
        if user:
            return user

    username = _value(row, 'username', 'user_username')
    if username:
        user = User.objects.filter(username__iexact=username).first()
        if user:
            return user

    display_name = _value(row, 'user_display_name', 'display_name', 'member')
    if display_name:
        user = User.objects.filter(display_name__iexact=display_name).first()
        if user:
            return user
    return None


@transaction.atomic
def import_user_aliases(upload):
    reader = csv.DictReader(io.StringIO(_decode_upload(upload)))
    headers = {header.strip().lower() for header in (reader.fieldnames or [])}
    if not ({'first_name_alias', 'last_name_alias'} <= headers or 'full_name_alias' in headers):
        raise UserAliasImportError('User alias CSV requires full_name_alias or first_name_alias and last_name_alias columns.')

    counts = {'created': 0, 'updated': 0, 'skipped': 0}
    for line_number, row in enumerate(reader, start=2):
        first = _value(row, 'first_name_alias', 'first_name', 'First Name')
        last = _value(row, 'last_name_alias', 'last_name', 'Last Name')
        full = _value(row, 'full_name_alias', 'full_name', 'Full Name')
        normalized = normalize_user_alias_name(first, last, full)
        if not normalized:
            counts['skipped'] += 1
            continue
        user = _user_for_row(row)
        if not user:
            alias_label = full or f'{first} {last}'.strip()
            raise UserAliasImportError(f'Row {line_number}: could not find target user for alias "{alias_label}".')

        institution_name = _value(row, 'institution_name', 'institution', 'Institution')
        institution = _institution_for_name(institution_name) if institution_name else None
        defaults = {
            'first_name_alias': first,
            'last_name_alias': last,
            'full_name_alias': full,
            'user': user,
            'institution': institution,
            'notes': _value(row, 'notes', 'Notes'),
            'is_active': _value(row, 'is_active', 'Is Active').lower() not in {'0', 'false', 'no', 'n'},
        }
        _, created = UserAlias.objects.update_or_create(
            normalized_alias=normalized,
            defaults=defaults,
        )
        counts['created' if created else 'updated'] += 1
    return counts
