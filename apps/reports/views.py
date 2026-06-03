from django.contrib import messages
from django.core.paginator import EmptyPage, Paginator
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views import View

from apps.accounts.permissions import TalkReporterRequiredMixin
from apps.core.markdown import render_markdown
from apps.talks.models import Talk

from . import ai_summary, exporters
from .filters import TalkFilter
from .forms import AIPromptConfigForm
from .models import AIPromptConfig

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
            'prompt_form': AIPromptConfigForm(instance=AIPromptConfig.get_solo()),
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


class ReportSummaryView(TalkReporterRequiredMixin, View):
    def post(self, request):
        _, qs = _filtered_qs(request.POST)
        selected_ids = request.POST.getlist('selected_ids')
        if selected_ids:
            qs = qs.filter(pk__in=selected_ids)
        count = qs.count()
        if count == 0:
            return render(request, 'reports/partials/_summary.html', {
                'error': 'No talks matched. Adjust filters or select rows in the preview first.',
            })
        query = request.POST.get('ai_query', '').strip()
        try:
            text = ai_summary.generate(qs, query=query, user=request.user)
        except Exception as exc:
            return render(request, 'reports/partials/_summary.html', {'error': str(exc)})
        from apps.audit.service import log_event
        log_event(
            action='export',
            request=request,
            changes={'format': 'ai_summary', 'count': count, 'selection': bool(selected_ids)},
        )
        html = render_markdown(text)
        return render(request, 'reports/partials/_summary.html', {
            'summary_text': text,
            'summary_html': html,
            'count': count,
            'query': query,
        })


class SummaryDownloadMdView(TalkReporterRequiredMixin, View):
    def post(self, request):
        text = request.POST.get('summary_text', '')
        ts = timezone.now().strftime('%Y%m%d_%H%M')
        resp = HttpResponse(text, content_type='text/markdown; charset=utf-8')
        resp['Content-Disposition'] = f'attachment; filename="mu2e_summary_{ts}.md"'
        return resp


class SummaryDownloadPdfView(TalkReporterRequiredMixin, View):
    def post(self, request):
        from ._pdf import md_to_pdf
        text = request.POST.get('summary_text', '')
        ts_label = timezone.now().strftime('%Y-%m-%d %H:%M')
        pdf_bytes = md_to_pdf(
            markdown_text=text,
            title='Mu2eTalks — AI Summary',
            meta=f'Generated {ts_label} UTC',
        )
        ts = timezone.now().strftime('%Y%m%d_%H%M')
        resp = HttpResponse(pdf_bytes, content_type='application/pdf')
        resp['Content-Disposition'] = f'attachment; filename="mu2e_summary_{ts}.pdf"'
        return resp


class AIPromptConfigView(TalkReporterRequiredMixin, View):
    def post(self, request):
        if not request.user.is_mu2e_admin:
            return HttpResponseForbidden()
        form = AIPromptConfigForm(request.POST, instance=AIPromptConfig.get_solo())
        if form.is_valid():
            form.save()
            messages.success(request, 'AI prompt configuration saved.')
        else:
            messages.error(request, 'Could not save — check the form for errors.')
        return redirect('reports:index')
