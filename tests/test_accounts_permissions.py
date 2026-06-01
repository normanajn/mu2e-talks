import pytest

from apps.accounts.models import User


@pytest.mark.parametrize(
    ('role', 'can_manage', 'can_delete'),
    [
        (User.Role.USER, False, False),
        (User.Role.IB_REP, True, False),
        (User.Role.SPOKESPERSON, True, True),
        (User.Role.ADMIN, True, True),
    ],
)
def test_role_capabilities(db, role, can_manage, can_delete):
    user = User.objects.create_user(username=role, email=f'{role}@example.com', role=role)
    assert user.can_manage_talks is can_manage
    assert user.can_delete_talks is can_delete


def test_admin_property_alias(db):
    admin = User.objects.create_user(username='admin', email='admin@example.com', role=User.Role.ADMIN)
    assert admin.is_mu2e_admin is True
    assert admin.is_scd_admin is True
