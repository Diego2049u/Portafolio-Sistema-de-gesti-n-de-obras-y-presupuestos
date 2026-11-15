"""Administración de Django para el MVP de FYAG.

Criterio de diseño:
- Los datos maestros (usuarios, clientes, contratos y categorías de servicio)
  se pueden crear y editar desde el admin.
- Los registros operativos y financieros (presupuestos, ítems, obras, costos,
  facturas, pagos, notas de crédito, reversas, versiones e historial) quedan en
  solo lectura. Sus reglas viven en la API (`api/services.py`); editarlos a mano
  saltaría los workflows, la auditoría y las validaciones de saldo.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import (
    AuditoriaLog, CategoriaServicio, Cliente, Contrato, CostoMaterial, Factura,
    ItemPresupuesto, NotaCredito, Obra, ObraEstadoHistorial, Pago, Presupuesto,
    ReversaPago, Usuario, VersionPresupuesto,
)

admin.site.site_header = 'FYAG Obras y Presupuestos'
admin.site.site_title = 'FYAG'
admin.site.index_title = 'Administración de datos'


class SoloLecturaAdmin(admin.ModelAdmin):
    """Permite consultar, filtrar y buscar, pero no crear, editar ni eliminar."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Usuario)
class UsuarioAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'get_full_name', 'rol', 'estado', 'is_active', 'is_staff')
    list_filter = ('rol', 'estado', 'is_active', 'is_staff')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'rut_usuario')
    ordering = ('username',)
    readonly_fields = ('last_login', 'date_joined')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Datos FYAG', {'fields': ('rut_usuario', 'cargo', 'rol', 'estado')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Datos FYAG', {'fields': ('email', 'cargo', 'rol', 'estado')}),
    )

    def save_model(self, request, obj, form, change):
        # rut_usuario es único y opcional: evita guardar '' y chocar con otro usuario.
        obj.rut_usuario = obj.rut_usuario or None
        super().save_model(request, obj, form, change)


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('codigo_cliente', 'razon_social', 'rut_cliente', 'sector', 'estado', 'habilitar_emision')
    list_filter = ('estado', 'sector', 'habilitar_emision')
    search_fields = ('codigo_cliente', 'razon_social', 'rut_cliente', 'correo_contacto')
    ordering = ('razon_social',)


@admin.register(Contrato)
class ContratoAdmin(admin.ModelAdmin):
    list_display = ('numero_contrato', 'nombre', 'cliente', 'estado', 'fecha_inicio', 'fecha_termino')
    list_filter = ('estado', 'fecha_inicio')
    search_fields = ('numero_contrato', 'nombre', 'cliente__razon_social')
    autocomplete_fields = ('cliente',)
    date_hierarchy = 'fecha_inicio'


@admin.register(CategoriaServicio)
class CategoriaServicioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'orden')
    list_editable = ('orden',)
    search_fields = ('nombre',)
    ordering = ('orden', 'nombre')


@admin.register(Presupuesto)
class PresupuestoAdmin(SoloLecturaAdmin):
    list_display = ('numero_presupuesto', 'cliente', 'categoria_servicio', 'estado',
                    'aprobacion_gerencia', 'monto_total', 'fecha_emision')
    list_filter = ('estado', 'aprobacion_gerencia', 'categoria_servicio', 'fecha_emision')
    search_fields = ('numero_presupuesto', 'cliente__razon_social', 'contacto')
    date_hierarchy = 'fecha_emision'
    ordering = ('-fecha_emision', '-id')


@admin.register(ItemPresupuesto)
class ItemPresupuestoAdmin(SoloLecturaAdmin):
    list_display = ('presupuesto', 'descripcion', 'cantidad', 'unidad', 'precio_unitario', 'subtotal')
    search_fields = ('presupuesto__numero_presupuesto', 'descripcion')
    ordering = ('presupuesto', 'id')

    @admin.display(description='Subtotal')
    def subtotal(self, obj):
        return obj.subtotal


