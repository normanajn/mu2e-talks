from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import ProtectedError, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from apps.accounts.permissions import TalkDeleteRequiredMixin, TalkManagerRequiredMixin
from apps.core.markdown import render_markdown

from .forms import ConferenceForm, TalkForm, TalkSpreadsheetImportForm
from .models import Conference, Talk
from .spreadsheet_import import TalkSpreadsheetImportError, import_talk_records, records_from_json, workbook_to_records


def _can_edit(user, talk):
    return user.can_manage_talks or talk.assigned_to_id == user.id


_SORT_FIELDS = {
    'talk':       'talk_title',
    'date':       'conference__start_date',
    'conference': 'conference__title',
    'type':       'type',
    'assigned':   'assigned_to__display_name',
    'practice':   'practice_talk_date',
    'status':     'status',
}


class TalkListView(LoginRequiredMixin, ListView):
    model = Talk
    template_name = 'talks/list.html'
    context_object_name = 'talks'
    paginate_by = 50
    page_size_options = ('50', '100', '200', 'all')

    def _sort_params(self):
        sort_key = self.request.GET.get('sort', 'date').strip()
        sort_dir = self.request.GET.get('dir', 'desc').strip()
        if sort_key not in _SORT_FIELDS:
            sort_key = 'date'
        if sort_dir not in ('asc', 'desc'):
            sort_dir = 'desc'
        return sort_key, sort_dir

    def get_paginate_by(self, queryset):
        per_page = self.request.GET.get('per_page', '50').strip().lower()
        if per_page == 'all':
            return None
        if per_page in self.page_size_options:
            return int(per_page)
        return self.paginate_by

    def get_queryset(self):
        qs = Talk.objects.select_related('conference', 'assigned_to', 'created_by')
        user = self.request.user
        if not user.can_manage_talks:
            qs = qs.filter(Q(assigned_to=user) | Q(created_by=user, status=Talk.Status.DRAFT))
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(Q(talk_title__icontains=q) | Q(conference__title__icontains=q))
        status = self.request.GET.get('status', '').strip()
        if status in Talk.Status.values:
            qs = qs.filter(status=status)
        sort_key, sort_dir = self._sort_params()
        field = _SORT_FIELDS[sort_key]
        order = f'-{field}' if sort_dir == 'desc' else field
        return qs.order_by(order, 'talk_title', 'pk')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        per_page = self.request.GET.get('per_page', '50').strip().lower()
        if per_page not in self.page_size_options:
            per_page = '50'
        sort_key, sort_dir = self._sort_params()
        # filter_query: all params except sort/dir/page — used to build column sort links
        filter_params = self.request.GET.copy()
        for k in ('sort', 'dir', 'page'):
            filter_params.pop(k, None)
        filter_query = filter_params.urlencode()
        # pagination_query: all params except page — preserves active sort
        pagination_params = self.request.GET.copy()
        pagination_params.pop('page', None)
        ctx['per_page'] = per_page
        ctx['page_size_options'] = self.page_size_options
        ctx['pagination_query'] = pagination_params.urlencode()
        from datetime import timedelta
        from django.utils import timezone
        today = timezone.localdate()
        ctx['sort'] = sort_key
        ctx['sort_dir'] = sort_dir
        ctx['filter_query'] = filter_query
        ctx['today'] = today
        ctx['sixty_days_from_now'] = today + timedelta(days=60)
        return ctx


class TalkCreateView(LoginRequiredMixin, CreateView):
    model = Talk
    form_class = TalkForm
    template_name = 'talks/form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['allow_status'] = self.request.user.can_manage_talks
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        if self.request.user.can_manage_talks:
            initial['status'] = Talk.Status.ACTIVE
        else:
            initial['status'] = Talk.Status.DRAFT
            initial['assigned_to'] = self.request.user.pk
        return initial

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        if not self.request.user.can_manage_talks:
            form.instance.status = Talk.Status.DRAFT
            form.instance.assigned_to = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f'Talk "{self.object.talk_title}" created.')
        return response

    def get_success_url(self):
        return reverse('talks:detail', kwargs={'pk': self.object.pk})


class TalkDetailView(LoginRequiredMixin, DetailView):
    model = Talk
    template_name = 'talks/detail.html'

    def get_queryset(self):
        return Talk.objects.select_related('conference', 'assigned_to', 'created_by')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['comments_html'] = render_markdown(self.object.comments)
        ctx['can_edit'] = _can_edit(self.request.user, self.object)
        ctx['can_delete'] = self.request.user.can_delete_talks
        ctx['can_activate'] = self.request.user.can_manage_talks and self.object.status == Talk.Status.DRAFT
        return ctx


