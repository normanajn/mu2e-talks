from datetime import date

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.accounts.models import User
from apps.talks.models import Conference, Talk


@pytest.fixture
def user(db):
    return User.objects.create_user(username='user', email='user@example.com', password='pass')


@pytest.fixture
def ib_rep(db):
    return User.objects.create_user(username='ib', email='ib@example.com', password='pass', role=User.Role.IB_REP)


@pytest.fixture
def spokesperson(db):
    return User.objects.create_user(username='spokes', email='spokes@example.com', password='pass', role=User.Role.SPOKESPERSON)


@pytest.fixture
def conference(db):
    return Conference.objects.create(
        title='Muon Physics 2026',
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 5),
        url='https://example.org/conf',
    )


@pytest.fixture
def talk(db, user, conference):
    return Talk.objects.create(
        created_by=user,
        assigned_to=user,
        conference=conference,
        talk_title='Muon conversion update',
        docdb_number='12345-v2',
        comments='Ready for **review**',
    )


def test_conference_end_must_be_on_or_after_start():
    conf = Conference(title='Bad', start_date=date(2026, 5, 2), end_date=date(2026, 5, 1))
    with pytest.raises(ValidationError):
        conf.full_clean()


def test_draft_requires_only_talk_title(user):
    talk = Talk(created_by=user, assigned_to=user, talk_title='Draft idea')
    talk.full_clean()


def test_active_talk_requires_conference(user):
    talk = Talk(created_by=user, assigned_to=user, talk_title='Needs conference', status=Talk.Status.ACTIVE)
    with pytest.raises(ValidationError):
        talk.full_clean()


def test_active_talk_allows_conference_title_without_dates(user):
    conf = Conference(title='Title only conference')
    talk = Talk(
        created_by=user,
        assigned_to=user,
        conference=conf,
        talk_title='Active title-only talk',
        status=Talk.Status.ACTIVE,
    )
    talk.clean()


def test_ib_rep_can_create_active_talk_with_inline_conference(client, ib_rep):
    client.force_login(ib_rep)
    resp = client.post(reverse('talks:create'), {
        'talk_title': 'Inline conference talk',
        'conference_title': 'Inline Conference 2026',
        'conference_start_date': '2026-08-12',
        'conference_end_date': '2026-08-14',
        'status': Talk.Status.ACTIVE,
    })
    assert resp.status_code == 302
    talk = Talk.objects.select_related('conference').get(talk_title='Inline conference talk')
    assert talk.status == Talk.Status.ACTIVE
    assert talk.conference.title == 'Inline Conference 2026'
    assert talk.conference.start_date == date(2026, 8, 12)
    assert talk.conference.end_date == date(2026, 8, 14)


def test_ib_rep_can_create_active_talk_with_inline_conference_title_only(client, ib_rep):
    client.force_login(ib_rep)
    resp = client.post(reverse('talks:create'), {
        'talk_title': 'Title-only conference talk',
        'conference_title': 'Title Only Conference',
        'status': Talk.Status.ACTIVE,
    })
    assert resp.status_code == 302
    talk = Talk.objects.select_related('conference').get(talk_title='Title-only conference talk')
    assert talk.status == Talk.Status.ACTIVE
    assert talk.conference.title == 'Title Only Conference'


def test_ib_rep_can_create_plenary_parallel_talk(client, ib_rep):
    client.force_login(ib_rep)
    resp = client.post(reverse('talks:create'), {
        'talk_title': 'Session types',
        'conference_title': 'Typed Conference',
        'status': Talk.Status.ACTIVE,
        'plenary': 'on',
        'parallel': 'on',
    })
    assert resp.status_code == 302
    talk = Talk.objects.get(talk_title='Session types')
    assert talk.plenary is True
    assert talk.parallel is True


def test_ib_rep_can_create_talk_with_type(client, ib_rep):
    client.force_login(ib_rep)
    resp = client.post(reverse('talks:create'), {
        'talk_title': 'Colloquium entry',
        'conference_title': 'Colloquium Series',
        'status': Talk.Status.ACTIVE,
        'type': Talk.Type.COLLOQUIUM,
    })
    assert resp.status_code == 302
    talk = Talk.objects.get(talk_title='Colloquium entry')
    assert talk.type == Talk.Type.COLLOQUIUM
    assert talk.get_type_display() == 'Colloquium'


def test_user_create_makes_draft_assigned_to_self(client, user):
    client.force_login(user)
    resp = client.post(reverse('talks:create'), {'talk_title': 'My draft', 'status': Talk.Status.ACTIVE})
    assert resp.status_code == 302
    talk = Talk.objects.get(talk_title='My draft')
    assert talk.status == Talk.Status.DRAFT
    assert talk.assigned_to == user
    assert talk.created_by == user


def test_assigned_user_can_edit_talk(client, user, talk):
    client.force_login(user)
    resp = client.post(reverse('talks:edit', kwargs={'pk': talk.pk}), {
        'talk_title': 'Updated',
        'docdb_number': talk.docdb_number,
        'assigned_to': user.pk,
        'status': talk.status,
        'comments': talk.comments,
    })
    assert resp.status_code == 302
    talk.refresh_from_db()
    assert talk.talk_title == 'Updated'


def test_unassigned_user_cannot_edit_talk(client, db, talk):
    other = User.objects.create_user(username='other', email='other@example.com', password='pass')
    client.force_login(other)
    resp = client.get(reverse('talks:edit', kwargs={'pk': talk.pk}))
    assert resp.status_code == 403


def test_ib_rep_can_activate_draft(client, ib_rep, talk):
    client.force_login(ib_rep)
    resp = client.post(reverse('talks:activate', kwargs={'pk': talk.pk}))
    assert resp.status_code == 302
    talk.refresh_from_db()
    assert talk.status == Talk.Status.ACTIVE


def test_spokesperson_can_delete(client, spokesperson, talk):
    client.force_login(spokesperson)
    resp = client.post(reverse('talks:delete', kwargs={'pk': talk.pk}))
    assert resp.status_code == 302
    assert not Talk.objects.filter(pk=talk.pk).exists()
