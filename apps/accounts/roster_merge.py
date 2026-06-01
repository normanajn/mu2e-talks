from difflib import SequenceMatcher

from django.db import transaction

from .models import User


ROSTER_FIELDS = (
    'contact_email', 'display_name', 'collaboration_member_number',
    'collaboration_start_date', 'collaboration_position', 'collaboration_international',
    'office_phone', 'mobile_phone', 'other_phone', 'collaboration_status', 'orcid',
    'inspire_id', 'fnal_username', 'github_username', 'collaboration_flag',
    'minority_serving', 'roster_comments', 'institution', 'is_collaboration_member',
)


def available_roster_records():
    return User.objects.filter(
        is_collaboration_member=True,
        roster_merge_completed=False,
        email='',
    ).select_related('institution')


def _normalized(value):
    return ''.join(ch for ch in (value or '').lower() if ch.isalnum())


def _normalized_name(value):
    words = ''.join(ch if ch.isalnum() else ' ' for ch in (value or '').lower()).split()
    return ''.join(sorted(words))


def _email_local(value):
    return (value or '').split('@', 1)[0].lower()


def roster_match_score(account, record):
    account_name = _normalized_name(account.display_name)
    record_name = _normalized_name(record.display_name)
    score = SequenceMatcher(None, account_name, record_name).ratio() * 70 if account_name and record_name else 0

    login_local = _normalized(_email_local(account.email))
    contact_local = _normalized(_email_local(record.contact_email))
    fnal_username = _normalized(record.fnal_username)
    if login_local and login_local == contact_local:
        score += 35
    if login_local and login_local == fnal_username:
        score += 35
    return round(min(score, 100), 1)


def suggested_roster_records(account, limit=8):
    scored = [
        (roster_match_score(account, record), record)
        for record in available_roster_records().exclude(pk=account.pk)
    ]
    scored.sort(key=lambda item: (-item[0], item[1].display_name.lower()))
    return scored[:limit]


@transaction.atomic
def merge_roster_record(account, record):
    from apps.talks.models import Talk

    if account.pk == record.pk or not available_roster_records().filter(pk=record.pk).exists():
        raise ValueError('The selected roster record is not available for merging.')

    Talk.objects.filter(assigned_to=record).update(assigned_to=account)
    Talk.objects.filter(created_by=record).update(created_by=account)

    for field in ROSTER_FIELDS:
        setattr(account, field, getattr(record, field))
    if account.role == User.Role.USER and record.role != User.Role.USER:
        account.role = record.role
    account.roster_merge_completed = True
    account.save()
    account.managed_groups.add(*record.managed_groups.all())
    account.managed_projects.add(*record.managed_projects.all())
    record.delete()
    return account
