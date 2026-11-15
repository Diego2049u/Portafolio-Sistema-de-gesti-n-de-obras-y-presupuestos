from django.conf import settings
from django.core.cache import cache
from django.middleware.csrf import get_token
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
import hashlib

from .models import Usuario


def revocar_refresh_usuario(usuario):
    for token in OutstandingToken.objects.filter(user=usuario, expires_at__gt=timezone.now()):
        BlacklistedToken.objects.get_or_create(token=token)


def _cookie_options(max_age):
    return {
        'max_age': max_age,
        'httponly': True,
        'secure': getattr(settings, 'JWT_COOKIE_SECURE', not settings.DEBUG),
        'samesite': getattr(settings, 'JWT_COOKIE_SAMESITE', 'Lax'),
        'path': '/',
    }


def _set_auth_cookies(response, access, refresh=None):
    access_name = getattr(settings, 'JWT_ACCESS_COOKIE_NAME', 'fyag_access')
    refresh_name = getattr(settings, 'JWT_REFRESH_COOKIE_NAME', 'fyag_refresh')
    access_lifetime = int(jwt_settings.ACCESS_TOKEN_LIFETIME.total_seconds())
    response.set_cookie(access_name, str(access), **_cookie_options(access_lifetime))
    if refresh is not None:
        refresh_lifetime = int(jwt_settings.REFRESH_TOKEN_LIFETIME.total_seconds())
        response.set_cookie(refresh_name, str(refresh), **_cookie_options(refresh_lifetime))


def _clear_auth_cookies(response):
    for name in (
        getattr(settings, 'JWT_ACCESS_COOKIE_NAME', 'fyag_access'),
        getattr(settings, 'JWT_REFRESH_COOKIE_NAME', 'fyag_refresh'),
    ):
        response.delete_cookie(name, path='/', samesite=getattr(settings, 'JWT_COOKIE_SAMESITE', 'Lax'))


class CsrfTokenView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        return Response({'csrfToken': get_token(request)})


@method_decorator(csrf_protect, name='dispatch')
class CookieLoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'

    def post(self, request):
        email = str(request.data.get('email', '')).strip().lower()
        password = request.data.get('password', '')
        ip_address = request.META.get('REMOTE_ADDR', 'unknown')
        digest = hashlib.sha256(f'{ip_address}:{email}'.encode()).hexdigest()
        attempt_key = f'login-fail:{digest}'
        threshold = getattr(settings, 'LOGIN_FAILURE_LIMIT', 5)
        if int(cache.get(attempt_key, 0)) >= threshold:
            from .services import registrar_evento
            registrar_evento(usuario=None, modulo='Acceso al sistema', accion='inicio_sesion_bloqueado', resultado='error', detalle='Intento rechazado por bloqueo temporal de autenticación.')
            raise AuthenticationFailed('Credenciales incorrectas o acceso temporalmente bloqueado.')
        user = Usuario.all_objects.filter(email__iexact=email).first()
        if not user or not user.check_password(password) or not user.is_active or user.estado != 'activo' or user.deleted_at:
            attempts = int(cache.get(attempt_key, 0)) + 1
            cache.set(attempt_key, attempts, timeout=getattr(settings, 'LOGIN_FAILURE_WINDOW', 900))
            from .services import registrar_evento
            registrar_evento(usuario=user, modulo='Acceso al sistema', accion='inicio_sesion_fallido', resultado='error', detalle='Intento de inicio de sesión rechazado.')
            raise AuthenticationFailed('Correo o contraseña incorrectos, o la cuenta no está activa.')
        cache.delete(attempt_key)
        refresh = RefreshToken.for_user(user)
        response = Response({
            'user': {
                'id': user.pk,
                'name': user.get_full_name(),
                'email': user.email,
                'role': user.rol,
            },
        }, status=status.HTTP_200_OK)
        _set_auth_cookies(response, refresh.access_token, refresh)
        from .services import registrar_evento
        registrar_evento(usuario=user, modulo='Acceso al sistema', accion='inicio_sesion', resultado='exito', detalle='Inicio de sesión correcto.')
        return response


@method_decorator(csrf_protect, name='dispatch')
class CookieRefreshView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_name = getattr(settings, 'JWT_REFRESH_COOKIE_NAME', 'fyag_refresh')
        refresh_token = request.COOKIES.get(refresh_name)
        if not refresh_token:
            raise AuthenticationFailed('No hay una sesión renovable.')
        try:
            refresh = RefreshToken(refresh_token)
            user_id = refresh.get(jwt_settings.USER_ID_CLAIM)
        except TokenError as exc:
            raise AuthenticationFailed('La sesión renovable no es válida.') from exc
        user = Usuario.all_objects.filter(pk=user_id).first()
        if not user or not user.is_active or user.estado != 'activo' or user.deleted_at is not None:
            try:
                refresh.blacklist()
            except TokenError:
                pass
            response = Response({'detail': 'La cuenta no está activa. Inicie sesión nuevamente.'}, status=status.HTTP_401_UNAUTHORIZED)
            _clear_auth_cookies(response)
            from .services import registrar_evento
            registrar_evento(usuario=user, modulo='Acceso al sistema', accion='refresh_rechazado', resultado='error', detalle='Refresh rechazado porque la cuenta fue desactivada o eliminada.')
            return response
        serializer = TokenRefreshSerializer(data={'refresh': refresh_token})
        serializer.is_valid(raise_exception=True)
        response = Response({'detail': 'Sesión renovada.'}, status=status.HTTP_200_OK)
        _set_auth_cookies(response, serializer.validated_data['access'], serializer.validated_data.get('refresh'))
        return response


@method_decorator(csrf_protect, name='dispatch')
class CookieLogoutView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_name = getattr(settings, 'JWT_REFRESH_COOKIE_NAME', 'fyag_refresh')
        refresh_token = request.COOKIES.get(refresh_name)
        if refresh_token:
            try:
                RefreshToken(refresh_token).blacklist()
            except Exception:
                pass
        response = Response({'detail': 'Sesión cerrada.'}, status=status.HTTP_200_OK)
        _clear_auth_cookies(response)
        return response


class CurrentUserView(APIView):
    def get(self, request):
        user = request.user
        return Response({'id': user.pk, 'name': user.get_full_name(), 'email': user.email, 'role': user.rol})
