from django.core.paginator import EmptyPage, Paginator
from django.http import HttpResponseBadRequest
from django.shortcuts import render
from django.views import View

from apps.accounts.permissions import TalkReporterRequiredMixin
from apps.talks.models import Talk

from . import exporters
from .filters import TalkFilter

PREVIEW_LIMIT = 50


def _filtered_qs(data):
    qs = Talk.objects.select_related('conference', 'assigned_to', 'created_by')
    f = TalkFilter(data, queryset=qs)
    return f, f.qs.order_by('status', '-conference__start_date', 'talk_title')


class ReportIndexView(TalkReporterRequiredMixin, View):
    def get(self, request):
        return render(request, 'reports/index.html', {
            'filter': TalkFilter(queryset=Talk.objects.none()),
            'formats': exporters.available(),
        })


class ReportPreviewView(TalkReporterRequiredMixin, View):
    def post(self, request):
        f, qs = _filtered_qs(request.POST)
        paginator = Paginator(qs, PREVIEW_LIMIT)
        try:
            page_number = int(request.POST.get('page', 1))
        except (TypeError, ValueError):
            page_number = 1
        try:
            page_obj = paginator.page(page_number)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)
        return render(request, 'reports/partials/_preview.html', {
            'filter': f,
            'rows': page_obj.object_list,
            'page_obj': page_obj,
            'paginator': paginator,
            'total': paginator.count,
            'limit': PREVIEW_LIMIT,
        })


class ReportDownloadView(TalkReporterRequiredMixin, View):
    def post(self, request, fmt: str):
        exporter = exporters.get(fmt)
        if not exporter:
            return HttpResponseBadRequest(f'Unknown format: {fmt}')
        _, qs = _filtered_qs(request.POST)
        selected_ids = request.POST.getlist('selected_ids')
        if selected_ids:
            qs = qs.filter(pk__in=selected_ids)
        from apps.audit.service import log_event
        log_event(
            action='export',
            request=request,
            changes={'format': fmt, 'count': qs.count(), 'selection': bool(selected_ids)},
        )
        return exporter(qs)
