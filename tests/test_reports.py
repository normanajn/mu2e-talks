from datetime import date

import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.reports.filters import TalkFilter
from apps.reports import exporters
from apps.talks.models import Conference, Talk


@pytest.fixture
def user(db):
    return User.objects.create_user(username='user', email='user@example.com', password='pass')


@pytest.fixture
def talk(db, user):
    conf = Conference.objects.create(
        title='International Mu2e Workshop',
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 4),
        url='https://example.org/workshop',
    )
    return Talk.objects.create(
        created_by=user,
        assigned_to=user,
        conference=conf,
        talk_title='Tracker status',
        docdb_number='MU2E-123',
        comments='Discusses straw tracker commissioning.',
        status=Talk.Status.ACTIVE,
    )


def test_reports_page_available_to_user(client, user):
    client.force_login(user)
    resp = client.get(reverse('reports:index'))
    assert resp.status_code == 200


def test_boolean_search_matches_talk_fields(talk):
    f = TalkFilter({'search': 'tracker AND commissioning'}, queryset=Talk.objects.all())
    assert list(f.qs) == [talk]


def test_boolean_search_can_exclude_nonmatching_xor(talk):
    f = TalkFilter({'search': 'tracker XOR commissioning'}, queryset=Talk.objects.all())
    assert list(f.qs) == []


def test_docdb_filter(talk):
    f = TalkFilter({'docdb_number': '123'}, queryset=Talk.objects.all())
    assert list(f.qs) == [talk]


def test_plenary_and_parallel_filters_and_export(talk):
    talk.plenary = True
    talk.parallel = True
    talk.save()
    assert list(TalkFilter({'plenary': 'true'}, queryset=Talk.objects.all()).qs) == [talk]
    assert list(TalkFilter({'parallel': 'true'}, queryset=Talk.objects.all()).qs) == [talk]
    rows = list(exporters._rows(Talk.objects.filter(pk=talk.pk)))
    assert rows[0]['plenary'] == 'yes'
    assert rows[0]['parallel'] == 'yes'


def test_type_filter_and_export(talk):
    talk.type = Talk.Type.SEMINAR
    talk.save()
    assert list(TalkFilter({'type': Talk.Type.SEMINAR}, queryset=Talk.objects.all()).qs) == [talk]
    rows = list(exporters._rows(Talk.objects.filter(pk=talk.pk)))
    assert rows[0]['type'] == 'Seminar'


def test_preview_renders_rows(client, user, talk):
    client.force_login(user)
    resp = client.post(reverse('reports:preview'), {'search': 'tracker'})
    assert resp.status_code == 200
    assert b'Tracker status' in resp.content


def test_csv_export_has_talk_headers(client, user, talk):
    client.force_login(user)
    resp = client.post(reverse('reports:download', kwargs={'fmt': 'csv'}), {'search': 'tracker'})
    body = resp.content.decode()
    assert resp.status_code == 200
    assert 'conference_title,talk_title' in body
    assert 'Tracker status' in body


def test_spreadsheet_safe_comments(talk):
    talk.comments = '@SUM(1,1)'
    talk.save()
    rows = list(exporters._spreadsheet_rows(Talk.objects.filter(pk=talk.pk)))
    assert rows[0]['comments'] == "'@SUM(1,1)"
