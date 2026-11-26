from rest_framework.permissions import BasePermission, SAFE_METHODS


ADMIN_GENERAL = 'ADMIN_GENERAL'
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
        if user.is_superuser and user.rol != GERENCIA:
            return True
        if getattr(user, 'estado', None) != 'activo' or getattr(user, 'deleted_at', None):
            return False
        if user.rol == GERENCIA:
            return request.method in SAFE_METHODS
        allowed = self.role_actions.get(view.action, set())
        return user.rol == ADMIN_GENERAL or user.rol in allowed


class UserPermission(RolePermission):
    role_actions = {
        'list': {ADMIN_GENERAL}, 'retrieve': {ADMIN_GENERAL}, 'create': {ADMIN_GENERAL},
        'update': {ADMIN_GENERAL}, 'partial_update': {ADMIN_GENERAL}, 'destroy': {ADMIN_GENERAL},
        'activar': {ADMIN_GENERAL},
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
        'decision_cliente': {FINANZAS}, 'aprobar_gerencia': {ADMIN_GENERAL},
        'exigir_aprobacion': {ADMIN_GENERAL}, 'historial_versiones': {FINANZAS},
    }


class ObraPermission(RolePermission):
    role_actions = {
        'list': {FINANZAS, SUPERVISOR, TECNICO}, 'retrieve': {FINANZAS, SUPERVISOR, TECNICO},
        'create': {SUPERVISOR}, 'update': {SUPERVISOR}, 'partial_update': {SUPERVISOR}, 'destroy': {SUPERVISOR},
        'transicionar': {SUPERVISOR}, 'cerrar_comercial': {FINANZAS}, 'reabrir': {ADMIN_GENERAL},
        'presupuestos_disponibles': {SUPERVISOR}, 'tecnicos_disponibles': {SUPERVISOR},
        'agenda_tecnico': {SUPERVISOR, TECNICO},
        'historial_estados': {FINANZAS, SUPERVISOR, TECNICO},
    }


class MaterialPermission(RolePermission):
    role_actions = {
        'list': {SUPERVISOR}, 'retrieve': {SUPERVISOR},
        'saldos_totales': {SUPERVISOR},
        'materiales': {SUPERVISOR}, 'registrar_merma': {SUPERVISOR}, 'registrar_movimiento_material': {SUPERVISOR},
    }


class CostoPermission(RolePermission):
    role_actions = {
        'list': {FINANZAS, SUPERVISOR}, 'retrieve': {FINANZAS, SUPERVISOR},
        'create': {FINANZAS, SUPERVISOR}, 'update': {FINANZAS, SUPERVISOR},
        'partial_update': {FINANZAS, SUPERVISOR}, 'destroy': {FINANZAS, SUPERVISOR},
        'despachos': {FINANZAS, SUPERVISOR},
    }


class FacturaPermission(RolePermission):
    role_actions = {
        'list': {FINANZAS}, 'retrieve': {FINANZAS}, 'create': {FINANZAS},
        'update': {FINANZAS}, 'partial_update': {FINANZAS}, 'destroy': {FINANZAS},
        'notas_credito': {FINANZAS}, 'pendientes': {FINANZAS},
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
        'create': {ADMIN_GENERAL}, 'update': {ADMIN_GENERAL}, 'partial_update': {ADMIN_GENERAL}, 'destroy': {ADMIN_GENERAL},
    }


class AuditoriaPermission(RolePermission):
    pass


class GastoGeneralPermission(RolePermission):
    role_actions = {
        'list': {FINANZAS}, 'retrieve': {FINANZAS}, 'create': {FINANZAS},
        'update': {FINANZAS}, 'partial_update': {FINANZAS}, 'destroy': {FINANZAS},
    }


class ProveedorPermission(RolePermission):
    role_actions = {
        'list': {FINANZAS, SUPERVISOR}, 'retrieve': {FINANZAS, SUPERVISOR},
        'create': {FINANZAS}, 'update': {FINANZAS}, 'partial_update': {FINANZAS},
    }


class DashboardPermission(BasePermission):
    allowed_roles = {ADMIN_GENERAL, GERENCIA}

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
