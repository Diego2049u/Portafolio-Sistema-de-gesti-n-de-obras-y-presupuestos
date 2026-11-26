from django.db.models import Exists, F, OuterRef, Q, Subquery, Sum
from django.db.models.functions import Coalesce
from django.db import transaction
from django.core.cache import cache
from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
import hashlib
import json
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .dashboard import construir_resumen_dashboard
from .dashboard_serializers import DashboardFiltroSerializer
from .rentabilidad import despachos_pendientes, detallar_otros_costos
from .models import (
    AuditoriaLog, CategoriaServicio, Cliente, Contrato, CostoMaterial, Factura, GastoGeneral, Material,
    MovimientoMaterial, NotaCredito, Obra, ObraEstadoHistorial, ObraMaterial, Pago, Presupuesto, Proveedor, Usuario, VersionPresupuesto,
)
from .permissions import (
    AuditoriaPermission, CategoriaServicioPermission, ClientePermission,
    ContratoPermission, CostoPermission, FacturaPermission, GastoGeneralPermission, MaterialPermission, ObraPermission,
    PagoPermission, PresupuestoPermission, ProveedorPermission, UserPermission, DashboardPermission,
)
from .serializers import (
    AuditoriaLogSerializer, CategoriaServicioSerializer, ClienteSerializer,
    ContratoSerializer, CostoMaterialSerializer, EstablecerPasswordSerializer, FacturaSerializer, GastoGeneralSerializer,
    MaterialSerializer, MermaMaterialSerializer, MovimientoMaterialSerializer, NotaCreditoSerializer, ObraMaterialSerializer,
    ObraSerializer, PagoSerializer, PresupuestoSerializer,
    ProveedorSerializer, ReversaPagoSerializer, UsuarioSerializer,
)
from .services import (
    cerrar_obra_comercial, decidir_aprobacion_gerencia, exigir_aprobacion_gerencia, registrar_decision_cliente,
    registrar_evento, registrar_pago, enviar_presupuesto, soft_delete_instance,
    registrar_nota_credito, reabrir_obra, revertir_pago, transicionar_obra,
)
from .pdf_generador import generar_pdf_presupuesto
from .disponibilidad import CHILE, agenda, evaluar, validar_rango
from datetime import date, datetime, time, timedelta
from django.utils import timezone
from rest_framework import serializers


class PeriodoDisponibilidadSerializer(serializers.Serializer):
    inicio = serializers.DateTimeField(default_timezone=CHILE)
    fin = serializers.DateTimeField(default_timezone=CHILE)

    def validate(self, attrs):
        validar_rango(attrs['inicio'], attrs['fin'])
        return attrs


def periodo_disponibilidad(params):
    if not params.get('inicio') and not params.get('fin'):
        hoy = timezone.localdate(timezone=CHILE)
        lunes = hoy - timedelta(days=hoy.weekday())
        return datetime.combine(lunes, time(8), CHILE), datetime.combine(lunes + timedelta(days=4), time(18), CHILE)
    filtro = PeriodoDisponibilidadSerializer(data=params)
    filtro.is_valid(raise_exception=True)
    return filtro.validated_data['inicio'], filtro.validated_data['fin']


def _apply_date_range(queryset, params, field):
    """Apply the shared `desde`/`hasta` YYYY-MM-DD query contract."""
    bounds = {}
    for key, lookup in (('desde', 'gte'), ('hasta', 'lte')):
        raw = params.get(key)
        if not raw:
            continue
        try:
            value = serializers.DateField().run_validation(raw)
        except ValidationError as exc:
            raise ValidationError({key: exc.detail}) from exc
        bounds[f'{field}__{lookup}'] = value
    if 'desde' in params and 'hasta' in params and bounds:
        if bounds.get(f'{field}__gte') and bounds.get(f'{field}__lte') and bounds[f'{field}__gte'] > bounds[f'{field}__lte']:
            raise ValidationError({'desde': 'La fecha inicial debe ser anterior o igual a la fecha final.'})
    return queryset.filter(**bounds) if bounds else queryset


