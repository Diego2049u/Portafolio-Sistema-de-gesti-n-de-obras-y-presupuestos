from rest_framework.permissions import BasePermission


GERENCIA = 'GERENCIA'
FINANZAS = 'FINANZAS'
SUPERVISOR = 'SUPERVISOR'
TECNICO = 'TECNICO'


class RolePermission(BasePermission):
    """Acceso por rol a una acción; el filtrado de registros va en el queryset."""
    role_actions = {}

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated or not user.is_active:
            return False
        if user.is_superuser:
            return True
        if getattr(user, 'estado', None) != 'activo' or getattr(user, 'deleted_at', None):
            return False
        allowed = self.role_actions.get(view.action, set())
        return user.rol == GERENCIA or user.rol in allowed


class UserPermission(RolePermission):
    role_actions = {
        'list': {GERENCIA}, 'retrieve': {GERENCIA}, 'create': {GERENCIA},
        'update': {GERENCIA}, 'partial_update': {GERENCIA}, 'destroy': {GERENCIA},
        'activar': {GERENCIA},
    }


class ClientePermission(RolePermission):
    role_actions = {
        'list': {FINANZAS, SUPERVISOR}, 'retrieve': {FINANZAS, SUPERVISOR},
        'create': {FINANZAS}, 'update': {FINANZAS}, 'partial_update': {FINANZAS}, 'destroy': {FINANZAS},
    }


class ContratoPermission(RolePermission):
    role_actions = {
        'list': {FINANZAS}, 'retrieve': {FINANZAS}, 'create': {FINANZAS},
        'update': {FINANZAS}, 'partial_update': {FINANZAS}, 'destroy': {FINANZAS},
    }


class PresupuestoPermission(RolePermission):
    role_actions = {
        'list': {FINANZAS}, 'retrieve': {FINANZAS}, 'create': {FINANZAS},
        'update': {FINANZAS}, 'partial_update': {FINANZAS}, 'destroy': {FINANZAS},
        'exportar_pdf': {FINANZAS}, 'enviar': {FINANZAS},
        'decision_cliente': {FINANZAS}, 'aprobar_gerencia': {GERENCIA},
        'exigir_aprobacion': {GERENCIA}, 'historial_versiones': {FINANZAS},
    }


class ObraPermission(RolePermission):
    role_actions = {
        'list': {FINANZAS, SUPERVISOR, TECNICO}, 'retrieve': {FINANZAS, SUPERVISOR, TECNICO},
        'create': {SUPERVISOR}, 'update': {SUPERVISOR}, 'partial_update': {SUPERVISOR}, 'destroy': {SUPERVISOR},
        'transicionar': {SUPERVISOR}, 'cerrar_comercial': {FINANZAS}, 'reabrir': {GERENCIA},
        'presupuestos_disponibles': {SUPERVISOR}, 'tecnicos_disponibles': {SUPERVISOR},
        'historial_estados': {FINANZAS, SUPERVISOR, TECNICO},
    }


class CostoPermission(RolePermission):
    role_actions = {
        'list': {FINANZAS, SUPERVISOR}, 'retrieve': {FINANZAS, SUPERVISOR},
        'create': {FINANZAS, SUPERVISOR}, 'update': {FINANZAS, SUPERVISOR},
        'partial_update': {FINANZAS, SUPERVISOR}, 'destroy': {FINANZAS, SUPERVISOR},
    }


class FacturaPermission(RolePermission):
    role_actions = {
        'list': {FINANZAS}, 'retrieve': {FINANZAS}, 'create': {FINANZAS},
        'update': {FINANZAS}, 'partial_update': {FINANZAS}, 'destroy': {FINANZAS},
        'notas_credito': {FINANZAS},
    }


class PagoPermission(RolePermission):
    role_actions = {
        'list': {FINANZAS}, 'retrieve': {FINANZAS}, 'create': {FINANZAS},
        'update': {FINANZAS}, 'partial_update': {FINANZAS}, 'destroy': {FINANZAS},
        'reversas': {FINANZAS},
    }


class CategoriaServicioPermission(RolePermission):
    role_actions = {
        'list': {FINANZAS, SUPERVISOR, TECNICO}, 'retrieve': {FINANZAS, SUPERVISOR, TECNICO},
        'create': {GERENCIA}, 'update': {GERENCIA}, 'partial_update': {GERENCIA}, 'destroy': {GERENCIA},
    }


class AuditoriaPermission(RolePermission):
    role_actions = {'list': {GERENCIA}, 'retrieve': {GERENCIA}}


class DashboardPermission(BasePermission):
    allowed_roles = {GERENCIA, FINANZAS}

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and (user.is_superuser or user.rol in self.allowed_roles)
            and getattr(user, 'estado', None) == 'activo'
            and not getattr(user, 'deleted_at', None)
        )
