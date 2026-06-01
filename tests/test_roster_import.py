import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.accounts.models import Institution, User


def _upload(name, text):
    return SimpleUploadedFile(name, text.encode('utf-8'), content_type='text/csv')


@pytest.fixture
def admin(db):
    institution = Institution.objects.create(name='Admin Lab')
    return User.objects.create_user(
        username='admin@example.com',
        email='admin@example.com',
        password='pass',
        role=User.Role.ADMIN,
        institution=institution,
    )


def _member_csv(email='person@example.com', ib_rep='True'):
    return (
        'institution number,institution,institution website,institution code,member number,member,'
        'start date,position,int.,contact email,office phone,mobile phone,other phone,status,ORCID,'
        'Inspire ID,FNAL username,GitHub username,flag,minority serving,comments,IB Rep\n'
        f'7,Example University,physics.example.edu,U,42,\"Person, Pat\",2020-02-03,PD,D,{email},'
        f'111,222,333,QE,0000-0001-0002-0003,123,pperson,patgit,F,M,Imported comment,{ib_rep}\n'
    )


def test_admin_can_import_institutions(client, admin):
    client.force_login(admin)
    csv_text = 'name,URL\nExample University,physics.example.edu\n'
    response = client.post(reverse('roster-import'), {
        'import_type': 'institutions',
        'csv_file': _upload('institutions.csv', csv_text),
    })
    assert response.status_code == 302
    institution = Institution.objects.get(name='Example University')
    assert institution.url == 'https://physics.example.edu'


def test_admin_can_import_members_and_repeat_upload_updates(client, admin):
    client.force_login(admin)
    response = client.post(reverse('roster-import'), {
        'import_type': 'members',
        'csv_file': _upload('members.csv', _member_csv()),
    })
    assert response.status_code == 302
    user = User.objects.get(collaboration_member_number='42')
    assert user.email == ''
    assert user.contact_email == 'person@example.com'
    assert user.display_name == 'Person, Pat'
    assert user.institution.name == 'Example University'
    assert user.institution.url == 'https://physics.example.edu'
    assert user.collaboration_start_date.isoformat() == '2020-02-03'
    assert user.collaboration_position == 'PD'
    assert user.fnal_username == 'pperson'
    assert user.role == User.Role.IB_REP
    assert user.has_usable_password() is False

    updated = _member_csv(email='new-address@example.com', ib_rep='False')
    client.post(reverse('roster-import'), {
        'import_type': 'members',
        'csv_file': _upload('members.csv', updated),
    })
    user.refresh_from_db()
    assert User.objects.filter(collaboration_member_number='42').count() == 1
    assert user.email == ''
    assert user.contact_email == 'new-address@example.com'
    assert user.role == User.Role.IB_REP


def test_member_without_email_receives_stable_fallback_username(client, admin):
    client.force_login(admin)
    client.post(reverse('roster-import'), {
        'import_type': 'members',
        'csv_file': _upload('members.csv', _member_csv(email='', ib_rep='False')),
    })
    user = User.objects.get(collaboration_member_number='42')
    assert user.email == ''
    assert user.contact_email == ''
    assert user.username == 'pperson'


def test_regular_user_cannot_open_import_page(client, db):
    institution = Institution.objects.create(name='User Lab')
    user = User.objects.create_user(username='user', institution=institution)
    client.force_login(user)
    assert client.get(reverse('roster-import')).status_code == 403


def test_ib_rep_can_edit_institution(client, db):
    institution = Institution.objects.create(name='Original')
    ib_rep = User.objects.create_user(
        username='ib',
        role=User.Role.IB_REP,
        institution=institution,
    )
    client.force_login(ib_rep)
    response = client.post(reverse('institution-edit', args=[institution.pk]), {
        'name': 'Updated',
        'url': 'https://updated.example.edu',
        'collaboration_number': '9',
        'collaboration_code': 'U',
        'sort_order': '4',
        'is_active': 'on',
    })
    assert response.status_code == 302
    institution.refresh_from_db()
    assert institution.name == 'Updated'
    assert institution.url == 'https://updated.example.edu'
    assert institution.collaboration_number == '9'


def test_admin_can_edit_imported_user(client, admin):
    user = User.objects.create_user(username='member', display_name='Member')
    client.force_login(admin)
    response = client.post(reverse('user-edit', args=[user.pk]), {
        'email': 'member@example.com',
        'display_name': 'Updated Member',
        'institution': admin.institution_id,
        'role': User.Role.USER,
        'collaboration_member_number': '5',
        'collaboration_start_date': '',
        'collaboration_position': '',
        'collaboration_international': '',
        'office_phone': '',
        'mobile_phone': '',
        'other_phone': '',
        'collaboration_status': '',
        'orcid': '',
        'inspire_id': '',
        'fnal_username': '',
        'github_username': '',
        'collaboration_flag': '',
        'minority_serving': '',
        'roster_comments': '',
        'is_collaboration_member': 'on',
        'is_active': 'on',
    })
    assert response.status_code == 302
    user.refresh_from_db()
    assert user.display_name == 'Updated Member'
    assert user.collaboration_member_number == '5'
    assert user.institution == admin.institution


def test_admin_can_search_users_by_name_and_institution(client, admin):
    lab = Institution.objects.create(name='Searchable University')
    User.objects.create_user(
        username='pat@example.com',
        email='pat@example.com',
        display_name='Pat Search',
        institution=lab,
    )
    User.objects.create_user(
        username='other@example.com',
        email='other@example.com',
        display_name='Other Person',
        institution=admin.institution,
    )
    client.force_login(admin)

    response = client.get(reverse('admin-users'), {'q': 'Pat Search'})
    assert response.status_code == 200
    assert list(response.context['users'].values_list('email', flat=True)) == ['pat@example.com']

    response = client.get(reverse('admin-users'), {'q': 'Searchable University'})
    assert list(response.context['users'].values_list('email', flat=True)) == ['pat@example.com']