class AuditedModelViewSet(viewsets.ModelViewSet):
    module_name = 'Sistema'

    @staticmethod
    def snapshot_instance(instance):
        values = {}
        for field in instance._meta.concrete_fields:
            if field.name in {'password', 'last_login'}:
                continue
            values[field.name] = getattr(instance, field.attname)
        if isinstance(instance, Presupuesto):
            values['items'] = list(instance.items.filter(deleted_at__isnull=True).order_by('id').values(
                'descripcion', 'cantidad', 'unidad', 'precio_unitario',
            ))
        return json.loads(json.dumps(values, cls=DjangoJSONEncoder))

    @transaction.atomic
    def perform_create(self, serializer):
        model = serializer.Meta.model
        fields = {field.name for field in model._meta.concrete_fields}
        actor_values = {key: self.request.user for key in ('created_by', 'updated_by') if key in fields}
        instance = serializer.save(**actor_values)
        if isinstance(instance, Obra):
            ObraEstadoHistorial.objects.create(obra=instance, estado_anterior='', estado_nuevo=instance.estado_operativo, usuario=self.request.user, observacion='Estado inicial')
        registrar_evento(usuario=self.request.user, modulo=self.module_name, accion='crear', resultado='exito', detalle=f"Registro creado: {instance}.", entidad=instance.__class__.__name__, entidad_id=instance.pk, valores_nuevos=self.snapshot_instance(instance))

    @transaction.atomic
    def perform_update(self, serializer):
        instance = serializer.instance
        anterior = self.snapshot_instance(instance)
        fields = {field.name for field in instance._meta.concrete_fields}
        actor_values = {'updated_by': self.request.user} if 'updated_by' in fields else {}
        instance = serializer.save(**actor_values)
        registrar_evento(usuario=self.request.user, modulo=self.module_name, accion='actualizar', resultado='exito', detalle=f"Registro actualizado: {instance}.", entidad=instance.__class__.__name__, entidad_id=instance.pk, valores_anteriores=anterior, valores_nuevos=self.snapshot_instance(instance))

    @transaction.atomic
    def perform_destroy(self, instance):
        anterior = self.snapshot_instance(instance)
        soft_delete_instance(instance, self.request.user, valores_anteriores=anterior)

    def handle_exception(self, exc):
        user = getattr(self.request, 'user', None)
        if user and user.is_authenticated:
            detail = getattr(exc, 'detail', str(exc))
            detail_text = str(detail)[:1000]
            incompleto = any(word in detail_text.lower() for word in ('required', 'obligatorio', 'falta', 'incompleto', 'requerido', 'datos_incompletos'))
            accion = 'eliminacion_fallida' if getattr(self, 'action', None) == 'destroy' else 'operacion_fallida'
            model = getattr(getattr(self, 'queryset', None), 'model', None)
            registrar_evento(
                usuario=user,
                modulo=self.module_name,
                accion=accion,
                resultado='incompleto' if incompleto else 'error',
                detalle=detail_text,
                entidad=model.__name__ if model else '',
                entidad_id=self.kwargs.get(self.lookup_url_kwarg or self.lookup_field, ''),
                metadata={'accion_solicitada': getattr(self, 'action', '')},
            )
        return super().handle_exception(exc)


class UsuarioViewSet(AuditedModelViewSet):
    queryset = Usuario.objects.all().order_by('last_name', 'first_name')
    serializer_class = UsuarioSerializer
    permission_classes = [UserPermission]
    module_name = 'Usuarios'

    @action(detail=True, methods=['post'])
    def activar(self, request, pk=None):
        usuario = self.get_object()
        estado_anterior = usuario.estado
        activo_anterior = usuario.is_active
        serializer = EstablecerPasswordSerializer(data=request.data, context={'user': usuario})
        serializer.is_valid(raise_exception=True)
        usuario.set_password(serializer.validated_data['password'])
        usuario.estado = 'activo'
        usuario.is_active = True
        usuario.save(update_fields=['password', 'estado', 'is_active'])
        from .auth_views import revocar_refresh_usuario
        revocar_refresh_usuario(usuario)
        registrar_evento(usuario=request.user, modulo='Usuarios', accion='activar_cuenta', resultado='exito', detalle=f'Se activó o restableció la cuenta {usuario.email}.', entidad='Usuario', entidad_id=usuario.pk, valores_anteriores={'estado': estado_anterior, 'is_active': activo_anterior}, valores_nuevos={'estado': usuario.estado, 'is_active': usuario.is_active, 'password_actualizada': True})
        return Response(self.get_serializer(usuario).data)


class ClienteViewSet(AuditedModelViewSet):
    queryset = Cliente.objects.order_by('razon_social', 'pk')
    serializer_class = ClienteSerializer
    permission_classes = [ClientePermission]
    module_name = 'Clientes y Contratos'

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params
        q = params.get('q', '').strip()
        if q:
            queryset = queryset.filter(Q(codigo_cliente__icontains=q) | Q(rut_cliente__icontains=q) | Q(razon_social__icontains=q) | Q(giro_comercial__icontains=q) | Q(contacto_principal__icontains=q) | Q(correo_contacto__icontains=q))
        for field in ('estado', 'sector'):
            if params.get(field):
                queryset = queryset.filter(**{field: params[field]})
        return queryset