@admin.register(Obra)
class ObraAdmin(SoloLecturaAdmin):
    list_display = ('codigo_obra', 'nombre_obra', 'cliente', 'tecnico_responsable',
                    'estado_operativo', 'estado_comercial', 'avance_porcentaje', 'fecha_inicio')
    list_filter = ('estado_operativo', 'estado_comercial', 'clasificacion_servicio', 'tecnico_responsable')
    search_fields = ('codigo_obra', 'nombre_obra', 'presupuesto__numero_presupuesto',
                     'presupuesto__cliente__razon_social')
    date_hierarchy = 'fecha_inicio'
    ordering = ('-fecha_inicio', '-id')

    @admin.display(description='Cliente')
    def cliente(self, obj):
        return obj.presupuesto.cliente.razon_social


@admin.register(CostoMaterial)
class CostoMaterialAdmin(SoloLecturaAdmin):
    list_display = ('obra', 'categoria', 'monto', 'fecha', 'descripcion_corta')
    list_filter = ('categoria', 'fecha')
    search_fields = ('obra__codigo_obra', 'descripcion')
    date_hierarchy = 'fecha'
    ordering = ('-fecha', '-id')

    @admin.display(description='Descripción')
    def descripcion_corta(self, obj):
        return obj.descripcion[:60]


@admin.register(Factura)
class FacturaAdmin(SoloLecturaAdmin):
    list_display = ('numero_factura', 'obra', 'cliente', 'fecha_emision', 'fecha_vencimiento',
                    'monto_total', 'saldo_pendiente', 'estado_pago')
    list_filter = ('estado_pago', 'fecha_emision', 'fecha_vencimiento')
    search_fields = ('numero_factura', 'obra__codigo_obra', 'obra__presupuesto__cliente__razon_social')
    date_hierarchy = 'fecha_emision'
    ordering = ('-fecha_emision', '-id')

    @admin.display(description='Cliente')
    def cliente(self, obj):
        return obj.obra.presupuesto.cliente.razon_social


@admin.register(Pago)
class PagoAdmin(SoloLecturaAdmin):
    list_display = ('factura', 'monto', 'fecha_pago', 'metodo_pago', 'folio_recibo')
    list_filter = ('metodo_pago', 'fecha_pago')
    search_fields = ('factura__numero_factura', 'folio_recibo', 'comprobante')
    date_hierarchy = 'fecha_pago'
    ordering = ('-fecha_pago', '-id')


@admin.register(NotaCredito)
class NotaCreditoAdmin(SoloLecturaAdmin):
    list_display = ('numero', 'factura', 'monto', 'usuario', 'fecha')
    list_filter = ('fecha',)
    search_fields = ('numero', 'factura__numero_factura', 'motivo')
    ordering = ('-fecha', '-id')


@admin.register(ReversaPago)
class ReversaPagoAdmin(SoloLecturaAdmin):
    list_display = ('pago', 'monto', 'usuario', 'fecha')
    list_filter = ('fecha',)
    search_fields = ('pago__factura__numero_factura', 'motivo')
    ordering = ('-fecha', '-id')


@admin.register(VersionPresupuesto)
class VersionPresupuestoAdmin(SoloLecturaAdmin):
    list_display = ('presupuesto', 'numero_version', 'usuario', 'fecha')
    list_filter = ('fecha',)
    search_fields = ('presupuesto__numero_presupuesto',)
    ordering = ('-fecha', '-id')


@admin.register(ObraEstadoHistorial)
class ObraEstadoHistorialAdmin(SoloLecturaAdmin):
    list_display = ('obra', 'estado_anterior', 'estado_nuevo', 'usuario', 'fecha')
    list_filter = ('estado_nuevo', 'fecha')
    search_fields = ('obra__codigo_obra', 'observacion')
    date_hierarchy = 'fecha'
    ordering = ('-fecha', '-id')


@admin.register(AuditoriaLog)
class AuditoriaLogAdmin(SoloLecturaAdmin):
    list_display = ('fecha', 'usuario', 'modulo', 'accion', 'resultado', 'entidad', 'entidad_id')
    list_filter = ('resultado', 'modulo', 'fecha')
    search_fields = ('accion', 'detalle', 'entidad', 'entidad_id', 'usuario__email')
    date_hierarchy = 'fecha'
    ordering = ('-fecha', '-id')
