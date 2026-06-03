from django.urls import reverse

from apps.accounts.models import Institution, User


def test_user_can_edit_profile_record_fields(client, db):
    institution = Institution.objects.create(name='Original Lab')
    new_institution = Institution.objects.create(name='New Lab')
    user = User.objects.create_user(
        username='person@example.com',
        email='person@example.com',
        password='pass',
        institution=institution,
        role=User.Role.USER,
    )
    client.force_login(user)

    response = client.post(reverse('profile'), {
        'display_name': 'Updated Person',
        'contact_email': 'contact@example.edu',
        'institution': new_institution.pk,
        'collaboration_member_number': '123',
        'collaboration_start_date': '2024-01-15',
        'collaboration_position': User.CollaborationPosition.RESEARCH_SCIENTIST,
        'collaboration_international': 'Yes',
        'office_phone': '111-222-3333',
        'mobile_phone': '222-333-4444',
        'other_phone': '333-444-5555',
        'collaboration_status': 'Active',
        'orcid': '0000-0001-0002-0003',
        'inspire_id': 'INSPIRE-123',
        'fnal_username': 'person',
        'github_username': 'personhub',
        'collaboration_flag': 'Flag',
        'minority_serving': 'MSI',
        'roster_comments': 'Updated by profile.',
        'is_collaboration_member': 'on',
    })

    assert response.status_code == 302
    user.refresh_from_db()
    assert user.display_name == 'Updated Person'
    assert user.email == 'person@example.com'
    assert user.contact_email == 'contact@example.edu'
    assert user.institution == new_institution
    assert user.collaboration_member_number == '123'
    assert user.collaboration_start_date.isoformat() == '2024-01-15'
    assert user.collaboration_position == User.CollaborationPosition.RESEARCH_SCIENTIST
    assert user.collaboration_international == 'Yes'
    assert user.office_phone == '111-222-3333'
    assert user.mobile_phone == '222-333-4444'
    assert user.other_phone == '333-444-5555'
    assert user.collaboration_status == 'Active'
    assert user.orcid == '0000-0001-0002-0003'
    assert user.inspire_id == 'INSPIRE-123'
    assert user.fnal_username == 'person'
    assert user.github_username == 'personhub'
    assert user.collaboration_flag == 'Flag'
    assert user.minority_serving == 'MSI'
    assert user.roster_comments == 'Updated by profile.'
    assert user.is_collaboration_member is True


def test_profile_does_not_allow_self_role_change(client, db):
    institution = Institution.objects.create(name='Lab')
    user = User.objects.create_user(
        username='user@example.com',
        email='user@example.com',
        password='pass',
        role=User.Role.USER,
        institution=institution,
    )
    client.force_login(user)

    response = client.post(reverse('profile'), {
        'display_name': 'Regular User',
        'contact_email': '',
        'institution': institution.pk,
        'role': User.Role.ADMIN,
        'collaboration_member_number': '',
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
    })

    assert response.status_code == 302
    user.refresh_from_db()
    assert user.role == User.Role.USER