class ContratoViewSet(AuditedModelViewSet):
    queryset = Contrato.objects.select_related('cliente').all()
    serializer_class = ContratoSerializer
    permission_classes = [ContratoPermission]
    module_name = 'Clientes y Contratos'

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params
        q = params.get('q', '').strip()
        if q:
            queryset = queryset.filter(Q(numero_contrato__icontains=q) | Q(nombre__icontains=q) | Q(cliente__razon_social__icontains=q))
        if params.get('cliente_id'):
            queryset = queryset.filter(cliente_id=params['cliente_id'])
        if params.get('estado'):
            queryset = queryset.filter(estado=params['estado'])
        return _apply_date_range(queryset, params, 'fecha_inicio')


class CategoriaServicioViewSet(AuditedModelViewSet):
    queryset = CategoriaServicio.objects.all()
    serializer_class = CategoriaServicioSerializer
    permission_classes = [CategoriaServicioPermission]
    module_name = 'Categorías de servicio'

    def get_queryset(self):
        queryset = super().get_queryset()
        q = self.request.query_params.get('q', '').strip()
        return queryset.filter(nombre__icontains=q) if q else queryset


class PresupuestoViewSet(AuditedModelViewSet):
    queryset = Presupuesto.objects.select_related('cliente', 'categoria_servicio').prefetch_related('items').order_by('pk')
    serializer_class = PresupuestoSerializer
    permission_classes = [PresupuestoPermission]
    module_name = 'Presupuestos'

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params
        q = params.get('q', '').strip()
        if q:
            queryset = queryset.filter(Q(numero_presupuesto__icontains=q) | Q(cliente__razon_social__icontains=q) | Q(contacto__icontains=q) | Q(items__descripcion__icontains=q)).distinct()
        for param, field in (('cliente_id', 'cliente_id'), ('categoria_servicio_id', 'categoria_servicio_id'), ('estado', 'estado'), ('aprobacion_gerencia', 'aprobacion_gerencia')):
            if params.get(param):
                queryset = queryset.filter(**{field: params[param]})
        return _apply_date_range(queryset, params, 'fecha_emision')

    @action(detail=True, methods=['post'])
    def enviar(self, request, pk=None):
        presupuesto = enviar_presupuesto(self.get_object(), request.user)
        return Response(self.get_serializer(presupuesto).data)

    @action(detail=True, methods=['post'], url_path='decision-cliente')
    def decision_cliente(self, request, pk=None):
        presupuesto = registrar_decision_cliente(self.get_object(), request.data.get('decision'), request.user)
        return Response(self.get_serializer(presupuesto).data)

    @action(detail=True, methods=['post'], url_path='aprobar-gerencia')
    def aprobar_gerencia(self, request, pk=None):
        presupuesto = decidir_aprobacion_gerencia(self.get_object(), request.data.get('decision'), request.user)
        return Response(self.get_serializer(presupuesto).data)

    @action(detail=True, methods=['post'], url_path='exigir-aprobacion-gerencia')
    def exigir_aprobacion(self, request, pk=None):
        presupuesto = exigir_aprobacion_gerencia(self.get_object(), request.user)
        return Response(self.get_serializer(presupuesto).data)

    @action(detail=True, methods=['get'], url_path='historial-versiones')
    def historial_versiones(self, request, pk=None):
        presupuesto = self.get_object()
        versiones = VersionPresupuesto.objects.filter(presupuesto=presupuesto).select_related('usuario')
        return Response([{
            'id': version.pk,
            'numero_version': version.numero_version,
            'snapshot': version.snapshot,
            'usuario_id': version.usuario_id,
            'usuario_nombre': version.usuario.get_full_name() if version.usuario else None,
            'fecha': version.fecha,
        } for version in versiones])

    @action(detail=True, methods=['get'], url_path='exportar-pdf')
    def exportar_pdf(self, request, pk=None):
        presupuesto = self.get_object()
        pdf_buffer = generar_pdf_presupuesto(presupuesto)
        response = HttpResponse(pdf_buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Presupuesto_{presupuesto.numero_presupuesto}.pdf"'
        return response


class MaterialViewSet(AuditedModelViewSet):
    queryset = Material.objects.all()
    serializer_class = MaterialSerializer
    permission_classes = [MaterialPermission]
    http_method_names = ['get', 'post', 'patch', 'head', 'options']
    module_name = 'Recursos'

    @action(detail=False, methods=['get'], url_path='saldos-totales')
    def saldos_totales(self, request):
        materiales = {
            material.pk: {
                'id': material.pk, 'nombre': material.nombre, 'unidad': material.unidad,
                'saldo': None, 'sin_entradas': 0, 'obras': [],
            }
            for material in Material.objects.order_by('nombre', 'pk')
        }
        asignaciones = ObraMaterial.objects.filter(obra__deleted_at__isnull=True).select_related(
            'obra',
        ).prefetch_related('movimientos', 'mermas').order_by('obra__codigo_obra', 'pk')
        for asignacion in asignaciones:
            material = materiales.get(asignacion.material_id)
            if material is None:
                continue
            saldo = asignacion.saldo_registrado()
            if saldo is None:
                material['sin_entradas'] += 1
            else:
                material['saldo'] = (material['saldo'] or 0) + saldo
            material['obras'].append({
                'codigo': asignacion.obra.codigo_obra,
                'nombre': asignacion.obra.nombre_obra,
                'saldo': str(saldo) if saldo is not None else None,
            })
        for material in materiales.values():
            if material['saldo'] is not None:
                material['saldo'] = str(material['saldo'])
        return Response(list(materiales.values()))

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.query_params.get('activo') == '1':
            queryset = queryset.filter(activo=True)
        return queryset


class ObraViewSet(AuditedModelViewSet):
    queryset = Obra.objects.select_related('presupuesto__cliente', 'tecnico_responsable', 'clasificacion_servicio').order_by('pk')
    serializer_class = ObraSerializer
    permission_classes = [ObraPermission]
    module_name = 'Obras y Proyectos'

    @action(detail=True, methods=['get'], url_path='materiales', permission_classes=[MaterialPermission])
    def materiales(self, request, pk=None):
        asignaciones = self.get_object().materiales.select_related('material').prefetch_related('mermas', 'movimientos')
        return Response(ObraMaterialSerializer(asignaciones, many=True).data)

    @action(detail=True, methods=['post'], url_path=r'materiales/(?P<asignacion_id>[0-9]+)/mermas',
            permission_classes=[MaterialPermission])
    @transaction.atomic
    def registrar_merma(self, request, pk=None, asignacion_id=None):
        obra = get_object_or_404(Obra.objects.select_for_update(), pk=self.get_object().pk)
        if obra.estado_operativo != 'en-proceso' or obra.estado_comercial == 'cerrada':
            raise ValidationError({'obra': 'Solo puedes registrar merma en una obra en proceso.'})
        asignacion = get_object_or_404(ObraMaterial, pk=asignacion_id, obra=obra)
        serializer = MermaMaterialSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        saldo = asignacion.saldo_registrado()
        if saldo is not None and serializer.validated_data['cantidad'] > saldo:
            raise ValidationError({'cantidad': 'La merma supera el saldo registrado.'})
        merma = serializer.save(asignacion=asignacion, registrado_por=request.user)
        registrar_evento(usuario=request.user, modulo='Recursos', accion='crear', resultado='exito',
                        detalle=f'Merma registrada en {obra.codigo_obra}.', entidad='MermaMaterial',
                        entidad_id=merma.pk, valores_nuevos=self.snapshot_instance(merma))
        return Response({**serializer.data, 'saldo': str(saldo - merma.cantidad) if saldo is not None else None}, status=201)

    @action(detail=True, methods=['post'], url_path=r'materiales/(?P<asignacion_id>[0-9]+)/movimientos',
            permission_classes=[MaterialPermission])
    @transaction.atomic
    def registrar_movimiento_material(self, request, pk=None, asignacion_id=None):
        obra = get_object_or_404(Obra.objects.select_for_update(), pk=self.get_object().pk)
        if obra.estado_operativo != 'en-proceso' or obra.estado_comercial == 'cerrada':
            raise ValidationError({'obra': 'Solo puedes registrar movimientos en una obra en proceso.'})
        asignacion = get_object_or_404(ObraMaterial.objects.select_related('material'), pk=asignacion_id, obra=obra)
        serializer = MovimientoMaterialSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        saldo = asignacion.saldo_registrado()
        cantidad = serializer.validated_data['cantidad']
        referencia = serializer.validated_data.get('referencia', '')
        if serializer.validated_data['tipo'] == MovimientoMaterial.Tipo.CONSUMO:
            if referencia:
                raise ValidationError({'referencia': 'La referencia de despacho se usa en las entradas.'})
            if saldo is None or cantidad > saldo:
                raise ValidationError({'cantidad': 'El consumo requiere un saldo registrado suficiente.'})
        else:
            entradas = asignacion.movimientos.filter(tipo=MovimientoMaterial.Tipo.ENTRADA)
            if referencia and entradas.filter(referencia__iexact=referencia).exists():
                raise ValidationError({'referencia': 'Este despacho ya está registrado para el material.'})
            if not referencia and entradas.filter(
                fecha__date=timezone.localdate(), cantidad=cantidad,
                motivo__iexact=serializer.validated_data['motivo'],
            ).exists():
                raise ValidationError({'referencia': 'Ya hay una entrada igual hoy. Si es otro despacho, indique su referencia.'})
            if saldo is None and cantidad < sum(merma.cantidad for merma in asignacion.mermas.all()):
                raise ValidationError({'cantidad': 'La entrada inicial debe incluir las mermas ya registradas.'})
        movimiento = serializer.save(asignacion=asignacion, registrado_por=request.user)
        registrar_evento(usuario=request.user, modulo='Recursos', accion='registrar_movimiento',
                         resultado='exito', detalle=movimiento.motivo, entidad='MovimientoMaterial',
                         entidad_id=movimiento.pk, valores_nuevos=self.snapshot_instance(movimiento))
        return Response(ObraMaterialSerializer(asignacion).data, status=201)

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.rol in {'ADMIN_GENERAL', 'FINANZAS'}:
            facturas = Factura.objects.filter(obra_id=OuterRef('pk'))
            queryset = queryset.annotate(
                puede_cerrar_comercial=(
                    Q(estado_operativo='finalizada') & ~Q(estado_comercial='cerrada')
                    & Exists(facturas) & ~Exists(facturas.filter(saldo_pendiente__gt=0))
                ),
            )
        if self.request.user.rol == 'TECNICO':
            queryset = queryset.filter(tecnico_responsable=self.request.user)
        params = self.request.query_params
        q = params.get('q', '').strip()
        if q:
            queryset = queryset.filter(Q(codigo_obra__icontains=q) | Q(nombre_obra__icontains=q) | Q(presupuesto__numero_presupuesto__icontains=q) | Q(presupuesto__cliente__razon_social__icontains=q) | Q(tecnico_responsable__first_name__icontains=q) | Q(tecnico_responsable__last_name__icontains=q))
        for param, field in (('cliente_id', 'presupuesto__cliente_id'), ('tecnico_id', 'tecnico_responsable_id'), ('estado', 'estado_operativo'), ('estado_comercial', 'estado_comercial'), ('categoria_servicio_id', 'clasificacion_servicio_id')):
            if params.get(param):
                queryset = queryset.filter(**{field: params[param]})
        return _apply_date_range(queryset, params, 'fecha_inicio')

    @action(detail=False, methods=['get'], url_path='presupuestos-disponibles')
    def presupuestos_disponibles(self, request):
        disponibles = Presupuesto.objects.filter(estado='aprobado').exclude(obra__isnull=False).select_related('cliente')
        return Response([{
            'id': item.pk,
            'numero_presupuesto': item.numero_presupuesto,
            'cliente': item.cliente.razon_social,
            'categoria_servicio': item.categoria_servicio_id,
            'categoria_servicio_nombre': item.categoria_servicio.nombre,
        } for item in disponibles])

    @action(detail=False, methods=['get'], url_path='tecnicos-disponibles')
    def tecnicos_disponibles(self, request):
        inicio, fin = periodo_disponibilidad(request.query_params)
        excluir = serializers.IntegerField(required=False, min_value=1).run_validation(request.query_params['excluir']) if request.query_params.get('excluir') else None
        tecnicos = Usuario.objects.filter(rol='TECNICO', estado='activo', is_active=True).order_by('first_name', 'last_name', 'id')
        return Response([{'id': t.pk, 'first_name': t.first_name, 'last_name': t.last_name,
                          'nombre': t.get_full_name(), 'especialidad': t.cargo,
                          **evaluar(t.pk, inicio, fin, excluir)} for t in tecnicos])

    @action(detail=False, methods=['get'], url_path='agenda-tecnico')
    def agenda_tecnico(self, request):
        from django.shortcuts import get_object_or_404
        # El técnico nunca puede consultar la agenda de otro usuario.
        tecnico_id = request.user.pk if request.user.rol == 'TECNICO' else request.query_params.get('tecnico_id')
        if not tecnico_id or not str(tecnico_id).isdigit():
            raise ValidationError({'tecnico_id': 'Seleccione un técnico válido.'})
        tecnico = get_object_or_404(Usuario.objects, pk=tecnico_id, rol='TECNICO')
        desde = serializers.DateField().run_validation(request.query_params.get('desde'))
        hasta = serializers.DateField().run_validation(request.query_params.get('hasta'))
        if desde > hasta or (hasta - desde).days > 366:
            raise ValidationError({'periodo': 'Consulte entre 1 y 367 días consecutivos.'})
        if hasta == date.max:
            raise ValidationError({'hasta': 'Elija una fecha final anterior al límite del calendario.'})
        return Response(agenda(tecnico, datetime.combine(desde, time.min, CHILE), datetime.combine(hasta + timedelta(days=1), time.min, CHILE)))

    @action(detail=True, methods=['get'], url_path='historial-estados')
    def historial_estados(self, request, pk=None):
        obra = self.get_object()
        eventos = obra.historial_estados.select_related('usuario')
        return Response([{
            'id': evento.pk,
            'estado_anterior': evento.estado_anterior,
            'estado_nuevo': evento.estado_nuevo,
            'usuario_id': evento.usuario_id,
            'fecha': evento.fecha,
            'observacion': evento.observacion,
            'usuario_nombre': evento.usuario_nombre_finalizacion or (
                (evento.usuario.get_full_name() or evento.usuario.get_username()) if evento.usuario else None
            ),
            'usuario_rol_finalizacion': evento.usuario_rol_finalizacion or None,
            'usuario_rol_finalizacion_nombre': evento.get_usuario_rol_finalizacion_display() or None,
            'usuario_rol_actual_nombre': (
                evento.usuario.get_rol_display()
                if evento.estado_nuevo == 'finalizada' and not evento.usuario_rol_finalizacion and evento.usuario
                else None
            ),
        } for evento in eventos])

    @action(detail=True, methods=['post'], url_path='transicionar')
    def transicionar(self, request, pk=None):
        obra = transicionar_obra(
            self.get_object(), request.data.get('estado_operativo'), request.user,
            request.data.get('motivo', ''), costos_confirmados=request.data.get('costos_confirmados', False),
        )
        return Response(self.get_serializer(obra).data)

    @action(detail=True, methods=['post'])
    def reabrir(self, request, pk=None):
        obra = reabrir_obra(self.get_object(), request.user, request.data.get('motivo', ''))
        return Response(self.get_serializer(obra).data)

    @action(detail=True, methods=['post'], url_path='cerrar-comercial')
    def cerrar_comercial(self, request, pk=None):
        motivo = serializers.CharField(allow_blank=True, max_length=1000).run_validation(request.data.get('motivo', ''))
        obra = cerrar_obra_comercial(self.get_object(), request.user, motivo=motivo)
        return Response(self.get_serializer(obra).data)


class ProveedorViewSet(AuditedModelViewSet):
    queryset = Proveedor.objects.all()
    serializer_class = ProveedorSerializer
    permission_classes = [ProveedorPermission]
    http_method_names = ['get', 'post', 'patch', 'head', 'options']
    module_name = 'Proveedores'


class CostoMaterialViewSet(AuditedModelViewSet):
    queryset = CostoMaterial.objects.select_related('obra', 'proveedor').order_by('pk')
    serializer_class = CostoMaterialSerializer
    permission_classes = [CostoPermission]
    module_name = 'Costos de obra'

    @action(detail=False, methods=['get'], url_path=r'despachos/(?P<obra_id>[0-9]+)')
    def despachos(self, request, obra_id=None):
        obra = get_object_or_404(Obra, pk=obra_id)
        return Response(despachos_pendientes([obra.pk]).values(
            'id', 'cantidad', 'fecha', 'asignacion__material__nombre', 'asignacion__material__unidad',
        ))

    @staticmethod
    def bloquear_obra_costos(obra_id, despacho=None, excluir=None):
        obra = Obra.objects.select_for_update().get(pk=obra_id)
        if obra.estado_operativo in {'finalizada', 'cancelada'} or obra.estado_comercial == 'cerrada':
            raise ValidationError({'obra': 'La obra ya no admite cambios de costos.'})
        if despacho and CostoMaterial.objects.filter(despacho=despacho).exclude(pk=excluir).exists():
            raise ValidationError({'despacho': 'Este despacho ya tiene un costo registrado.'})

    @transaction.atomic
    def perform_create(self, serializer):
        self.bloquear_obra_costos(serializer.validated_data['obra'].pk, serializer.validated_data.get('despacho'))
        super().perform_create(serializer)

    @transaction.atomic
    def perform_update(self, serializer):
        costo = serializer.instance
        self.bloquear_obra_costos(costo.obra_id, serializer.validated_data.get('despacho', costo.despacho), costo.pk)
        super().perform_update(serializer)

    @transaction.atomic
    def perform_destroy(self, instance):
        self.bloquear_obra_costos(instance.obra_id)
        motivo = serializers.CharField(max_length=1000, allow_blank=True).run_validation(
            self.request.data.get('motivo', ''),
        )
        soft_delete_instance(instance, self.request.user, self.snapshot_instance(instance), motivo=motivo)

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params
        q = params.get('q', '').strip()
        if q:
            queryset = queryset.filter(Q(descripcion__icontains=q) | Q(obra__codigo_obra__icontains=q) | Q(obra__nombre_obra__icontains=q))
        for param, field in (('obra_id', 'obra_id'), ('cliente_id', 'obra__presupuesto__cliente_id'), ('tecnico_id', 'obra__tecnico_responsable_id'), ('estado', 'obra__estado_operativo'), ('categoria', 'categoria')):
            if params.get(param):
                queryset = queryset.filter(**{field: params[param]})
        return _apply_date_range(queryset, params, 'fecha')


class GastoGeneralViewSet(AuditedModelViewSet):
    queryset = GastoGeneral.objects.all()
    serializer_class = GastoGeneralSerializer
    permission_classes = [GastoGeneralPermission]
    module_name = 'Gastos generales'


class FacturaViewSet(AuditedModelViewSet):
    queryset = Factura.objects.select_related('obra__presupuesto__cliente').order_by('pk')
    serializer_class = FacturaSerializer
    permission_classes = [FacturaPermission]
    module_name = 'Facturación y Cobranza'

    @action(detail=False, methods=['get'], url_path='pendientes')
    def pendientes(self, request):
        hoy = timezone.localdate()
        facturas = Factura.objects.filter(obra_id=OuterRef('pk')).order_by()
        totales = facturas.values('obra_id').annotate(total=Sum('monto_total')).values('total')
        creditos = NotaCredito.objects.filter(
            factura__obra_id=OuterRef('pk'), factura__deleted_at__isnull=True,
        ).order_by().values('factura__obra_id').annotate(total=Sum('monto')).values('total')
        obras = Obra.objects.filter(estado_operativo='finalizada').exclude(estado_comercial='cerrada').annotate(
            tiene_factura=Exists(facturas),
            facturado=Coalesce(Subquery(totales), 0, output_field=Factura._meta.get_field('monto_total')),
            acreditado=Coalesce(Subquery(creditos), 0, output_field=Factura._meta.get_field('monto_total')),
        ).select_related('presupuesto__cliente').order_by(F('fecha_termino').asc(nulls_last=True), 'pk')
        pendientes = []
        for obra in obras:
            saldo = max(0, obra.presupuesto.monto_total - obra.facturado + obra.acreditado)
            if saldo or not obra.tiene_factura:
                pendientes.append({
                    'id': obra.pk, 'codigo': obra.codigo_obra, 'nombre': obra.nombre_obra,
                    'cliente': obra.presupuesto.cliente.razon_social, 'fecha_termino': obra.fecha_termino,
                    'dias': max(0, (hoy - obra.fecha_termino).days) if obra.fecha_termino else None,
                    'saldo': saldo, 'tiene_factura': obra.tiene_factura,
                })
        cobranza = Factura.objects.select_related('obra__presupuesto__cliente').filter(
            saldo_pendiente__gt=0, fecha_vencimiento__lte=hoy + timedelta(days=7),
        ).order_by('fecha_vencimiento', 'pk')
        return Response({'facturacion': pendientes, 'cobranza': [{
            'id': factura.pk, 'numero': factura.numero_factura,
            'cliente': factura.obra.presupuesto.cliente.razon_social,
            'vencimiento': factura.fecha_vencimiento, 'dias': (factura.fecha_vencimiento - hoy).days,
            'saldo': factura.saldo_pendiente,
        } for factura in cobranza]})

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params
        q = params.get('q', '').strip()
        if q:
            queryset = queryset.filter(Q(numero_factura__icontains=q) | Q(obra__codigo_obra__icontains=q) | Q(obra__nombre_obra__icontains=q) | Q(obra__presupuesto__cliente__razon_social__icontains=q))
        for param, field in (('cliente_id', 'obra__presupuesto__cliente_id'), ('tecnico_id', 'obra__tecnico_responsable_id'), ('obra_id', 'obra_id'), ('estado', 'estado_pago')):
            if params.get(param):
                queryset = queryset.filter(**{field: params[param]})
        return _apply_date_range(queryset, params, 'fecha_emision')

    @action(detail=True, methods=['get', 'post'], url_path='notas-credito')
    def notas_credito(self, request, pk=None):
        factura = self.get_object()
        if request.method == 'GET':
            return Response(list(factura.notas_credito.order_by('fecha', 'id').values('id', 'numero', 'monto', 'motivo', 'fecha', 'usuario_id')))
        serializer = NotaCreditoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        nota = registrar_nota_credito(factura, **serializer.validated_data, usuario=request.user)
        return Response({'id': nota.pk, 'factura': factura.pk, 'numero': nota.numero, 'monto': nota.monto, 'motivo': nota.motivo, 'fecha': nota.fecha})


class PagoViewSet(AuditedModelViewSet):
    queryset = Pago.objects.select_related('factura').order_by('pk')
    serializer_class = PagoSerializer
    permission_classes = [PagoPermission]
    module_name = 'Facturación y Cobranza'
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params
        q = params.get('q', '').strip()
        if q:
            queryset = queryset.filter(Q(factura__numero_factura__icontains=q) | Q(metodo_pago__icontains=q) | Q(comprobante__icontains=q) | Q(folio_recibo__icontains=q))
        for param, field in (('factura_id', 'factura_id'), ('cliente_id', 'factura__obra__presupuesto__cliente_id'), ('tecnico_id', 'factura__obra__tecnico_responsable_id')):
            if params.get(param):
                queryset = queryset.filter(**{field: params[param]})
        return _apply_date_range(queryset, params, 'fecha_pago')

    def perform_create(self, serializer):
        factura = serializer.validated_data['factura']
        datos = {key: value for key, value in serializer.validated_data.items() if key != 'factura'}
        pago = registrar_pago(factura, datos, self.request.user)
        serializer.instance = pago

    @action(detail=True, methods=['get', 'post'], url_path='reversas')
    def reversas(self, request, pk=None):
        pago = self.get_object()
        if request.method == 'GET':
            return Response(list(pago.reversiones.order_by('fecha', 'id').values('id', 'monto', 'motivo', 'fecha', 'usuario_id')))
        serializer = ReversaPagoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reversa = revertir_pago(pago, **serializer.validated_data, usuario=request.user)
        return Response({'id': reversa.pk, 'pago': pago.pk, 'monto': reversa.monto, 'motivo': reversa.motivo, 'fecha': reversa.fecha})


class AuditoriaLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditoriaLog.objects.select_related('usuario').all()
    serializer_class = AuditoriaLogSerializer
    permission_classes = [AuditoriaPermission]

    def get_queryset(self):
        queryset = super().get_queryset()
        modulo = self.request.query_params.get('modulo')
        resultado = self.request.query_params.get('resultado')
        params = self.request.query_params
        busqueda = self.request.query_params.get('q')
        if modulo:
            queryset = queryset.filter(modulo=modulo)
        if resultado in {'exito', 'error', 'incompleto'}:
            queryset = queryset.filter(resultado=resultado)
        if busqueda:
            queryset = queryset.filter(Q(accion__icontains=busqueda) | Q(detalle__icontains=busqueda) | Q(entidad__icontains=busqueda))
        return _apply_date_range(queryset, params, 'fecha__date')


class DashboardOtrosCostosView(APIView):
    permission_classes = [DashboardPermission]

    def get(self, request, obra_id):
        obra = get_object_or_404(Obra, pk=obra_id)
        return Response(detallar_otros_costos(obra))


class DashboardResumenView(APIView):
    permission_classes = [DashboardPermission]

    def get(self, request):
        filtros = DashboardFiltroSerializer(data=request.query_params)
        filtros.is_valid(raise_exception=True)
        force_refresh = request.query_params.get('actualizar') in {'1', 'true', 'si'}
        clave_datos = {'rol': request.user.rol, **{key: str(value) for key, value in filtros.validated_data.items()}}
        clave = 'dashboard:' + hashlib.sha256(json.dumps(clave_datos, sort_keys=True).encode()).hexdigest()
        if not force_refresh:
            cached = cache.get(clave)
            if cached is not None:
                return Response(cached)
        data = construir_resumen_dashboard(incluir_merma=request.user.rol in {'ADMIN_GENERAL', 'GERENCIA'}, **filtros.validated_data)
        cache.set(clave, data, timeout=15)
        return Response(data)
