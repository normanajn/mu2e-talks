import json
from datetime import date

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from apps.accounts.models import Institution, User
from apps.talks.models import Conference, Talk

from .auth import api_token_required
from .models import ApiToken


def _json_body(request):
    try:
        data = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError as exc:
        raise ValueError(f'Invalid JSON: {exc.msg}') from exc
    if not isinstance(data, dict):
        raise ValueError('JSON body must be an object.')
    return data


def _date(value):
    if value in (None, ''):
        return None
    return date.fromisoformat(str(value))


def _bool(value, default=False):
    if value in (None, ''):
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {'1', 'true', 'yes', 'y', 'on'}


def _bad_request(message, errors=None):
    payload = {'error': message}
    if errors:
        payload['fields'] = errors
    return JsonResponse(payload, status=400)


class ApiDocsView(LoginRequiredMixin, View):
    template_name = 'api/index.html'

    def get(self, request):
        tokens = ApiToken.objects.filter(user=request.user)
        return render(request, self.template_name, {'tokens': tokens})

    def post(self, request):
        if not request.user.can_manage_talks:
            messages.error(request, 'Your role cannot create API tokens.')
            return redirect('api:index')
        name = request.POST.get('name', '').strip() or 'API token'
        token, key = ApiToken.create_token(request.user, name)
        messages.success(request, f'API token "{token.name}" created. Copy it now; it will not be shown again.')
        tokens = ApiToken.objects.filter(user=request.user)
        return render(request, self.template_name, {'tokens': tokens, 'new_token': key})


class ApiTokenRevokeView(LoginRequiredMixin, View):
    def post(self, request, pk):
        token = get_object_or_404(ApiToken, pk=pk, user=request.user)
        token.is_active = False
        token.save(update_fields=['is_active', 'updated_at'])
        messages.success(request, f'API token "{token.name}" revoked.')
        return redirect('api:index')


@method_decorator(csrf_exempt, name='dispatch')
class InstitutionCreateApiView(View):
    @method_decorator(api_token_required)
    def post(self, request):
        try:
            data = _json_body(request)
            institution = Institution(
                name=str(data.get('name', '')).strip(),
                url=str(data.get('url', '')).strip(),
                collaboration_number=str(data.get('collaboration_number', '')).strip(),
                collaboration_code=str(data.get('collaboration_code', '')).strip(),
                sort_order=int(data.get('sort_order') or 0),
                is_active=_bool(data.get('is_active'), True),
            )
        except (ValueError, ObjectDoesNotExist) as exc:
            return _bad_request(str(exc))
        try:
            institution.full_clean()
            institution.save()
        except (ValidationError, ValueError) as exc:
            return _bad_request('Institution could not be created.', getattr(exc, 'message_dict', None))
        return JsonResponse({'id': institution.pk, 'name': institution.name, 'url': institution.url}, status=201)


@method_decorator(csrf_exempt, name='dispatch')
class ConferenceCreateApiView(View):
    @method_decorator(api_token_required)
    def post(self, request):
        try:
            data = _json_body(request)
            conference = Conference(
                inspire_id=str(data.get('inspire_id') or '').strip() or None,
                title=str(data.get('title', '')).strip(),
                start_date=_date(data.get('start_date')),
                end_date=_date(data.get('end_date')),
                url=str(data.get('url', '')).strip(),
            )
            conference.full_clean()
            conference.save()
        except (ValueError, ObjectDoesNotExist) as exc:
            return _bad_request(str(exc))
        except ValidationError as exc:
            return _bad_request('Conference could not be created.', exc.message_dict)
        return JsonResponse({'id': conference.pk, 'title': conference.title}, status=201)


@method_decorator(csrf_exempt, name='dispatch')
class TalkCreateApiView(View):
    @method_decorator(api_token_required)
    def post(self, request):
        try:
            data = _json_body(request)
            conference = self._conference(data)
            assigned_to = self._user(data.get('assigned_to_id'), data.get('assigned_to_email'))
            speaker_institution = self._institution(data.get('speaker_institution_id'), data.get('speaker_institution_name'))
            talk = Talk(
                created_by=request.api_user,
                conference=conference,
                assigned_to=assigned_to,
                speaker_institution=speaker_institution,
                talk_title=str(data.get('talk_title', '')).strip(),
                presentation_date=_date(data.get('presentation_date')),
                type=data.get('type') or Talk.Type.OTHER,
                spreadsheet_type_raw=str(data.get('spreadsheet_type_raw', '')).strip(),
                docdb_number=str(data.get('docdb_number', '')).strip(),
                docdb_password_number=str(data.get('docdb_password_number', '')).strip(),
                docdb_certificate_number=str(data.get('docdb_certificate_number', '')).strip(),
                plenary=_bool(data.get('plenary')),
                parallel=_bool(data.get('parallel')),
                speaker_first_name=str(data.get('speaker_first_name', '')).strip(),
                speaker_last_name=str(data.get('speaker_last_name', '')).strip(),
                speaker_home_institution_raw=str(data.get('speaker_home_institution_raw', '')).strip(),
                duration_minutes=data.get('duration_minutes') or None,
                duration_raw=str(data.get('duration_raw', '')).strip(),
                practice_talk_date=_date(data.get('practice_talk_date')),
                practice_talk_complete=_bool(data.get('practice_talk_complete')),
                final_approval=_bool(data.get('final_approval')),
                committee_approved_raw=str(data.get('committee_approved_raw', '')).strip(),
                complete_given=_bool(data.get('complete_given')),
                mu2e_program=str(data.get('mu2e_program', '')).strip(),
                proceedings_url=str(data.get('proceedings_url', '')).strip(),
                arxiv_url=str(data.get('arxiv_url', '')).strip(),
                comments=str(data.get('comments', '')).strip(),
                status=data.get('status') or Talk.Status.ACTIVE,
            )
            talk.full_clean()
            talk.save()
        except (ValueError, ObjectDoesNotExist) as exc:
            return _bad_request(str(exc))
        except ValidationError as exc:
            return _bad_request('Talk could not be created.', exc.message_dict)
        return JsonResponse({'id': talk.pk, 'talk_title': talk.talk_title, 'status': talk.status}, status=201)

    @staticmethod
    def _conference(data):
        conference_id = data.get('conference_id')
        if conference_id:
            return Conference.objects.get(pk=conference_id)
        title = str(data.get('conference_title', '')).strip()
        if not title:
            return None
        conference, _ = Conference.objects.get_or_create(
            title=title,
            defaults={
                'start_date': _date(data.get('conference_start_date')),
                'end_date': _date(data.get('conference_end_date')),
                'url': str(data.get('conference_url', '')).strip(),
            },
        )
        return conference

    @staticmethod
    def _user(user_id, email):
        if user_id:
            return User.objects.get(pk=user_id)
        if email:
            return User.objects.filter(email__iexact=email).first() or User.objects.filter(contact_email__iexact=email).first()
        return None

    @staticmethod
    def _institution(institution_id, name):
        if institution_id:
            return Institution.objects.get(pk=institution_id)
        if name:
            return Institution.objects.filter(name__iexact=name).first()
        return None
