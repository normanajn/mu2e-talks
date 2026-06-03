from datetime import date

import pytest
from django.urls import reverse

from apps.accounts.models import Institution, User
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


def test_reports_form_enter_defaults_to_preview(client, user):
    client.force_login(user)
    response = client.get(reverse('reports:index'))
    assert response.status_code == 200
    assert b'id="report-form" method="post" class="space-y-5"' in response.content
    assert b'<button type="submit"' in response.content
    assert b'hx-post="/reports/preview/"' in response.content
    assert b'hx-target="#preview"' in response.content


def test_reports_form_has_clear_button(client, user):
    client.force_login(user)
    response = client.get(reverse('reports:index'))
    assert response.status_code == 200
    assert b'id="report-reset"' in response.content
    assert b"replaceChildren()" in response.content


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


def test_institution_filters(talk, user):
    assigned_institution = Institution.objects.create(name='Assigned Institution')
    speaker_institution = Institution.objects.create(name='Speaker Institution')
    other_institution = Institution.objects.create(name='Other Institution')
    user.institution = assigned_institution
    user.save()
    talk.speaker_institution = speaker_institution
    talk.save()

    assigned_filter = TalkFilter(
        {'assigned_institution': assigned_institution.pk},
        queryset=Talk.objects.all(),
    )
    assert list(assigned_filter.qs) == [talk]

    speaker_filter = TalkFilter(
        {'speaker_institution': speaker_institution.pk},
        queryset=Talk.objects.all(),
    )
    assert list(speaker_filter.qs) == [talk]

    no_match = TalkFilter(
        {'assigned_institution': other_institution.pk},
        queryset=Talk.objects.all(),
    )
    assert list(no_match.qs) == []


def test_preview_renders_rows(client, user, talk):
    client.force_login(user)
    resp = client.post(reverse('reports:preview'), {'search': 'tracker'})
    assert resp.status_code == 200
    assert b'Tracker status' in resp.content


def test_preview_paginates_after_50_results(client, user, talk):
    talks = [
        Talk(
            created_by=user,
            assigned_to=user,
            conference=talk.conference,
            talk_title=f'Paginated talk {idx:02d}',
            status=Talk.Status.ACTIVE,
        )
        for idx in range(60)
    ]
    Talk.objects.bulk_create(talks)

    client.force_login(user)
    first_page = client.post(reverse('reports:preview'), {'search': 'Paginated'})
    assert first_page.status_code == 200
    assert b'>60</span> talks matched' in first_page.content
    assert b'showing 1-50' in first_page.content
    assert b'Next' in first_page.content
    assert b'Paginated talk 00' in first_page.content
    assert b'Paginated talk 59' not in first_page.content

    second_page = client.post(reverse('reports:preview'), {'search': 'Paginated', 'page': '2'})
    assert second_page.status_code == 200
    assert b'showing 51-60' in second_page.content
    assert b'Previous' in second_page.content
    assert b'Paginated talk 59' in second_page.content


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
