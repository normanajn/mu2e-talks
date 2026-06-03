from functools import wraps

from django.http import JsonResponse

from .models import ApiToken


def _token_from_request(request):
    auth = request.headers.get('Authorization', '').strip()
    if auth.lower().startswith('bearer '):
        return auth[7:].strip()
    return request.headers.get('X-API-Token', '').strip()


def authenticate_api_request(request):
    key = _token_from_request(request)
    if not key:
        return None
    token = (
        ApiToken.objects.select_related('user')
        .filter(prefix=key[:16], key_hash=ApiToken.hash_key(key), is_active=True)
        .first()
    )
    if not token or not token.user.is_active:
        return None
    token.mark_used()
    return token.user


def api_token_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user = authenticate_api_request(request)
        if not user:
            return JsonResponse({'error': 'Authentication credentials were not provided or are invalid.'}, status=401)
        if not user.can_manage_talks:
            return JsonResponse({'error': 'This API token is not authorized to create these records.'}, status=403)
        request.api_user = user
        return view_func(request, *args, **kwargs)
    return wrapper
