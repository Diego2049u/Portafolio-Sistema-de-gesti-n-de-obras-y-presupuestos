from django.conf import settings
from rest_framework.authentication import CSRFCheck
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework_simplejwt.authentication import JWTAuthentication


def enforce_csrf(request):
    django_request = request._request
    check = CSRFCheck(lambda req: None)
    check.process_request(django_request)
    reason = check.process_view(django_request, None, (), {})
    if reason:
        raise PermissionDenied(f'CSRF validation failed: {reason}')


class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        cookie_name = getattr(settings, 'JWT_ACCESS_COOKIE_NAME', 'fyag_access')
        raw_token = request.COOKIES.get(cookie_name)
        if not raw_token:
            return None
        if request.method not in ('GET', 'HEAD', 'OPTIONS', 'TRACE'):
            enforce_csrf(request)
        validated_token = self.get_validated_token(raw_token.encode('utf-8'))
        user = self.get_user(validated_token)
        if not user.is_active or user.estado != 'activo' or user.deleted_at is not None:
            raise AuthenticationFailed('La cuenta no está activa.')
        return user, validated_token
