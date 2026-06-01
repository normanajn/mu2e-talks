from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, UpdateView

from apps.taxonomy.models import WorkGroup

from .forms import AdminCreateUserForm, AdminEditUserForm, InstitutionForm, ProfileForm, RosterImportForm
from .models import Institution, SiteSettings
from .permissions import AdminRequiredMixin, TalkManagerRequiredMixin, UserPageRequiredMixin
from .roster_import import RosterImportError, import_institutions, import_members
from .roster_merge import available_roster_records, merge_roster_record, suggested_roster_records

User = get_user_model()


class ProfileView(AdminRequiredMixin, UpdateView):
    model = User
    form_class = ProfileForm
    template_name = 'accounts/profile.html'
    success_url = reverse_lazy('profile')

    # Override test_func from AdminRequiredMixin — profile is for all auth users
    def test_func(self):
        return self.request.user.is_authenticated

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, 'Profile updated.')
        return super().form_valid(form)


class AdminUsersView(UserPageRequiredMixin, ListView):
    model = User
    template_name = 'accounts/admin_users.html'
    context_object_name = 'users'
    ordering = ['email']

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get('q', '').strip()
        if query:
            queryset = queryset.filter(
                Q(display_name__icontains=query)
                | Q(email__icontains=query)
                | Q(contact_email__icontains=query)
                | Q(username__icontains=query)
                | Q(institution__name__icontains=query)
                | Q(collaboration_member_number__icontains=query)
                | Q(fnal_username__icontains=query)
                | Q(github_username__icontains=query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['query'] = self.request.GET.get('q', '').strip()
        ctx['role_choices'] = User.Role.choices
        ctx['site_settings'] = SiteSettings.get_solo()
        ctx['create_form'] = AdminCreateUserForm()
        ctx['all_institutions'] = Institution.objects.filter(is_active=True)
        return ctx


class UserRoleUpdateView(AdminRequiredMixin, View):
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if user == request.user:
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden('You cannot change your own role.')
        role = request.POST.get('role', '')
        if role in User.Role.values:
            user.role = role
            user.save(update_fields=['role'])
        return render(request, 'accounts/partials/_role_update_response.html', {
            'u': user,
            'role_choices': User.Role.choices,
            'managed_group_ids':   list(user.managed_groups.values_list('pk', flat=True)),
            'managed_project_ids': list(user.managed_projects.values_list('pk', flat=True)),
        })


class UserSetPasswordView(AdminRequiredMixin, View):
    template_name = 'accounts/set_password.html'

    def _get_target(self, pk):
        return get_object_or_404(User, pk=pk)

    def get(self, request, pk):
        return render(request, self.template_name, {'target': self._get_target(pk)})

    def post(self, request, pk):
        target = self._get_target(pk)
        p1 = request.POST.get('new_password1', '')
        p2 = request.POST.get('new_password2', '')
        if not p1:
            messages.error(request, 'Password cannot be empty.')
            return render(request, self.template_name, {'target': target})
        if p1 != p2:
            messages.error(request, 'Passwords do not match.')
            return render(request, self.template_name, {'target': target})
        try:
            validate_password(p1, user=target)
        except ValidationError as e:
            for msg in e.messages:
                messages.error(request, msg)
            return render(request, self.template_name, {'target': target})
        target.set_password(p1)
        target.save(update_fields=['password'])
        messages.success(request, f'Password updated for {target.email}.')
        return redirect('admin-users')


class UserDeleteView(AdminRequiredMixin, View):
    template_name = 'accounts/confirm_delete_user.html'

    def _get_target(self, pk):
        return get_object_or_404(User, pk=pk)

    def get(self, request, pk):
        target = self._get_target(pk)
        if target == request.user:
            messages.error(request, 'You cannot delete your own account.')
            return redirect('admin-users')
        return render(request, self.template_name, {'target': target})

    def post(self, request, pk):
        target = self._get_target(pk)
        if target == request.user:
            messages.error(request, 'You cannot delete your own account.')
            return redirect('admin-users')
        email = target.email
        try:
            target.delete()
            messages.success(request, f'Account "{email}" has been deleted.')
        except ProtectedError:
            messages.error(
                request,
                f'Cannot delete "{email}" — they have existing talks. '
                'Remove or reassign their talks first.',
            )
        return redirect('admin-users')


class UserUpdateView(AdminRequiredMixin, UpdateView):
    model = User
    form_class = AdminEditUserForm
    template_name = 'accounts/edit_user.html'
    success_url = reverse_lazy('admin-users')

    def form_valid(self, form):
        messages.success(self.request, f'User "{form.instance}" updated.')
        return super().form_valid(form)


class UserPrimaryGroupView(UserPageRequiredMixin, View):
    def _context(self, user, editing=False):
        return {
            'u': user,
            'all_groups': WorkGroup.objects.filter(is_active=True).order_by('sort_order', 'name'),
            'editing': editing,
        }

    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        editing = request.GET.get('edit') == '1'
        return render(request, 'accounts/partials/_primary_group_cell.html', self._context(user, editing))

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        group_id = request.POST.get('group', '').strip()
        if group_id:
            user.group = get_object_or_404(WorkGroup, pk=group_id, is_active=True)
        else:
            user.group = None
        user.save(update_fields=['group'])
        return render(request, 'accounts/partials/_primary_group_cell.html', self._context(user))


class UserManagedGroupsView(AdminRequiredMixin, View):
    def _context(self, user, editing=False):
        from apps.taxonomy.models import WorkGroup
        return {
            'u': user,
            'all_groups': WorkGroup.objects.order_by('name'),
            'managed_group_ids': list(user.managed_groups.values_list('pk', flat=True)),
            'editing': editing,
        }

    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        editing = request.GET.get('edit') == '1'
        return render(request, 'accounts/partials/_managed_groups_cell.html', self._context(user, editing))

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        user.managed_groups.set(request.POST.getlist('managed_groups'))
        return render(request, 'accounts/partials/_managed_groups_cell.html', self._context(user))


class UserManagedProjectsView(AdminRequiredMixin, View):
    def _context(self, user, editing=False):
        from apps.taxonomy.models import Project
        return {
            'u': user,
            'all_projects': Project.objects.order_by('sort_order', 'name'),
            'managed_project_ids': list(user.managed_projects.values_list('pk', flat=True)),
            'editing': editing,
        }

    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        editing = request.GET.get('edit') == '1'
        return render(request, 'accounts/partials/_managed_projects_cell.html', self._context(user, editing))

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        user.managed_projects.set(request.POST.getlist('managed_projects'))
        return render(request, 'accounts/partials/_managed_projects_cell.html', self._context(user))


class SignupToggleView(AdminRequiredMixin, View):
    def post(self, request):
        s = SiteSettings.get_solo()
        s.allow_signup = not s.allow_signup
        s.save(update_fields=['allow_signup'])
        state = 'enabled' if s.allow_signup else 'disabled'
        messages.success(request, f'Self-serve signup {state}.')
        return redirect('admin-users')


class RolePreviewView(View):
    """Activate or exit role preview mode for admins."""

    def post(self, request):
        if not request.user.is_authenticated:
            from django.conf import settings as django_settings
            return redirect(django_settings.LOGIN_URL)

        # Re-query the DB so we check the real role even if middleware already overrode it
        real_user = User.objects.get(pk=request.user.pk)
        if real_user.role != User.Role.ADMIN:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied

        role = request.POST.get('role', '').strip()
        if not role or role == 'exit':
            request.session.pop('_preview_role', None)
        elif role in User.Role.values and role != User.Role.ADMIN:
            request.session['_preview_role'] = role

        return redirect(request.POST.get('next', '/'))


class GroupSelectionView(View):
    """Backward-compatible alias for the institution selection flow."""

    def dispatch(self, request, *args, **kwargs):
        return InstitutionSelectionView.as_view()(request, *args, **kwargs)


class InstitutionSelectionView(View):
    """First-login institution selection for authenticated users."""

    def dispatch(self, request, *args, **kwargs):
        from django.contrib.auth.mixins import LoginRequiredMixin
        if not request.user.is_authenticated:
            from django.conf import settings
            return redirect(settings.LOGIN_URL)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        institutions = Institution.objects.filter(is_active=True)
        return render(request, 'accounts/select_institution.html', {'institutions': institutions})

    def post(self, request):
        institution_id = request.POST.get('institution', '').strip()
        if institution_id:
            try:
                institution = Institution.objects.get(pk=institution_id, is_active=True)
                request.user.institution = institution
                request.user.save(update_fields=['institution'])
                messages.success(request, f'Welcome! Your institution has been set to "{institution.name}".')
            except Institution.DoesNotExist:
                messages.error(request, 'Invalid institution selection.')
                return redirect('select-institution')
        else:
            request.session['_institution_selection_done'] = True
            messages.info(request, 'You can set your institution at any time from your profile.')

        return redirect('dashboard')


class RosterMergeView(View):
    """Connect a first-login account to an imported collaboration roster row."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.conf import settings
            return redirect(settings.LOGIN_URL)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        if request.user.roster_merge_completed or request.user.is_collaboration_member:
            return redirect('dashboard')
        return render(request, 'accounts/merge_roster.html', {
            'suggestions': suggested_roster_records(request.user),
            'roster_records': available_roster_records().order_by('display_name'),
        })

    def post(self, request):
        if request.POST.get('skip'):
            request.user.roster_merge_completed = True
            request.user.save(update_fields=['roster_merge_completed'])
            messages.info(request, 'Roster merge skipped. An administrator can update your record later.')
            return redirect('dashboard')

        record_id = request.POST.get('roster_record') or request.POST.get('suggested_record')
        record = get_object_or_404(available_roster_records(), pk=record_id)
        try:
            merge_roster_record(request.user, record)
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect('merge-roster')
        messages.success(request, f'Your login has been connected to the roster record for {record.display_name}.')
        return redirect('dashboard')


class AdminCreateUserView(AdminRequiredMixin, View):
    def post(self, request):
        form = AdminCreateUserForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            messages.success(request, f'User "{user.email}" created.')
            return redirect('admin-users')
        # Re-render page with form errors
        users = User.objects.order_by('email')
        return render(request, 'accounts/admin_users.html', {
            'users': users,
            'role_choices': User.Role.choices,
            'site_settings': SiteSettings.get_solo(),
            'create_form': form,
            'all_institutions': Institution.objects.filter(is_active=True),
            'show_create_form': True,
        })


class InstitutionListView(TalkManagerRequiredMixin, ListView):
    model = Institution
    template_name = 'accounts/institutions.html'
    context_object_name = 'institutions'

    def get_queryset(self):
        return Institution.objects.all()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form'] = InstitutionForm()
        return ctx

    def post(self, request):
        form = InstitutionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Institution created.')
            return redirect('institutions')
        return render(request, self.template_name, {
            'institutions': Institution.objects.all(),
            'form': form,
        })


class InstitutionUpdateView(TalkManagerRequiredMixin, View):
    def post(self, request, pk):
        institution = get_object_or_404(Institution, pk=pk)
        form = InstitutionForm(request.POST, instance=institution)
        if form.is_valid():
            form.save()
            messages.success(request, 'Institution updated.')
        else:
            messages.error(request, 'Could not update institution.')
        return redirect('institutions')


class InstitutionEditView(TalkManagerRequiredMixin, UpdateView):
    model = Institution
    form_class = InstitutionForm
    template_name = 'accounts/edit_institution.html'
    success_url = reverse_lazy('institutions')

    def form_valid(self, form):
        messages.success(self.request, 'Institution updated.')
        return super().form_valid(form)


class RosterImportView(AdminRequiredMixin, View):
    template_name = 'accounts/import_roster.html'

    def get(self, request):
        return render(request, self.template_name, {'form': RosterImportForm()})

    def post(self, request):
        form = RosterImportForm(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form})
        try:
            if form.cleaned_data['import_type'] == RosterImportForm.ImportType.INSTITUTIONS:
                counts = import_institutions(form.cleaned_data['csv_file'])
                messages.success(
                    request,
                    f'Institution import complete: {counts["created"]} created, '
                    f'{counts["updated"]} updated.',
                )
            else:
                counts = import_members(form.cleaned_data['csv_file'])
                messages.success(
                    request,
                    f'Member import complete: {counts["created"]} users created, '
                    f'{counts["updated"]} updated, '
                    f'{counts["institutions_created"]} institutions created.',
                )
        except RosterImportError as exc:
            form.add_error('csv_file', str(exc))
            return render(request, self.template_name, {'form': form})
        return redirect('roster-import')
