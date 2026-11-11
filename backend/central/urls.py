from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from api.views import (
    UsuarioViewSet, ClienteViewSet, PresupuestoViewSet,
    ObraViewSet, CostoMaterialViewSet, FacturaViewSet, PagoViewSet
)

router = DefaultRouter()
router.register(r'usuarios', UsuarioViewSet)
router.register(r'clientes', ClienteViewSet)
router.register(r'presupuestos', PresupuestoViewSet)
router.register(r'obras', ObraViewSet)
router.register(r'costos', CostoMaterialViewSet)
router.register(r'facturas', FacturaViewSet)
router.register(r'pagos', PagoViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    
    # Endpoints JWT para Iniciar Sesión en Auth.jsx
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]