import json

import pytest
from django.urls import reverse

from apps.accounts.models import Institution, User
from apps.api.models import ApiToken
from apps.talks.models import Conference, Talk


@pytest.fixture
def manager(db):
    return User.objects.create_user(
        username='ib',
        email='ib@example.com',
        password='pass',
        role=User.Role.IB_REP,
    )


@pytest.fixture
def api_key(manager):
    _, key = ApiToken.create_token(manager, 'tests')
    return key


def _post_json(client, url, payload, api_key):
    return client.post(
        url,
        data=json.dumps(payload),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {api_key}',
    )


def test_api_docs_require_login(client):
    response = client.get(reverse('api:index'))
    assert response.status_code == 302


def test_manager_can_create_api_token_from_docs_page(client, manager):
    client.force_login(manager)
    response = client.post(reverse('api:index'), {'name': 'Import job'})
    assert response.status_code == 200
    assert ApiToken.objects.filter(user=manager, name='Import job').exists()
    assert b'mu2e_' in response.content


def test_api_rejects_missing_token(client):
    response = client.post(reverse('api:conference-create'), data='{}', content_type='application/json')
    assert response.status_code == 401


def test_user_role_token_cannot_create_records(client, db):
    user = User.objects.create_user(username='user', email='user@example.com', role=User.Role.USER)
    _, key = ApiToken.create_token(user, 'blocked')
    response = _post_json(client, reverse('api:conference-create'), {'title': 'Blocked'}, key)
    assert response.status_code == 403


def test_api_can_create_institution(client, api_key):
    response = _post_json(client, reverse('api:institution-create'), {
        'name': 'API University',
        'url': 'https://api.example.edu',
        'collaboration_code': 'API',
    }, api_key)

    assert response.status_code == 201
    institution = Institution.objects.get(name='API University')
    assert response.json()['id'] == institution.pk
    assert institution.collaboration_code == 'API'


def test_api_can_create_conference(client, api_key):
    response = _post_json(client, reverse('api:conference-create'), {
        'title': 'API Conference',
        'start_date': '2027-05-01',
        'end_date': '2027-05-03',
        'url': 'https://api.example.org/conf',
    }, api_key)

    assert response.status_code == 201
    conference = Conference.objects.get(title='API Conference')
    assert response.json()['id'] == conference.pk
    assert str(conference.start_date) == '2027-05-01'


def test_api_can_create_talk_with_inline_conference(client, api_key, manager):
    speaker = User.objects.create_user(username='speaker', email='speaker@example.com')
    institution = Institution.objects.create(name='Speaker Lab')
    response = _post_json(client, reverse('api:talk-create'), {
        'talk_title': 'API Talk',
        'conference_title': 'API Talk Conference',
        'conference_start_date': '2027-06-01',
        'conference_end_date': '2027-06-05',
        'assigned_to_email': speaker.email,
        'speaker_institution_name': institution.name,
        'type': Talk.Type.CONFERENCE,
        'status': Talk.Status.ACTIVE,
        'docdb_number': '12345',
        'plenary': True,
    }, api_key)

    assert response.status_code == 201
    talk = Talk.objects.select_related('conference', 'assigned_to', 'speaker_institution').get(talk_title='API Talk')
    assert talk.created_by == manager
    assert talk.conference.title == 'API Talk Conference'
    assert talk.assigned_to == speaker
    assert talk.speaker_institution == institution
    assert talk.plenary is True
