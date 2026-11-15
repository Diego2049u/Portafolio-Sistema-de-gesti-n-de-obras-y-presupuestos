from django.db.models import Q
from django.db import transaction
from django.core.cache import cache
from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponse
import hashlib
import json
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .dashboard import construir_resumen_dashboard
from .dashboard_serializers import DashboardFiltroSerializer
from .models import AuditoriaLog, CategoriaServicio, Cliente, Contrato, CostoMaterial, Factura, Obra, Pago, Presupuesto, Usuario
from .permissions import (
    AuditoriaPermission, CategoriaServicioPermission, ClientePermission,
    ContratoPermission, CostoPermission, FacturaPermission, ObraPermission,
    PagoPermission, PresupuestoPermission, UserPermission, DashboardPermission,
)
from .serializers import (
    AuditoriaLogSerializer, CategoriaServicioSerializer, ClienteSerializer,
    ContratoSerializer, CostoMaterialSerializer, EstablecerPasswordSerializer, FacturaSerializer,
    NotaCreditoSerializer, ObraSerializer, PagoSerializer, PresupuestoSerializer,
    ReversaPagoSerializer, UsuarioSerializer,
)
from .models import ObraEstadoHistorial, VersionPresupuesto
from .services import (
    cerrar_obra_comercial, decidir_aprobacion_gerencia, exigir_aprobacion_gerencia, registrar_decision_cliente,
    registrar_evento, registrar_pago, enviar_presupuesto, soft_delete_instance,
    registrar_nota_credito, reabrir_obra, revertir_pago, transicionar_obra,
)
from .pdf_generador import generar_pdf_presupuesto


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

    def perform_update(self, serializer):
        instance = serializer.instance
        anterior = self.snapshot_instance(instance)
        fields = {field.name for field in instance._meta.concrete_fields}
        actor_values = {'updated_by': self.request.user} if 'updated_by' in fields else {}
        instance = serializer.save(**actor_values)
        registrar_evento(usuario=self.request.user, modulo=self.module_name, accion='actualizar', resultado='exito', detalle=f"Registro actualizado: {instance}.", entidad=instance.__class__.__name__, entidad_id=instance.pk, valores_anteriores=anterior, valores_nuevos=self.snapshot_instance(instance))

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
    queryset = Cliente.objects.all().order_by('razon_social')
    serializer_class = ClienteSerializer
    permission_classes = [ClientePermission]
    module_name = 'Clientes y Contratos'


class ContratoViewSet(AuditedModelViewSet):
    queryset = Contrato.objects.select_related('cliente').all()
    serializer_class = ContratoSerializer
    permission_classes = [ContratoPermission]
    module_name = 'Clientes y Contratos'


class CategoriaServicioViewSet(AuditedModelViewSet):
    queryset = CategoriaServicio.objects.all()
    serializer_class = CategoriaServicioSerializer
    permission_classes = [CategoriaServicioPermission]
    module_name = 'Categorías de servicio'


class PresupuestoViewSet(AuditedModelViewSet):
    queryset = Presupuesto.objects.select_related('cliente', 'categoria_servicio').prefetch_related('items').all()
    serializer_class = PresupuestoSerializer
    permission_classes = [PresupuestoPermission]
    module_name = 'Presupuestos'

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


class ObraViewSet(AuditedModelViewSet):
    queryset = Obra.objects.select_related('presupuesto__cliente', 'tecnico_responsable', 'clasificacion_servicio').all()
    serializer_class = ObraSerializer
    permission_classes = [ObraPermission]
    module_name = 'Obras y Proyectos'

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.rol == 'TECNICO':
            return queryset.filter(tecnico_responsable=self.request.user)
        return queryset

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
        from django.db.models import Count, Q
        tecnicos = Usuario.objects.filter(rol='TECNICO', estado='activo').annotate(
            obras_activas=Count('obras_asignadas', filter=Q(obras_asignadas__estado_operativo__in=['en-proceso', 'suspendida']))
        ).values('id', 'first_name', 'last_name', 'obras_activas')
        return Response(list(tecnicos))

    @action(detail=True, methods=['get'], url_path='historial-estados')
    def historial_estados(self, request, pk=None):
        obra = self.get_object()
        return Response(list(ObraEstadoHistorial.objects.filter(obra=obra).values('id', 'estado_anterior', 'estado_nuevo', 'usuario_id', 'fecha', 'observacion')))

    @action(detail=True, methods=['post'], url_path='transicionar')
    def transicionar(self, request, pk=None):
        obra = transicionar_obra(self.get_object(), request.data.get('estado_operativo'), request.user, request.data.get('motivo', ''))
        return Response(self.get_serializer(obra).data)

    @action(detail=True, methods=['post'])
    def reabrir(self, request, pk=None):
        obra = reabrir_obra(self.get_object(), request.user, request.data.get('motivo', ''))
        return Response(self.get_serializer(obra).data)

    @action(detail=True, methods=['post'], url_path='cerrar-comercial')
    def cerrar_comercial(self, request, pk=None):
        obra = cerrar_obra_comercial(self.get_object(), request.user)
        return Response(self.get_serializer(obra).data)


class CostoMaterialViewSet(AuditedModelViewSet):
    queryset = CostoMaterial.objects.select_related('obra').all()
    serializer_class = CostoMaterialSerializer
    permission_classes = [CostoPermission]
    module_name = 'Costos de obra'


class FacturaViewSet(AuditedModelViewSet):
    queryset = Factura.objects.select_related('obra__presupuesto__cliente').all()
    serializer_class = FacturaSerializer
    permission_classes = [FacturaPermission]
    module_name = 'Facturación y Cobranza'

    @action(detail=True, methods=['post'], url_path='notas-credito')
    def notas_credito(self, request, pk=None):
        factura = self.get_object()
        serializer = NotaCreditoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        nota = registrar_nota_credito(factura, **serializer.validated_data, usuario=request.user)
        return Response({'id': nota.pk, 'factura': factura.pk, 'numero': nota.numero, 'monto': nota.monto, 'motivo': nota.motivo, 'fecha': nota.fecha})


class PagoViewSet(AuditedModelViewSet):
    queryset = Pago.objects.select_related('factura').all()
    serializer_class = PagoSerializer
    permission_classes = [PagoPermission]
    module_name = 'Facturación y Cobranza'
    http_method_names = ['get', 'post', 'head', 'options']

    def perform_create(self, serializer):
        factura = serializer.validated_data['factura']
        datos = {key: value for key, value in serializer.validated_data.items() if key != 'factura'}
        pago = registrar_pago(factura, datos, self.request.user)
        serializer.instance = pago

    @action(detail=True, methods=['post'], url_path='reversas')
    def reversas(self, request, pk=None):
        pago = self.get_object()
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
        desde = self.request.query_params.get('desde')
        hasta = self.request.query_params.get('hasta')
        busqueda = self.request.query_params.get('q')
        if modulo:
            queryset = queryset.filter(modulo=modulo)
        if resultado in {'exito', 'error', 'incompleto'}:
            queryset = queryset.filter(resultado=resultado)
        if desde:
            queryset = queryset.filter(fecha__date__gte=desde)
        if hasta:
            queryset = queryset.filter(fecha__date__lte=hasta)
        if busqueda:
            queryset = queryset.filter(Q(accion__icontains=busqueda) | Q(detalle__icontains=busqueda) | Q(entidad__icontains=busqueda))
        return queryset


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
        data = construir_resumen_dashboard(**filtros.validated_data)
        cache.set(clave, data, timeout=15)
        return Response(data)
