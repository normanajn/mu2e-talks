from datetime import date, timedelta
from io import BytesIO, StringIO

import openpyxl
import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.accounts.models import Institution, InstitutionAlias, User, UserAlias
from apps.talks.conference_import import import_conferences
from apps.talks.models import Conference, Talk
from apps.talks.spreadsheet_import import import_talk_records, workbook_to_records


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


def test_talk_list_paginates_and_preserves_page_size(client, ib_rep, conference):
    Talk.objects.bulk_create([
        Talk(
            created_by=ib_rep,
            assigned_to=ib_rep,
            conference=conference,
            talk_title=f'Paged talk {idx:03d}',
            status=Talk.Status.ACTIVE,
        )
        for idx in range(75)
    ])
    client.force_login(ib_rep)

    first_page = client.get(reverse('talks:list'), {'q': 'Paged talk'})
    assert first_page.status_code == 200
    assert len(first_page.context['talks']) == 50
    assert first_page.context['is_paginated'] is True
    assert first_page.context['per_page'] == '50'
    assert 'q=Paged+talk' in first_page.context['pagination_query']
    assert b'Next' in first_page.content

    second_page = client.get(reverse('talks:list'), {'q': 'Paged talk', 'page': '2'})
    assert len(second_page.context['talks']) == 25
    assert b'Previous' in second_page.content

    hundred = client.get(reverse('talks:list'), {'q': 'Paged talk', 'per_page': '100'})
    assert len(hundred.context['talks']) == 75
    assert hundred.context['is_paginated'] is False
    assert hundred.context['per_page'] == '100'


def test_talk_list_all_page_size_disables_pagination(client, ib_rep, conference):
    Talk.objects.bulk_create([
        Talk(
            created_by=ib_rep,
            assigned_to=ib_rep,
            conference=conference,
            talk_title=f'All talk {idx:03d}',
            status=Talk.Status.ACTIVE,
        )
        for idx in range(60)
    ])
    client.force_login(ib_rep)
    response = client.get(reverse('talks:list'), {'q': 'All talk', 'per_page': 'all'})
    assert response.status_code == 200
    assert len(response.context['talks']) == 60
    assert response.context['is_paginated'] is False
    assert response.context['per_page'] == 'all'


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


def test_docdb_number_links_to_mu2e_docdb(client, user, talk):
    client.force_login(user)
    response = client.get(reverse('talks:detail', kwargs={'pk': talk.pk}))
    assert response.status_code == 200
    assert b'https://mu2e-docdb.fnal.gov/cgi-bin/sso/ShowDocument?docid=12345' in response.content


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


def test_user_cannot_manage_conferences(client, user, conference):
    client.force_login(user)
    assert client.get(reverse('talks:conferences')).status_code == 403
    assert client.get(reverse('talks:conference-create')).status_code == 403
    assert client.get(reverse('talks:conference-edit', kwargs={'pk': conference.pk})).status_code == 403
    assert client.get(reverse('talks:conference-delete', kwargs={'pk': conference.pk})).status_code == 403


@pytest.mark.parametrize('role', [User.Role.IB_REP, User.Role.SPOKESPERSON, User.Role.ADMIN])
def test_manager_roles_can_create_and_edit_conference(client, db, role):
    manager = User.objects.create_user(username=role, email=f'{role}@example.com', role=role)
    client.force_login(manager)
    response = client.post(reverse('talks:conference-create'), {
        'title': 'New Conference',
        'start_date': '2026-10-01',
        'end_date': '2026-10-03',
        'url': 'https://example.org/new',
    })
    assert response.status_code == 302
    conference = Conference.objects.get(title='New Conference')

    response = client.post(reverse('talks:conference-edit', kwargs={'pk': conference.pk}), {
        'title': 'Updated Conference',
        'start_date': '2026-10-01',
        'end_date': '2026-10-04',
        'url': 'https://example.org/updated',
    })
    assert response.status_code == 302
    conference.refresh_from_db()
    assert conference.title == 'Updated Conference'
    assert conference.end_date == date(2026, 10, 4)


def test_import_conferences_updates_existing_inspire_record(db):
    csv_data = (
        'inspire_id,title,start_date,end_date,url\n'
        '1234,Original Conference,2026-08-01,2026-08-03,https://example.org/original\n'
    )
    assert import_conferences(StringIO(csv_data)) == (1, 0)

    csv_data = (
        'inspire_id,title,start_date,end_date,url\n'
        '1234,Updated Conference,2026-08-02,2026-08-04,https://example.org/updated\n'
    )
    assert import_conferences(StringIO(csv_data)) == (0, 1)
    conference = Conference.objects.get(inspire_id='1234')
    assert conference.title == 'Updated Conference'
    assert conference.start_date == date(2026, 8, 2)


