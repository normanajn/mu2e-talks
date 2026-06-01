from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied


class _PermissionDeniedMixin:
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        raise PermissionDenied


class AdminRequiredMixin(_PermissionDeniedMixin, LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_mu2e_admin


class TalkReporterRequiredMixin(_PermissionDeniedMixin, LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated


class TalkManagerRequiredMixin(_PermissionDeniedMixin, LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.can_manage_talks


class TalkDeleteRequiredMixin(_PermissionDeniedMixin, LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.can_delete_talks


class UserPageRequiredMixin(AdminRequiredMixin):
    pass


class TaxonomyEditorRequiredMixin(AdminRequiredMixin):
    pass
