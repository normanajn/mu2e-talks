from django.shortcuts import redirect
from django.urls import reverse

_SELECT_INSTITUTION_URL = None  # resolved lazily to avoid AppRegistryNotReady
_MERGE_ROSTER_URL = None


def _select_institution_url():
    global _SELECT_INSTITUTION_URL
    if _SELECT_INSTITUTION_URL is None:
        _SELECT_INSTITUTION_URL = reverse('select-institution')
    return _SELECT_INSTITUTION_URL


def _merge_roster_url():
    global _MERGE_ROSTER_URL
    if _MERGE_ROSTER_URL is None:
        _MERGE_ROSTER_URL = reverse('merge-roster')
    return _MERGE_ROSTER_URL


# Paths that must always be reachable regardless of group/role status
_PASSTHROUGH_PREFIXES = (
    '/accounts/',   # allauth login/logout/SSO callbacks
    '/static/',
    '/media/',
    '/__debug__/',
)


class RolePreviewMiddleware:
    """
    Lets admins temporarily preview the UI as another role.

    Reads ``_preview_role`` from the session. If set, overrides
    ``request.user.role`` for this request only — the database is never
    modified. Sets ``request.user._is_previewing = True`` so templates can
    show the preview banner.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            from apps.accounts.models import User
            # Check the *real* database role before any override
            if request.user.role == User.Role.ADMIN:
                preview_role = request.session.get('_preview_role')
                if preview_role and preview_role in User.Role.values and preview_role != User.Role.ADMIN:
                    request.user._is_previewing = True
                    request.user._preview_label = dict(User.Role.choices).get(preview_role, preview_role)
                    request.user.role = preview_role

        return self.get_response(request)


class InstitutionSelectionMiddleware:
    """Redirect authenticated users without an institution to the institution selection page."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.user.is_authenticated
            and not request.user.institution_id
            and not getattr(request.user, '_is_previewing', False)
            and not request.session.get('_institution_selection_done')
            and not self._is_passthrough(request.path)
            and request.path != _select_institution_url()
            and request.path != _merge_roster_url()
        ):
            from apps.accounts.models import Institution
            if Institution.objects.filter(is_active=True).exists():
                return redirect(_select_institution_url())

        return self.get_response(request)

    @staticmethod
    def _is_passthrough(path):
        return any(path.startswith(p) for p in _PASSTHROUGH_PREFIXES)


class RosterMergeMiddleware:
    """Prompt new login accounts to connect an imported collaboration record."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.user.is_authenticated
            and not request.user.is_mu2e_admin
            and not request.user.roster_merge_completed
            and not request.user.is_collaboration_member
            and not getattr(request.user, '_is_previewing', False)
            and not self._is_passthrough(request.path)
            and request.path != _merge_roster_url()
        ):
            from apps.accounts.roster_merge import available_roster_records
            if available_roster_records().exists():
                return redirect(_merge_roster_url())

        return self.get_response(request)

    @staticmethod
    def _is_passthrough(path):
        return any(path.startswith(p) for p in _PASSTHROUGH_PREFIXES)