def test_existing_conference_is_available_in_talk_dropdown(client, ib_rep, conference):
    client.force_login(ib_rep)
    response = client.get(reverse('talks:create'))
    assert response.status_code == 200
    assert conference in response.context['form'].fields['conference'].queryset


@pytest.mark.parametrize(
    ('query', 'expected_title'),
    [
        ('Muon', 'Muon Physics 2026'),
        ('example.org/conf', 'Muon Physics 2026'),
        ('98765', 'INSPIRE Search Match'),
    ],
)
def test_conference_search(client, ib_rep, conference, query, expected_title):
    conference.inspire_id = '98765'
    conference.title = 'INSPIRE Search Match' if query == '98765' else conference.title
    conference.save()
    Conference.objects.create(title='Other Conference', url='https://example.org/other')

    client.force_login(ib_rep)
    response = client.get(reverse('talks:conferences'), {'q': query})
    assert response.status_code == 200
    titles = [conf.title for conf in response.context['conferences']]
    assert titles == [expected_title]
    assert response.context['query'] == query


def test_conference_list_paginates(client, ib_rep):
    for idx in range(60):
        Conference.objects.create(
            title=f'Paged Conference {idx:02d}',
            start_date=date(2026, 1, 1) + timedelta(days=idx),
        )

    client.force_login(ib_rep)
    first_page = client.get(reverse('talks:conferences'), {'q': 'Paged Conference'})
    assert first_page.status_code == 200
    assert first_page.context['is_paginated']
    assert len(first_page.context['conferences']) == 50
    first_page_titles = [conf.title for conf in first_page.context['conferences']]
    assert 'Paged Conference 59' in first_page_titles
    assert 'Paged Conference 00' not in first_page_titles
    assert b'Next' in first_page.content

    second_page = client.get(reverse('talks:conferences'), {'q': 'Paged Conference', 'page': '2'})
    assert second_page.status_code == 200
    second_page_titles = [conf.title for conf in second_page.context['conferences']]
    assert 'Paged Conference 00' in second_page_titles
    assert b'Previous' in second_page.content


def test_ib_rep_can_delete_unused_conference(client, ib_rep, conference):
    client.force_login(ib_rep)
    response = client.post(reverse('talks:conference-delete', kwargs={'pk': conference.pk}))
    assert response.status_code == 302
    assert response.url == reverse('talks:conferences')
    assert not Conference.objects.filter(pk=conference.pk).exists()


def test_referenced_conference_cannot_be_deleted(client, ib_rep, conference, talk):
    client.force_login(ib_rep)
    response = client.post(reverse('talks:conference-delete', kwargs={'pk': conference.pk}), follow=True)
    assert response.status_code == 200
    assert Conference.objects.filter(pk=conference.pk).exists()
    assert b'cannot be deleted because it is assigned to one or more talks' in response.content


def _sample_talk_workbook():
    workbook = openpyxl.Workbook()
    ws = workbook.active
    ws.title = '2023'
    ws.append([
        'Date', 'Speaker', None, 'Home Institution', 'Venue', 'Title', 'Length (min)',
        'Type', None, 'Doc-db', 'Conference URL', 'Approved by Committee?',
        'Mu2e or Mu2e-II', 'Proceedings', 'Arxiv',
    ])
    ws.append([])
    ws.append([
        date(2023, 4, 15), 'Kampa', 'Cole', 'Northwestern', 'APS April 2023',
        'Imported Talk', '20+10', 'Plenary', None, 44337,
        'https://example.org/conf', 'Yes', 'Mu2e-II',
        'https://doi.org/10.1/example', 'https://arxiv.org/abs/2301.00001',
    ])
    buf = BytesIO()
    workbook.save(buf)
    buf.seek(0)
    buf.name = 'sample.xlsx'
    return buf


def test_workbook_to_records_maps_talk_spreadsheet_columns():
    records = workbook_to_records(_sample_talk_workbook())
    assert len(records) == 1
    record = records[0]
    assert record['source_row'] == 3
    assert record['speaker_last_name'] == 'Kampa'
    assert record['speaker_first_name'] == 'Cole'
    assert record['presentation_date'] == '2023-04-15'
    assert record['duration_minutes'] == 20
    assert record['type'] == Talk.Type.CONFERENCE
    assert record['plenary'] is True
    assert record['docdb_number'] == '44337'
    assert record['final_approval'] is True
    assert record['mu2e_program'] == 'Mu2e-II'


def test_workbook_to_records_handles_legacy_first_last_speaker_order():
    workbook = openpyxl.Workbook()
    ws = workbook.active
    ws.title = '2013-2015'
    ws.append(['Mu2e Talks Spreadsheet'])
    ws.append([])
    ws.append([])
    ws.append([])
    ws.append(['Date', 'Speaker', None, 'Home Institution', 'Venue', 'Title', 'Length (min)', 'Type', None, 'Doc-db Number', 'Conference Web page'])
    ws.append([date(2013, 2, 1), 'Eric', 'Prebys', 'Fermilab', 'Virginia Tech', 'The Mu2e Experiment', 45, 'Seminar', None, 2691, None])
    buf = BytesIO()
    workbook.save(buf)
    buf.seek(0)
    buf.name = 'legacy.xlsx'

    record = workbook_to_records(buf)[0]
    assert record['speaker_first_name'] == 'Eric'
    assert record['speaker_last_name'] == 'Prebys'


