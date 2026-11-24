from unicodedata import category, normalize

from django.http import FileResponse
from django.utils import timezone
from rest_framework import serializers
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from .exportar_reportes import exportar_excel, exportar_pdf
from .models import Cliente, Factura, Obra, Presupuesto, Usuario
from .permissions import ADMIN_GENERAL, FINANZAS, GERENCIA


REPORTES = {
    'obras': ('Obras y proyectos', 'Fecha de inicio', Obra.ESTADOS),
    'presupuestos': ('Presupuestos', 'Fecha de emisión', Presupuesto.ESTADOS),
    'cobranza': ('Facturación y cobranza', 'Fecha de emisión', Factura.ESTADOS_PAGO),
}


def tipos_permitidos(usuario):
    return ('cobranza',) if usuario.rol == FINANZAS else REPORTES.keys()


class ReportePermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return (
            user.is_authenticated and user.is_active and user.estado == 'activo'
            and not user.deleted_at and user.rol in {ADMIN_GENERAL, GERENCIA, FINANZAS}
        )


class ReporteConsultaSerializer(serializers.Serializer):
    tipo = serializers.ChoiceField(choices=list(REPORTES))
    salida = serializers.ChoiceField(choices=['vista', 'xlsx', 'pdf'], default='vista')
    desde = serializers.DateField(required=False)
    hasta = serializers.DateField(required=False)
    cliente_id = serializers.IntegerField(required=False, min_value=1)
    tecnico_id = serializers.IntegerField(required=False, min_value=1)
    estado = serializers.CharField(required=False, max_length=24)

    def validate(self, attrs):
        hasta = attrs.setdefault('hasta', timezone.localdate())
        desde = attrs.setdefault('desde', hasta.replace(day=1))
        if desde > hasta:
            raise serializers.ValidationError({'desde': 'La fecha inicial debe ser anterior o igual a la final.'})
        estados = dict(REPORTES[attrs['tipo']][2])
        if 'estado' in attrs and attrs['estado'] not in estados:
            raise serializers.ValidationError({'estado': 'Seleccione un estado disponible para este reporte.'})
        return attrs


def texto_limpio(value):
    if not isinstance(value, str):
        return value
    texto = normalize('NFC', value)
    return ' '.join(''.join(
        ' ' if char.isspace() else char
        for char in texto if char.isspace() or not category(char).startswith('C')
    ).split())


def obtener_reporte(tipo, desde, hasta, cliente_id=None, tecnico_id=None, estado=None):
    periodo = (desde, hasta)
    obras = Obra.objects.all()
    if cliente_id:
        obras = obras.filter(presupuesto__cliente_id=cliente_id)
    if tecnico_id:
        obras = obras.filter(tecnico_responsable_id=tecnico_id)

    if tipo == 'obras':
        filas = obras.filter(fecha_inicio__range=periodo).select_related(
            'presupuesto__cliente', 'tecnico_responsable', 'clasificacion_servicio',
        ).order_by('-fecha_inicio', '-pk')
        if estado:
            filas = filas.filter(estado_operativo=estado)
        return (
            ('Código', 'Obra', 'Cliente', 'Técnico', 'Servicio', 'Inicio', 'Término', 'Estado operativo', 'Estado comercial'),
            filas,
            fila_obra,
        )
    if tipo == 'presupuestos':
        filas = Presupuesto.objects.filter(fecha_emision__range=periodo).select_related(
            'cliente', 'categoria_servicio',
        ).order_by('-fecha_emision', '-pk')
        if cliente_id:
            filas = filas.filter(cliente_id=cliente_id)
        if tecnico_id:
            filas = filas.filter(pk__in=obras.values('presupuesto_id'))
        if estado:
            filas = filas.filter(estado=estado)
        return ('Folio', 'Cliente', 'Servicio', 'Emisión', 'Vencimiento', 'Estado', 'Total (CLP)'), filas, fila_presupuesto

    filas = Factura.objects.filter(obra__in=obras, fecha_emision__range=periodo).select_related(
        'obra__presupuesto__cliente', 'obra__tecnico_responsable',
    ).order_by('-fecha_emision', '-pk')
    if estado:
        filas = filas.filter(estado_pago=estado)
    return (
        ('Factura', 'Obra', 'Cliente', 'Técnico', 'Emisión', 'Vencimiento', 'Estado de pago', 'Total (CLP)', 'Saldo (CLP)'),
        filas,
        fila_factura,
    )


