from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from apps.accounts.permissions import TalkDeleteRequiredMixin, TalkManagerRequiredMixin
from apps.core.markdown import render_markdown

from .forms import TalkForm
from .models import Conference, Talk


def _can_edit(user, talk):
    return user.can_manage_talks or talk.assigned_to_id == user.id


class TalkListView(LoginRequiredMixin, ListView):
    model = Talk
    template_name = 'talks/list.html'
    context_object_name = 'talks'
    paginate_by = 25

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
        return qs


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
