from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from api.auth_views import CookieLoginView, CookieLogoutView, CookieRefreshView, CsrfTokenView, CurrentUserView
from api.views import (
    AuditoriaLogViewSet, CategoriaServicioViewSet, ClienteViewSet, ContratoViewSet,
    CostoMaterialViewSet, DashboardResumenView, FacturaViewSet, ObraViewSet, PagoViewSet,
    PresupuestoViewSet, UsuarioViewSet,
)

router = DefaultRouter()
router.register(r'usuarios', UsuarioViewSet)
router.register(r'clientes', ClienteViewSet)
router.register(r'contratos', ContratoViewSet)
router.register(r'categorias-servicio', CategoriaServicioViewSet)
router.register(r'presupuestos', PresupuestoViewSet)
router.register(r'obras', ObraViewSet)
router.register(r'costos', CostoMaterialViewSet)
router.register(r'facturas', FacturaViewSet)
router.register(r'pagos', PagoViewSet)
router.register(r'auditoria', AuditoriaLogViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/auth/csrf/', CsrfTokenView.as_view(), name='csrf-token'),
    path('api/auth/login/', CookieLoginView.as_view(), name='cookie-login'),
    path('api/auth/refresh/', CookieRefreshView.as_view(), name='cookie-refresh'),
    path('api/auth/logout/', CookieLogoutView.as_view(), name='cookie-logout'),
    path('api/auth/me/', CurrentUserView.as_view(), name='current-user'),
    path('api/dashboard/resumen/', DashboardResumenView.as_view(), name='dashboard-resumen'),
]
