import pytest
from django.urls import reverse

from apps.accounts.models import Institution, User


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
