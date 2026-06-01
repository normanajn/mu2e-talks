import pytest
from django.test import override_settings
from django.urls import reverse

from apps.accounts.models import Institution, User


class _GitHubResponse:
    status_code = 201

    @staticmethod
    def json():
        return {'number': 42}


@pytest.mark.django_db
@override_settings(GITHUB_TOKEN='test-token', GITHUB_ISSUES_REPO='normanajn/mu2e-talks')
def test_bug_report_uses_configured_github_repository(client, monkeypatch):
    institution = Institution.objects.create(name='Fermilab')
    user = User.objects.create_user(
        username='reporter',
        email='reporter@example.com',
        institution=institution,
    )
    client.force_login(user)

    request = {}

    def fake_post(url, **kwargs):
        request['url'] = url
        request['kwargs'] = kwargs
        return _GitHubResponse()

    monkeypatch.setattr('requests.post', fake_post)

    response = client.post(
        reverse('bug-report-submit'),
        {'title': 'Example issue', 'body': 'Example description'},
    )

    assert response.status_code == 302
    assert response.url == reverse('about')
    assert request['url'] == 'https://api.github.com/repos/normanajn/mu2e-talks/issues'
    assert request['kwargs']['headers']['Authorization'] == 'Bearer test-token'
