from datetime import date

import pytest

from apps.accounts.models import User
from apps.audit.models import AuditLogEntry
from apps.talks.models import Conference, Talk


@pytest.fixture
def user(db):
    return User.objects.create_user(username='user', email='user@example.com', password='pass')


@pytest.fixture
def conference(db):
    return Conference.objects.create(title='Conf', start_date=date(2026, 1, 1), end_date=date(2026, 1, 2))


def test_create_talk_logs_create(user, conference):
    talk = Talk.objects.create(created_by=user, assigned_to=user, conference=conference, talk_title='Audit me')
    assert AuditLogEntry.objects.filter(action='create', object_type='Talk', object_id=talk.pk).exists()


def test_update_talk_logs_changed_fields(user, conference):
    talk = Talk.objects.create(created_by=user, assigned_to=user, conference=conference, talk_title='Old')
    AuditLogEntry.objects.all().delete()
    talk.talk_title = 'New'
    talk.save()
    event = AuditLogEntry.objects.get(action='update', object_id=talk.pk)
    assert 'talk_title' in event.changes


def test_delete_talk_logs_delete(user, conference):
    talk = Talk.objects.create(created_by=user, assigned_to=user, conference=conference, talk_title='Delete me')
    pk = talk.pk
    AuditLogEntry.objects.all().delete()
    talk.delete()
    assert AuditLogEntry.objects.filter(action='delete', object_id=pk).exists()