def test_import_talk_records_matches_user_and_institution_and_is_idempotent(db, ib_rep):
    institution = Institution.objects.create(name='Northwestern University')
    speaker = User.objects.create_user(
        username='cole',
        email='cole@example.com',
        display_name='Cole Kampa',
        institution=institution,
    )
    records = workbook_to_records(_sample_talk_workbook())
    counts = import_talk_records(records, created_by=ib_rep)
    assert counts['created'] == 1
    assert counts['matched_users'] == 1
    talk = Talk.objects.get(source_sheet='2023', source_row=3)
    assert talk.assigned_to == speaker
    assert talk.speaker_institution == institution
    assert talk.conference.title == 'APS April 2023'
    assert talk.complete_given is True

    counts = import_talk_records(records, created_by=ib_rep)
    assert counts['created'] == 0
    assert counts['updated'] == 1
    assert Talk.objects.filter(source_sheet='2023', source_row=3).count() == 1


def test_import_talk_records_matches_institution_alias(db, ib_rep):
    institution = Institution.objects.create(name='University of Minnesota')
    InstitutionAlias.objects.create(alias='Minn', institution=institution)
    records = [{
        'source_spreadsheet': 'sample.xlsx',
        'source_sheet': 'Sheet1',
        'source_row': 4,
        'presentation_date': '2026-01-10',
        'speaker_first_name': 'No',
        'speaker_last_name': 'Match',
        'speaker_home_institution_raw': 'Minn',
        'conference_title': 'Alias Conference',
        'talk_title': 'Alias Talk',
        'type': Talk.Type.CONFERENCE,
    }]

    counts = import_talk_records(records, created_by=ib_rep)

    talk = Talk.objects.get(talk_title='Alias Talk')
    assert counts['matched_institutions'] == 1
    assert talk.speaker_institution == institution
    assert talk.spreadsheet_import_notes == 'user not matched: No Match'


def test_import_talk_records_matches_user_alias(db, ib_rep):
    institution = Institution.objects.create(name='Fermi National Accelerator Laboratory')
    user = User.objects.create_user(
        username='mete',
        email='mete@example.com',
        display_name='Mete Yucel',
        institution=institution,
    )
    UserAlias.objects.create(
        first_name_alias='Mete',
        last_name_alias='Yucel',
        user=user,
        institution=institution,
    )
    records = [{
        'source_spreadsheet': 'sample.xlsx',
        'source_sheet': 'Sheet1',
        'source_row': 5,
        'presentation_date': '2026-01-10',
        'speaker_first_name': 'Mete',
        'speaker_last_name': 'Yucel',
        'speaker_home_institution_raw': 'FNAL',
        'conference_title': 'Alias Conference',
        'talk_title': 'User Alias Talk',
        'type': Talk.Type.CONFERENCE,
    }]

    counts = import_talk_records(records, created_by=ib_rep)

    talk = Talk.objects.get(talk_title='User Alias Talk')
    assert counts['matched_users'] == 1
    assert talk.assigned_to == user


def test_import_talk_records_skips_malformed_long_speaker_name(db, ib_rep):
    Institution.objects.create(name='Boston University')
    records = [{
        'source_spreadsheet': 'sample.xlsx',
        'source_sheet': 'Sheet1',
        'source_row': 6,
        'presentation_date': '2026-01-10',
        'speaker_first_name': 'Nam',
        'speaker_last_name': 'https://indico.fnal.gov/event/45713/contributions/198492/',
        'speaker_home_institution_raw': 'BU',
        'conference_title': 'Malformed Speaker Conference',
        'talk_title': 'Malformed Speaker Talk',
        'type': Talk.Type.CONFERENCE,
    }]

    counts = import_talk_records(records, created_by=ib_rep)

    talk = Talk.objects.get(talk_title='Malformed Speaker Talk')
    assert counts['unmatched_users'] == 1
    assert talk.assigned_to is None


def test_talk_spreadsheet_upload_requires_manager_role(client, user):
    client.force_login(user)
    assert client.get(reverse('talks:spreadsheet-import')).status_code == 403


def test_ib_rep_can_upload_talk_spreadsheet(client, ib_rep):
    client.force_login(ib_rep)
    upload = SimpleUploadedFile(
        'sample.xlsx',
        _sample_talk_workbook().getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response = client.post(reverse('talks:spreadsheet-import'), {'spreadsheet_file': upload}, follow=True)
    assert response.status_code == 200
    assert Talk.objects.filter(talk_title='Imported Talk').exists()
