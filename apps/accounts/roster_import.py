import csv
from datetime import date
from io import StringIO
from urllib.parse import urlparse

from django.db import transaction

from .models import Institution, User


class RosterImportError(ValueError):
    pass


def _reader(upload, required_headers):
    try:
        text = upload.read().decode('utf-8-sig')
    except UnicodeDecodeError as exc:
        raise RosterImportError('The uploaded file must be a UTF-8 CSV file.') from exc
    reader = csv.DictReader(StringIO(text, newline=''))
    missing = required_headers - set(reader.fieldnames or [])
    if missing:
        raise RosterImportError(f'Missing required columns: {", ".join(sorted(missing))}.')
    return reader


def _normalize_url(value):
    value = value.strip()
    if value and not urlparse(value).scheme:
        return f'https://{value}'
    return value


def _parse_date(value):
    value = value.strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise RosterImportError(f'Invalid date "{value}". Expected YYYY-MM-DD.') from exc


def _is_true(value):
    return value.strip().lower() in {'1', 'true', 'yes', 'y', 'on'}


def _normalize_collaboration_position(value, line_number):
    value = str(value or '').strip()
    if not value:
        return ''
    normalized = value.lower().replace('.', '').strip()
    aliases = {
        'pl': User.CollaborationPosition.LAB_STAFF,
        'lab staff': User.CollaborationPosition.LAB_STAFF,
        'pd': User.CollaborationPosition.POST_DOC,
        'post doc': User.CollaborationPosition.POST_DOC,
        'postdoc': User.CollaborationPosition.POST_DOC,
        'rs': User.CollaborationPosition.RESEARCH_SCIENTIST,
        'research scientist': User.CollaborationPosition.RESEARCH_SCIENTIST,
        'sg': User.CollaborationPosition.GRADUATE_STUDENT,
        'graduate student': User.CollaborationPosition.GRADUATE_STUDENT,
        'su': User.CollaborationPosition.UNDERGRADUATE_STUDENT,
        'undergraduate student': User.CollaborationPosition.UNDERGRADUATE_STUDENT,
        'pu': User.CollaborationPosition.UNIVERSITY_PROFESSOR,
        'univ professor': User.CollaborationPosition.UNIVERSITY_PROFESSOR,
        'university professor': User.CollaborationPosition.UNIVERSITY_PROFESSOR,
        'e': User.CollaborationPosition.ENGINEER,
        'engineer': User.CollaborationPosition.ENGINEER,
        't': User.CollaborationPosition.TECHNICAL,
        'technical': User.CollaborationPosition.TECHNICAL,
        'pi': User.CollaborationPosition.PRIVATE_INSTITUTION,
        'private inst': User.CollaborationPosition.PRIVATE_INSTITUTION,
        'private institution': User.CollaborationPosition.PRIVATE_INSTITUTION,
    }
    if normalized in aliases:
        return aliases[normalized]
    for code, label in User.CollaborationPosition.choices:
        if normalized == label.lower().replace('.', '').replace(f'({code.lower()})', '').strip():
            return code
        if normalized == label.lower().replace('.', '').strip():
            return code
    allowed = ', '.join(code for code, _ in User.CollaborationPosition.choices)
    raise RosterImportError(
        f'Row {line_number}: invalid collaboration position "{value}". '
        f'Expected one of: {allowed}.'
    )


def _unique_username(base):
    base = base or 'mu2e-member'
    candidate = base
    suffix = 2
    while User.objects.filter(username=candidate).exists():
        candidate = f'{base}-{suffix}'
        suffix += 1
    return candidate


def _institution_from_member(row):
    name = row['institution'].strip()
    institution, created = Institution.objects.get_or_create(name=name)
    changed = []
    values = {
        'url': _normalize_url(row.get('institution website', '')),
        'collaboration_number': row.get('institution number', '').strip(),
        'collaboration_code': row.get('institution code', '').strip(),
    }
    for field, value in values.items():
        if value and getattr(institution, field) != value:
            setattr(institution, field, value)
            changed.append(field)
    if changed:
        institution.save(update_fields=changed + ['updated_at'])
    return institution, created


@transaction.atomic
def import_institutions(upload):
    reader = _reader(upload, {'name', 'URL'})
    counts = {'created': 0, 'updated': 0}
    for line_number, row in enumerate(reader, start=2):
        name = row['name'].strip()
        if not name:
            raise RosterImportError(f'Row {line_number}: institution name is required.')
        institution, created = Institution.objects.get_or_create(name=name)
        url = _normalize_url(row.get('URL', ''))
        changed = []
        if institution.url != url:
            institution.url = url
            changed.append('url')
        if changed:
            institution.save(update_fields=changed + ['updated_at'])
        counts['created' if created else 'updated'] += 1
    return counts


@transaction.atomic
def import_members(upload):
    required = {'institution', 'member number', 'member', 'contact email'}
    reader = _reader(upload, required)
    counts = {'created': 0, 'updated': 0, 'institutions_created': 0}
    for line_number, row in enumerate(reader, start=2):
        institution_name = row['institution'].strip()
        member_number = row['member number'].strip()
        display_name = row['member'].strip()
        contact_email = row['contact email'].strip()
        if not institution_name or not member_number or not display_name:
            raise RosterImportError(
                f'Row {line_number}: institution, member number, and member are required.'
            )

        institution, institution_created = _institution_from_member(row)
        if institution_created:
            counts['institutions_created'] += 1

        user = User.objects.filter(collaboration_member_number=member_number).first()
        created = user is None
        if created:
            username_base = row.get('FNAL username', '').strip() or f'mu2e-member-{member_number}'
            user = User(username=_unique_username(username_base))
            user.set_unusable_password()

        values = {
            'contact_email': contact_email,
            'display_name': display_name,
            'institution': institution,
            'collaboration_member_number': member_number,
            'collaboration_start_date': _parse_date(row.get('start date', '')),
            'collaboration_position': _normalize_collaboration_position(row.get('position', ''), line_number),
            'collaboration_international': row.get('int.', '').strip(),
            'office_phone': row.get('office phone', '').strip(),
            'mobile_phone': row.get('mobile phone', '').strip(),
            'other_phone': row.get('other phone', '').strip(),
            'collaboration_status': row.get('status', '').strip(),
            'orcid': row.get('ORCID', '').strip(),
            'inspire_id': row.get('Inspire ID', '').strip(),
            'fnal_username': row.get('FNAL username', '').strip(),
            'github_username': row.get('GitHub username', '').strip(),
            'collaboration_flag': row.get('flag', '').strip(),
            'minority_serving': row.get('minority serving', '').strip(),
            'roster_comments': row.get('comments', '').strip(),
            'is_collaboration_member': True,
            'roster_merge_completed': False,
        }
        for field, value in values.items():
            setattr(user, field, value)

        is_ib_rep = _is_true(row.get('IB Rep', ''))
        if is_ib_rep and user.role == User.Role.USER:
            user.role = User.Role.IB_REP
        user.save()
        counts['created' if created else 'updated'] += 1
    return counts
