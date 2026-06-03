import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.accounts.models import Institution, InstitutionAlias, User, UserAlias


@pytest.fixture
def user(db):
    return User.objects.create_user(username='u', email='u@example.com', password='pass')


@pytest.fixture
def institution(db):
    return Institution.objects.create(name='Fermilab')


def test_no_prompt_when_no_institutions_exist(client, user):
    client.force_login(user)
    assert client.get('/').status_code == 200


def test_user_without_institution_is_prompted(client, user, institution):
    client.force_login(user)
    resp = client.get('/')
    assert resp.status_code == 302
    assert resp.url == reverse('select-institution')


def test_user_can_select_institution(client, user, institution):
    client.force_login(user)
    resp = client.post(reverse('select-institution'), {'institution': institution.pk})
    assert resp.status_code == 302
    user.refresh_from_db()
    assert user.institution == institution


@pytest.mark.parametrize('role', [User.Role.IB_REP, User.Role.SPOKESPERSON, User.Role.ADMIN])
def test_management_roles_can_open_institutions_page(client, db, role):
    manager = User.objects.create_user(username=role, email=f'{role}@example.com', role=role)
    manager.institution = Institution.objects.create(name=f'{role} Lab')
    manager.save()
    client.force_login(manager)
    assert client.get(reverse('institutions')).status_code == 200


def test_institutions_page_paginates(client, db):
    manager = User.objects.create_user(username='ib', email='ib@example.com', role=User.Role.IB_REP)
    manager.institution = Institution.objects.create(name='Manager Lab')
    manager.save()
    for idx in range(60):
        Institution.objects.create(name=f'Paged Institution {idx:02d}')

    client.force_login(manager)
    first_page = client.get(reverse('institutions'))
    assert first_page.status_code == 200
    assert first_page.context['is_paginated']
    assert len(first_page.context['institutions']) == 50
    assert b'Paged Institution 00' in first_page.content
    assert b'Paged Institution 59' not in first_page.content
    assert b'Next' in first_page.content

    second_page = client.get(reverse('institutions'), {'page': '2'})
    assert second_page.status_code == 200
    assert b'Paged Institution 59' in second_page.content
    assert b'Previous' in second_page.content


def test_regular_user_cannot_open_institutions_page(client, user, institution):
    user.institution = institution
    user.save()
    client.force_login(user)
    assert client.get(reverse('institutions')).status_code == 403


def test_ib_rep_can_create_institution(client, db):
    ib_rep = User.objects.create_user(username='ib', email='ib@example.com', role=User.Role.IB_REP)
    ib_rep.institution = Institution.objects.create(name='Existing')
    ib_rep.save()
    client.force_login(ib_rep)
    resp = client.post(reverse('institutions'), {'name': 'University A', 'sort_order': '10', 'is_active': 'on'})
    assert resp.status_code == 302
    assert Institution.objects.filter(name='University A', is_active=True).exists()


def test_manager_can_import_institution_aliases(client, db):
    institution = Institution.objects.create(name='University of Minnesota')
    manager = User.objects.create_user(username='ib', email='ib@example.com', role=User.Role.IB_REP)
    manager.institution = institution
    manager.save()
    upload = SimpleUploadedFile(
        'aliases.csv',
        b'alias,institution_name,notes,is_active\nMinn,University of Minnesota,spreadsheet,true\n',
        content_type='text/csv',
    )

    client.force_login(manager)
    response = client.post(reverse('institution-aliases'), {'action': 'import', 'csv_file': upload})

    assert response.status_code == 302
    alias = InstitutionAlias.objects.get(alias='Minn')
    assert alias.institution == institution
    assert alias.normalized_alias == 'minn'


def test_manager_can_import_user_aliases(client, db):
    institution = Institution.objects.create(name='Fermilab')
    manager = User.objects.create_user(username='ib', email='ib@example.com', role=User.Role.IB_REP)
    manager.institution = institution
    manager.save()
    user = User.objects.create_user(
        username='mete',
        email='mete@example.com',
        display_name='Mete Yucel',
        institution=institution,
    )
    upload = SimpleUploadedFile(
        'user-aliases.csv',
        b'first_name_alias,last_name_alias,user_email,institution_name,notes,is_active\nMete,Yucel,mete@example.com,Fermilab,spreadsheet,true\n',
        content_type='text/csv',
    )

    client.force_login(manager)
    response = client.post(reverse('user-aliases'), {'action': 'import', 'csv_file': upload})

    assert response.status_code == 302
    alias = UserAlias.objects.get(first_name_alias='Mete', last_name_alias='Yucel')
    assert alias.user == user
    assert alias.institution == institution
    assert alias.normalized_alias == 'mete yucel'
