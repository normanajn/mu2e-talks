import pytest
from django.urls import reverse

from apps.accounts.models import Institution, User
from apps.accounts.roster_merge import suggested_roster_records
from apps.talks.models import Talk


@pytest.fixture
def institution(db):
    return Institution.objects.create(name='Fermilab')


@pytest.fixture
def roster_record(institution):
    return User.objects.create_user(
        username='gandr',
        email='',
        contact_email='gandr@fnal.gov',
        display_name='Gaponenko, Andrei',
        fnal_username='gandr',
        collaboration_member_number='106',
        institution=institution,
        is_collaboration_member=True,
        roster_merge_completed=False,
        role=User.Role.IB_REP,
    )


@pytest.fixture
def login_account(db):
    return User.objects.create_user(
        username='andrei.gaponenko@services.fnal.gov',
        email='andrei.gaponenko@services.fnal.gov',
        display_name='Andrei Gaponenko',
    )


def test_fuzzy_match_suggests_roster_record(login_account, roster_record):
    suggestions = suggested_roster_records(login_account)
    assert suggestions[0][1] == roster_record
    assert suggestions[0][0] > 50


def test_login_account_is_prompted_to_merge_before_institution_selection(client, login_account, roster_record):
    client.force_login(login_account)
    response = client.get('/')
    assert response.status_code == 302
    assert response.url == reverse('merge-roster')


def test_login_account_can_merge_roster_record(client, login_account, roster_record):
    client.force_login(login_account)
    response = client.post(reverse('merge-roster'), {'roster_record': roster_record.pk})
    assert response.status_code == 302
    login_account.refresh_from_db()
    assert login_account.email == 'andrei.gaponenko@services.fnal.gov'
    assert login_account.contact_email == 'gandr@fnal.gov'
    assert login_account.collaboration_member_number == '106'
    assert login_account.institution == roster_record.institution
    assert login_account.role == User.Role.IB_REP
    assert login_account.roster_merge_completed is True
    assert User.objects.filter(pk=roster_record.pk).exists() is False


def test_login_account_can_skip_roster_merge(client, login_account, roster_record):
    client.force_login(login_account)
    response = client.post(reverse('merge-roster'), {'skip': '1'})
    assert response.status_code == 302
    login_account.refresh_from_db()
    assert login_account.roster_merge_completed is True
    assert User.objects.filter(pk=roster_record.pk).exists() is True


def test_merge_reassigns_existing_talks(login_account, roster_record):
    talk = Talk.objects.create(
        talk_title='Assigned presentation',
        assigned_to=roster_record,
        created_by=login_account,
    )
    from apps.accounts.roster_merge import merge_roster_record

    merge_roster_record(login_account, roster_record)
    talk.refresh_from_db()
    assert talk.assigned_to == login_account