def fila_obra(obra):
    return (
        obra.codigo_obra, obra.nombre_obra, obra.presupuesto.cliente.razon_social,
        obra.tecnico_responsable.get_full_name() if obra.tecnico_responsable else '',
        obra.clasificacion_servicio.nombre, obra.fecha_inicio, obra.fecha_termino,
        obra.get_estado_operativo_display(), obra.get_estado_comercial_display(),
    )


def fila_presupuesto(presupuesto):
    return (
        presupuesto.numero_presupuesto, presupuesto.cliente.razon_social, presupuesto.categoria_servicio.nombre,
        presupuesto.fecha_emision, presupuesto.fecha_vencimiento, presupuesto.get_estado_display(),
        int(presupuesto.monto_total),
    )


def fila_factura(factura):
    obra = factura.obra
    return (
        factura.numero_factura, obra.codigo_obra, obra.presupuesto.cliente.razon_social,
        obra.tecnico_responsable.get_full_name() if obra.tecnico_responsable else '',
        factura.fecha_emision, factura.fecha_vencimiento, factura.get_estado_pago_display(),
        int(factura.monto_total), int(factura.saldo_pendiente),
    )


class ReporteFiltrosView(APIView):
    permission_classes = [ReportePermission]

    def get(self, request):
        clientes = Cliente.objects.order_by('razon_social', 'pk').values('id', 'razon_social')
        tecnicos = Usuario.objects.filter(rol='TECNICO').order_by('first_name', 'last_name', 'pk')
        permitidos = tipos_permitidos(request.user)
        hoy = timezone.localdate()
        return Response({
            'desde': hoy.replace(day=1),
            'hasta': hoy,
            'clientes': [{'id': c['id'], 'nombre': texto_limpio(c['razon_social'])} for c in clientes],
            'tecnicos': [{'id': t.pk, 'nombre': texto_limpio(t.get_full_name() or t.username)} for t in tecnicos],
            'tipos': [
                {'id': clave, 'nombre': nombre, 'fecha': fecha, 'estados': estados}
                for clave, (nombre, fecha, estados) in REPORTES.items() if clave in permitidos
            ],
        })


class ReporteView(APIView):
    permission_classes = [ReportePermission]

    def get(self, request):
        permitidos = tipos_permitidos(request.user)
        params = request.query_params.copy()
        params.setdefault('tipo', next(iter(permitidos)))
        consulta = ReporteConsultaSerializer(data=params)
        consulta.is_valid(raise_exception=True)
        filtros = consulta.validated_data.copy()
        salida = filtros.pop('salida')
        tipo = filtros['tipo']
        if tipo not in permitidos:
            raise PermissionDenied('Tu rol no puede consultar este tipo de reporte.')
        columnas, registros, construir_fila = obtener_reporte(**filtros)

        def filas_limpias(registros):
            for registro in registros:
                yield [texto_limpio(valor) for valor in construir_fila(registro)]

        if salida == 'vista':
            paginador = PageNumberPagination()
            pagina = paginador.paginate_queryset(registros, request, view=self)
            return paginador.get_paginated_response({
                'columnas': columnas,
                'filas': list(filas_limpias(pagina)),
            })

        titulo, fecha, _ = REPORTES[tipo]
        periodo = f"{fecha}: {filtros['desde']:%d-%m-%Y} a {filtros['hasta']:%d-%m-%Y}"
        filas = filas_limpias(registros.iterator(chunk_size=500))
        generar = exportar_excel if salida == 'xlsx' else exportar_pdf
        response = FileResponse(
            generar(titulo, periodo, columnas, filas), as_attachment=True, filename=f'reporte-{tipo}.{salida}',
        )
        response['Cache-Control'] = 'private, no-store'
        return response