class TalkUpdateView(LoginRequiredMixin, UpdateView):
    model = Talk
    form_class = TalkForm
    template_name = 'talks/form.html'

    def get_queryset(self):
        return Talk.objects.select_related('conference', 'assigned_to')

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not _can_edit(request.user, self.object):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['allow_status'] = self.request.user.can_manage_talks
        return kwargs

    def form_valid(self, form):
        if not self.request.user.can_manage_talks:
            form.instance.assigned_to = self.request.user
            if form.instance.status != Talk.Status.DRAFT:
                form.instance.status = self.object.status
        response = super().form_valid(form)
        messages.success(self.request, 'Talk updated.')
        return response

    def get_success_url(self):
        return reverse('talks:detail', kwargs={'pk': self.object.pk})


class TalkDeleteView(TalkDeleteRequiredMixin, DeleteView):
    model = Talk
    template_name = 'talks/confirm_delete.html'
    success_url = reverse_lazy('talks:list')

    def form_valid(self, form):
        title = self.object.talk_title
        response = super().form_valid(form)
        messages.success(self.request, f'Talk "{title}" deleted.')
        return response


class TalkActivateView(TalkManagerRequiredMixin, View):
    def post(self, request, pk):
        talk = get_object_or_404(Talk.objects.select_related('conference'), pk=pk)
        talk.status = Talk.Status.ACTIVE
        try:
            talk.full_clean()
        except Exception as exc:
            messages.error(request, f'Could not activate talk: {exc}')
            return redirect('talks:detail', pk=talk.pk)
        talk.save(update_fields=['status', 'updated_at'])
        messages.success(request, f'Talk "{talk.talk_title}" activated.')
        return redirect('talks:detail', pk=talk.pk)


class MarkdownPreviewView(LoginRequiredMixin, View):
    def post(self, request):
        text = request.POST.get('comments', '')
        return render(request, 'talks/partials/_markdown_preview.html', {
            'html': render_markdown(text),
        })


class ConferenceListView(TalkManagerRequiredMixin, ListView):
    model = Conference
    template_name = 'talks/conferences.html'
    context_object_name = 'conferences'
    paginate_by = 50

    def get_queryset(self):
        qs = Conference.objects.all()
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(url__icontains=q) | Q(inspire_id__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        query_params = self.request.GET.copy()
        query_params.pop('page', None)
        ctx['query'] = self.request.GET.get('q', '').strip()
        ctx['pagination_query'] = query_params.urlencode()
        return ctx


class TalkSpreadsheetImportView(TalkManagerRequiredMixin, View):
    template_name = 'talks/import_spreadsheet.html'

    def get(self, request):
        return render(request, self.template_name, {'form': TalkSpreadsheetImportForm()})

    def post(self, request):
        form = TalkSpreadsheetImportForm(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form})
        upload = form.cleaned_data['spreadsheet_file']
        try:
            if upload.name.lower().endswith('.json'):
                counts = import_talk_records(records_from_json(upload), created_by=request.user)
            else:
                counts = import_talk_records(workbook_to_records(upload), created_by=request.user)
        except TalkSpreadsheetImportError as exc:
            form.add_error('spreadsheet_file', str(exc))
            return render(request, self.template_name, {'form': form})

        messages.success(
            request,
            f'Talk import complete: {counts["created"]} created, {counts["updated"]} updated, '
            f'{counts["matched_users"]} speakers matched, {counts["unmatched_users"]} speakers unmatched, '
            f'{counts["matched_institutions"]} institutions matched, '
            f'{counts["unmatched_institutions"]} institutions unmatched.',
        )
        return redirect('talks:spreadsheet-import')


class ConferenceCreateView(TalkManagerRequiredMixin, CreateView):
    model = Conference
    form_class = ConferenceForm
    template_name = 'talks/conference_form.html'
    success_url = reverse_lazy('talks:conferences')

    def form_valid(self, form):
        messages.success(self.request, f'Conference "{form.instance.title}" created.')
        return super().form_valid(form)


class ConferenceUpdateView(TalkManagerRequiredMixin, UpdateView):
    model = Conference
    form_class = ConferenceForm
    template_name = 'talks/conference_form.html'
    success_url = reverse_lazy('talks:conferences')

    def form_valid(self, form):
        messages.success(self.request, f'Conference "{form.instance.title}" updated.')
        return super().form_valid(form)


class ConferenceDeleteView(TalkManagerRequiredMixin, DeleteView):
    model = Conference
    template_name = 'talks/conference_confirm_delete.html'
    success_url = reverse_lazy('talks:conferences')

    def form_valid(self, form):
        title = self.object.title
        try:
            response = super().form_valid(form)
        except ProtectedError:
            messages.error(
                self.request,
                f'Conference "{title}" cannot be deleted because it is assigned to one or more talks.',
            )
            return redirect('talks:conferences')
        messages.success(self.request, f'Conference "{title}" deleted.')
        return response
