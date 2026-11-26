import uuid
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from .models import (
    AuditoriaLog, CategoriaServicio, Cliente, Contrato, CostoMaterial,
    Factura, GastoGeneral, ItemPresupuesto, Material, MermaMaterial, MovimientoMaterial, NotaCredito, Obra,
    ObraMaterial, Pago, Presupuesto, Proveedor, Usuario,
)
from .services import actualizar_totales_presupuesto, guardar_version_presupuesto, iva_estandar, total_facturado_neto
from .disponibilidad import CHILE, validar_asignacion


class UsuarioSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=False, trim_whitespace=False)

    class Meta:
        model = Usuario
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'rut_usuario', 'cargo', 'rol', 'estado', 'password']
        read_only_fields = ['id']
        extra_kwargs = {'username': {'required': False}}

    def validate(self, attrs):
        if not self.instance and not attrs.get('username'):
            attrs['username'] = attrs.get('email', '').strip().lower()
        password = attrs.get('password')
        if password:
            from django.contrib.auth.password_validation import validate_password
            validate_password(password, user=self.instance)
        estado = attrs.get('estado', getattr(self.instance, 'estado', 'pendiente'))
        if estado == 'activo' and not password and (self.instance is None or not self.instance.has_usable_password()):
            raise serializers.ValidationError({'password': 'Se debe definir una contraseña antes de activar la cuenta.'})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = Usuario(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.is_active = user.estado == 'activo' and user.has_usable_password()
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        instance = super().update(instance, validated_data)
        if password:
            instance.set_password(password)
        instance.is_active = instance.estado == 'activo' and instance.deleted_at is None
        fields = ['is_active']
        if password:
            fields.append('password')
        instance.save(update_fields=fields)
        return instance

    def get_fields(self):
        fields = super().get_fields()
        if self.instance:
            fields['password'].read_only = True
        return fields


class EstablecerPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, min_length=1, trim_whitespace=False)

    def validate_password(self, value):
        from django.contrib.auth.password_validation import validate_password
        validate_password(value, user=self.context.get('user'))
        return value


class ClienteSerializer(serializers.ModelSerializer):
    deleted_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Cliente
        fields = '__all__'
        read_only_fields = ['deleted_at']
        extra_kwargs = {'codigo_cliente': {'required': False}}

    def create(self, validated_data):
        validated_data.setdefault('codigo_cliente', f"CLI-{uuid.uuid4().hex[:10].upper()}")
        return super().create(validated_data)


class ContratoSerializer(serializers.ModelSerializer):
    cliente_nombre = serializers.CharField(source='cliente.razon_social', read_only=True)

    class Meta:
        model = Contrato
        fields = '__all__'
        read_only_fields = ['deleted_at']


class CategoriaServicioSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoriaServicio
        fields = ['id', 'nombre', 'orden', 'deleted_at']
        read_only_fields = ['deleted_at']


class ItemPresupuestoSerializer(serializers.ModelSerializer):
    subtotal = serializers.DecimalField(max_digits=14, decimal_places=0, read_only=True)
    precio_unitario = serializers.DecimalField(max_digits=12, decimal_places=0, min_value=0, required=False)
    costo_unitario = serializers.DecimalField(max_digits=12, decimal_places=0, min_value=0, required=False, allow_null=True)

    class Meta:
        model = ItemPresupuesto
        fields = ['id', 'descripcion', 'cantidad', 'unidad', 'precio_unitario', 'costo_unitario', 'subtotal']
        read_only_fields = ['id', 'subtotal']

    def validate_cantidad(self, value):
        if value <= 0:
            raise serializers.ValidationError('La cantidad debe ser mayor que cero.')
        return value

class PresupuestoSerializer(serializers.ModelSerializer):
    items = ItemPresupuestoSerializer(many=True, required=False)
    cliente_nombre = serializers.CharField(source='cliente.razon_social', read_only=True)
    categoria_servicio_nombre = serializers.CharField(source='categoria_servicio.nombre', read_only=True)
    monto_neto = serializers.DecimalField(max_digits=12, decimal_places=0, read_only=True)
    iva = serializers.DecimalField(max_digits=12, decimal_places=0, read_only=True)
    monto_total = serializers.DecimalField(max_digits=12, decimal_places=0, read_only=True)
    estado = serializers.CharField(read_only=True)
    aprobacion_gerencia = serializers.CharField(read_only=True)
    fecha_emision = serializers.DateField(read_only=True)
    fecha_decision_cliente = serializers.DateTimeField(read_only=True)
    deleted_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Presupuesto
        fields = '__all__'
        read_only_fields = ['costo_base', 'reserva_imprevistos', 'ganancia_prevista']

    @staticmethod
    def preparar_partidas(presupuesto, items, *, ya_valorizado=False):
        margen = presupuesto.margen_objetivo
        contingencia = presupuesto.contingencia_porcentaje
        if ya_valorizado and margen is None and contingencia is None:
            raise serializers.ValidationError({'margen_objetivo': 'Conserve los porcentajes del presupuesto.'})
        if margen is not None or contingencia is not None:
            if margen is None or not 0 <= margen < 100:
                raise serializers.ValidationError({'margen_objetivo': 'Indique un margen desde 0 hasta 99,99%.'})
            if contingencia is None or not 0 <= contingencia <= 100:
                raise serializers.ValidationError({'contingencia_porcentaje': 'Indique una reserva desde 0 hasta 100%.'})
            if items is None:
                if ya_valorizado:
                    return
                raise serializers.ValidationError({'items': 'Ingrese las partidas con sus costos internos.'})
            if not items or any(item.get('costo_unitario') is None for item in items):
                raise serializers.ValidationError({'items': 'Ingrese el costo interno de cada partida.'})
            for item in items:
                item['precio_unitario'] = 0
        elif items is not None and any('precio_unitario' not in item or item.get('costo_unitario') is not None for item in items):
            raise serializers.ValidationError({'items': 'Ingrese el precio de venta o configure margen y contingencia para usar costos internos.'})

    @transaction.atomic
    def create(self, validated_data):
        items = validated_data.pop('items', [])
        cliente = validated_data.get('cliente')
        contrato = validated_data.get('contrato')
        if cliente and not cliente.habilitar_emision:
            raise serializers.ValidationError({'cliente': 'El cliente tiene deshabilitada la emisión de presupuestos y documentos de cobro.'})
        if contrato and contrato.cliente_id != cliente.pk:
            raise serializers.ValidationError({'contrato': 'El contrato debe pertenecer al mismo cliente del presupuesto.'})
        validated_data['numero_presupuesto'] = f'TMP-{uuid.uuid4().hex[:20]}'
        presupuesto = Presupuesto(**validated_data)
        self.preparar_partidas(presupuesto, items)
        presupuesto.save()
        presupuesto.numero_presupuesto = f'PRE-{timezone.localdate().year}-{presupuesto.pk:06d}'
        presupuesto.save(update_fields=['numero_presupuesto', 'updated_at'])
        usuario = getattr(self.context.get('request'), 'user', None)
        for item in items:
            ItemPresupuesto.objects.create(presupuesto=presupuesto, created_by=usuario, updated_by=usuario, **item)
        actualizar_totales_presupuesto(presupuesto)
        guardar_version_presupuesto(presupuesto, usuario)
        return presupuesto

    @transaction.atomic
    def update(self, instance, validated_data):
        instance = Presupuesto.objects.select_for_update().get(pk=instance.pk)
        items = validated_data.pop('items', None)
        ya_valorizado = instance.margen_objetivo is not None
        if instance.estado != 'borrador':
            raise serializers.ValidationError({'estado': 'Solo se pueden editar presupuestos en borrador.'})
        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        self.preparar_partidas(instance, items, ya_valorizado=ya_valorizado)
        if not instance.cliente.habilitar_emision:
            raise serializers.ValidationError({'cliente': 'El cliente tiene deshabilitada la emisión de presupuestos y documentos de cobro.'})
        if instance.contrato_id and instance.contrato.cliente_id != instance.cliente_id:
            raise serializers.ValidationError({'contrato': 'El contrato debe pertenecer al mismo cliente del presupuesto.'})
        instance.save()
        if items is not None:
            usuario = getattr(self.context.get('request'), 'user', None)
            for item in instance.items.all():
                item.updated_by = usuario
                item.soft_delete()
            for item_data in items:
                ItemPresupuesto.objects.create(presupuesto=instance, created_by=usuario, updated_by=usuario, **item_data)
        if items is not None or ya_valorizado:
            actualizar_totales_presupuesto(instance)
        usuario = getattr(self.context.get('request'), 'user', None)
        guardar_version_presupuesto(instance, usuario)
        return instance

    def validate(self, attrs):
        fecha_vencimiento = attrs.get('fecha_vencimiento')
        if fecha_vencimiento:
            fecha_emision = self.instance.fecha_emision if self.instance else timezone.localdate()
            if fecha_vencimiento <= fecha_emision:
                raise serializers.ValidationError({'fecha_vencimiento': 'Debe ser posterior a la fecha de emisión.'})
        contrato = attrs.get('contrato', getattr(self.instance, 'contrato', None))
        cliente = attrs.get('cliente', getattr(self.instance, 'cliente', None))
        if contrato and cliente and contrato.cliente_id != cliente.pk:
            raise serializers.ValidationError({'contrato': 'El contrato debe pertenecer al mismo cliente del presupuesto.'})
        return attrs

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get('request')
        fields['numero_presupuesto'].read_only = True
        if request and getattr(request.user, 'rol', None) != 'ADMIN_GENERAL':
            fields['requiere_aprobacion_gerencia'].read_only = True
        return fields


class MaterialSerializer(serializers.ModelSerializer):
    servicios = serializers.ListField(
        child=serializers.CharField(max_length=120), required=False, max_length=30,
    )

    class Meta:
        model = Material
        fields = ['id', 'nombre', 'unidad', 'servicios', 'activo']

    @transaction.atomic
    def update(self, instance, validated_data):
        instance = Material.objects.select_for_update().get(pk=instance.pk)
        if validated_data.get('unidad', instance.unidad) != instance.unidad and ObraMaterial.objects.filter(material=instance).exists():
            raise serializers.ValidationError({'unidad': 'La unidad ya se usa en una obra. Crea otro material para usar una unidad distinta.'})
        return super().update(instance, validated_data)


class ObraMaterialEntradaSerializer(serializers.Serializer):
    material = serializers.PrimaryKeyRelatedField(queryset=Material.objects.filter(activo=True))
    cantidad_planificada = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=Decimal('0.001'))


class MermaMaterialSerializer(serializers.ModelSerializer):
    cantidad = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=Decimal('0.001'))

    class Meta:
        model = MermaMaterial
        fields = ['id', 'cantidad', 'motivo', 'fecha']
        read_only_fields = ['id', 'fecha']


class MovimientoMaterialSerializer(serializers.ModelSerializer):
    cantidad = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=Decimal('0.001'))

    class Meta:
        model = MovimientoMaterial
        fields = ['id', 'tipo', 'cantidad', 'motivo', 'referencia', 'fecha', 'registrado_por']
        read_only_fields = ['fecha', 'registrado_por']


class ObraMaterialSerializer(serializers.ModelSerializer):
    material = MaterialSerializer(read_only=True)
    mermas = MermaMaterialSerializer(many=True, read_only=True)
    movimientos = MovimientoMaterialSerializer(many=True, read_only=True)
    saldo = serializers.SerializerMethodField()

    def get_saldo(self, instance):
        saldo = instance.saldo_registrado()
        return str(saldo) if saldo is not None else None

    class Meta:
        model = ObraMaterial
        fields = ['id', 'material', 'cantidad_planificada', 'mermas', 'movimientos', 'saldo']


class ObraSerializer(serializers.ModelSerializer):
    materiales = ObraMaterialEntradaSerializer(many=True, required=False, write_only=True, max_length=10)
    inicio_programado = serializers.DateTimeField(default_timezone=CHILE, required=False, allow_null=True)
    fin_estimado = serializers.DateTimeField(default_timezone=CHILE, required=False, allow_null=True)
    tecnico_nombre = serializers.CharField(source='tecnico_responsable.get_full_name', read_only=True)
    cliente_nombre = serializers.CharField(source='presupuesto.cliente.razon_social', read_only=True)
    cliente_id = serializers.IntegerField(source='presupuesto.cliente_id', read_only=True)
    numero_presupuesto = serializers.CharField(source='presupuesto.numero_presupuesto', read_only=True)
    categoria_servicio_nombre = serializers.CharField(source='clasificacion_servicio.nombre', read_only=True)
    estado_operativo = serializers.CharField(read_only=True)
    estado_comercial = serializers.CharField(read_only=True)
    puede_cerrar_comercial = serializers.BooleanField(read_only=True)
    fecha_termino = serializers.DateField(read_only=True)
    fecha_cierre_comercial = serializers.DateTimeField(read_only=True)
    deleted_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Obra
        fields = '__all__'

    @transaction.atomic
    def create(self, validated_data):
        materiales = validated_data.pop('materiales', [])
        ids = [item['material'].pk for item in materiales]
        activos = list(Material.objects.select_for_update().filter(pk__in=ids, activo=True).order_by('pk'))
        if len(activos) != len(ids):
            raise serializers.ValidationError({'materiales': 'Uno de los materiales seleccionados ya no está activo.'})
        validar_asignacion(validated_data.get('tecnico_responsable').pk if validated_data.get('tecnico_responsable') else None,
                           validated_data.get('inicio_programado'), validated_data.get('fin_estimado'))
        validated_data['fecha_inicio'] = validated_data['inicio_programado'].astimezone(CHILE).date()
        validated_data['codigo_obra'] = f'TMP-{uuid.uuid4().hex[:20]}'
        obra = super().create(validated_data)
        obra.codigo_obra = f'OBR-{timezone.localdate().year}-{obra.pk:06d}'
        obra.save(update_fields=['codigo_obra', 'updated_at'])
        ObraMaterial.objects.bulk_create([ObraMaterial(obra=obra, **item) for item in materiales])
        return obra

    @transaction.atomic
    def update(self, instance, validated_data):
        instance = Obra.objects.select_for_update().get(pk=instance.pk)
        if instance.estado_operativo in {'finalizada', 'cancelada'} or instance.estado_comercial == 'cerrada':
            campos_editables = {'observaciones_tecnicas', 'updated_by'}
            if set(validated_data) - campos_editables:
                raise serializers.ValidationError({'estado': 'La obra está finalizada o cerrada; no se permiten cambios operativos ni financieros.'})
        if {'tecnico_responsable', 'inicio_programado', 'fin_estimado'} & set(validated_data):
            tecnico = validated_data.get('tecnico_responsable', instance.tecnico_responsable)
            inicio = validated_data.get('inicio_programado', instance.inicio_programado)
            fin = validated_data.get('fin_estimado', instance.fin_estimado)
            if instance.estado_operativo == 'en-proceso':
                validar_asignacion(tecnico.pk if tecnico else None, inicio, fin, instance.pk)
            else:
                from .disponibilidad import validar_rango
                validar_rango(inicio, fin)
            validated_data['fecha_inicio'] = inicio.astimezone(CHILE).date()
        return super().update(instance, validated_data)

    def validate_avance_porcentaje(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError('El avance debe estar entre 0 y 100.')
        return value

    def get_fields(self):
        fields = super().get_fields()
        fields['codigo_obra'].read_only = True
        request = self.context.get('request')
        if request and getattr(request.user, 'rol', None) == 'TECNICO':
            for name in ('presupuesto', 'numero_presupuesto', 'estado_comercial', 'fecha_cierre_comercial'):
                fields.pop(name, None)
        if self.instance:
            fields['codigo_obra'].read_only = True
            if 'presupuesto' in fields:
                fields['presupuesto'].read_only = True
        return fields

    def validate(self, attrs):
        if 'materiales' in attrs:
            request = self.context.get('request')
            if request and request.user.rol not in {'ADMIN_GENERAL', 'SUPERVISOR'}:
                raise serializers.ValidationError({'materiales': 'Tu rol no puede asignar materiales.'})
            if self.instance is not None:
                raise serializers.ValidationError({'materiales': 'Asigna los materiales al crear la obra.'})
            ids = [item['material'].pk for item in attrs['materiales']]
            if len(ids) != len(set(ids)):
                raise serializers.ValidationError({'materiales': 'Selecciona cada material una sola vez.'})
        presupuesto = attrs.get('presupuesto', getattr(self.instance, 'presupuesto', None))
        tecnico = attrs.get('tecnico_responsable', getattr(self.instance, 'tecnico_responsable', None))
        categoria = attrs.get('clasificacion_servicio', getattr(self.instance, 'clasificacion_servicio', None))
        if self.instance is None and presupuesto and presupuesto.estado != 'aprobado':
            raise serializers.ValidationError({'presupuesto': 'La obra debe asociarse a un presupuesto aprobado por el cliente.'})
        if presupuesto and categoria and presupuesto.categoria_servicio_id != categoria.pk:
            raise serializers.ValidationError({'clasificacion_servicio': 'La clasificación debe coincidir con la del presupuesto aprobado.'})
        if tecnico and (tecnico.rol != 'TECNICO' or tecnico.estado != 'activo'):
            raise serializers.ValidationError({'tecnico_responsable': 'Seleccione un técnico activo.'})
        if categoria and not CategoriaServicio.objects.filter(pk=categoria.pk).exists():
            raise serializers.ValidationError({'clasificacion_servicio': 'La categoría no está activa.'})
        return attrs


class ProveedorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proveedor
        fields = ['id', 'rut', 'razon_social', 'correo', 'telefono', 'activo']

    def validate_rut(self, value):
        rut = value.replace('.', '').replace(' ', '').upper()
        cuerpo, separador, digito = rut.partition('-')
        if not separador or not cuerpo.isascii() or not cuerpo.isdigit() or len(cuerpo) > 8 or not cuerpo.lstrip('0'):
            raise serializers.ValidationError('Ingrese el RUT con su dígito verificador.')
        cuerpo = cuerpo.lstrip('0')
        resto = 11 - sum(int(numero) * (2 + indice % 6) for indice, numero in enumerate(reversed(cuerpo))) % 11
        esperado = '0' if resto == 11 else 'K' if resto == 10 else str(resto)
        if digito != esperado:
            raise serializers.ValidationError('El dígito verificador del RUT no coincide.')
        normalizado = f'{cuerpo}-{digito}'
        if Proveedor.all_objects.filter(rut=normalizado).exclude(pk=getattr(self.instance, 'pk', None)).exists():
            raise serializers.ValidationError('Ya existe un proveedor con ese RUT.')
        return normalizado


class CostoMaterialSerializer(serializers.ModelSerializer):
    monto = serializers.DecimalField(max_digits=12, decimal_places=0, required=False)
    obra_codigo = serializers.CharField(source='obra.codigo_obra', read_only=True)
    fecha = serializers.DateField(read_only=True)
    proveedor_nombre = serializers.CharField(source='proveedor.razon_social', read_only=True, default=None)

    class Meta:
        model = CostoMaterial
        fields = '__all__'
        read_only_fields = ['deleted_at']

    def get_fields(self):
        fields = super().get_fields()
        if self.instance:
            fields['obra'].read_only = True
        return fields

    def validate_monto(self, value):
        if value <= 0:
            raise serializers.ValidationError('El monto debe ser mayor que cero.')
        return value

    def validate_proveedor(self, proveedor):
        if proveedor and not proveedor.activo and proveedor.pk != getattr(self.instance, 'proveedor_id', None):
            raise serializers.ValidationError('Seleccione un proveedor activo.')
        return proveedor

    def validate(self, attrs):
        obra = attrs.get('obra', getattr(self.instance, 'obra', None))
        if obra and (obra.estado_operativo in {'finalizada', 'cancelada'} or obra.estado_comercial == 'cerrada'):
            raise serializers.ValidationError({'obra': 'No se pueden registrar ni modificar costos de una obra finalizada, cancelada o cerrada comercialmente.'})
        cantidad = attrs.get('cantidad_real', getattr(self.instance, 'cantidad_real', None))
        tarifa = attrs.get('costo_unitario_real', getattr(self.instance, 'costo_unitario_real', None))
        unidad = attrs.get('unidad_real', getattr(self.instance, 'unidad_real', ''))
        categoria = attrs.get('categoria', getattr(self.instance, 'categoria', None))
        despacho = attrs.get('despacho', getattr(self.instance, 'despacho', None))
        if despacho:
            if categoria != 'MATERIALES' or despacho.tipo != MovimientoMaterial.Tipo.ENTRADA or despacho.asignacion.obra_id != obra.pk:
                raise serializers.ValidationError({'despacho': 'Seleccione una entrada de materiales de esta obra.'})
            cantidad = attrs['cantidad_real'] = despacho.cantidad
            unidad = attrs['unidad_real'] = despacho.asignacion.material.unidad
        if cantidad is not None or tarifa is not None or unidad:
            if categoria not in {'MANO_DE_OBRA', 'MATERIALES'}:
                raise serializers.ValidationError({'categoria': 'El desglose corresponde a mano de obra o materiales.'})
            if cantidad is None or tarifa is None or cantidad <= 0 or tarifa <= 0 or not unidad:
                raise serializers.ValidationError({'cantidad_real': 'Indique cantidad, unidad y costo unitario positivos.'})
            if categoria == 'MANO_DE_OBRA' and unidad != 'h':
                raise serializers.ValidationError({'unidad_real': 'Registre las horas profesionales en h.'})
            monto = (cantidad * tarifa).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
            if not 0 < monto < 10**12:
                raise serializers.ValidationError({'monto': 'El costo calculado debe estar entre 1 y 999999999999 CLP.'})
            attrs['monto'] = monto
        elif self.instance is None and 'monto' not in attrs:
            raise serializers.ValidationError({'monto': 'Indique el monto del costo.'})
        return attrs


class GastoGeneralSerializer(serializers.ModelSerializer):
    monto = serializers.DecimalField(max_digits=12, decimal_places=0, min_value=Decimal('1'))

    class Meta:
        model = GastoGeneral
        fields = ['id', 'fecha', 'descripcion', 'monto']


class FacturaSerializer(serializers.ModelSerializer):
    aplica_iva = serializers.BooleanField(required=False, write_only=True)
    saldo_pendiente = serializers.DecimalField(max_digits=12, decimal_places=0, read_only=True)
    estado_pago = serializers.CharField(read_only=True)
    fecha_emision = serializers.DateField(read_only=True)
    obra_codigo = serializers.CharField(source='obra.codigo_obra', read_only=True)
    cliente_nombre = serializers.CharField(source='obra.presupuesto.cliente.razon_social', read_only=True)

    class Meta:
        model = Factura
        fields = '__all__'
        read_only_fields = ['deleted_at']

    def get_fields(self):
        fields = super().get_fields()
        fields['numero_factura'].read_only = True
        if self.instance:
            for name in ('obra', 'monto_neto', 'monto_total', 'aplica_iva'):
                fields[name].read_only = True
        return fields

    def validate(self, attrs):
        obra = attrs.get('obra')
        total = attrs.get('monto_total')
        neto = attrs.get('monto_neto')
        if obra and obra.estado_operativo != 'finalizada':
            raise serializers.ValidationError({'obra': 'Solo se puede facturar una obra finalizada.'})
        if obra and obra.estado_comercial == 'cerrada':
            raise serializers.ValidationError({'obra': 'No se puede emitir una nueva factura después del cierre comercial.'})
        if neto is not None and neto <= 0:
            raise serializers.ValidationError({'monto_neto': 'El monto neto debe ser mayor que cero.'})
        if neto is not None:
            con_iva = neto + iva_estandar(neto)
            aplica_iva = attrs.get('aplica_iva')
            permitidos = {con_iva} if aplica_iva is True else {neto} if aplica_iva is False else {neto, con_iva}
            if total not in permitidos:
                raise serializers.ValidationError({'monto_total': 'El total no coincide con el neto y el IVA aplicable.'})
        if obra:
            cliente = obra.presupuesto.cliente
            if not cliente.habilitar_emision:
                raise serializers.ValidationError({'obra': 'El cliente tiene deshabilitada la emisión de facturas.'})
            facturas_obra = Factura.objects.filter(obra=obra)
            if self.instance:
                facturas_obra = facturas_obra.exclude(pk=self.instance.pk)
            ya_facturado = total_facturado_neto(facturas_obra)
            monto_nuevo = total if total is not None else getattr(self.instance, 'monto_total', 0)
            if ya_facturado + monto_nuevo > obra.presupuesto.monto_total:
                raise serializers.ValidationError({'monto_total': 'La suma de facturas excedería el monto total aprobado del presupuesto.'})
        return attrs

    def create(self, validated_data):
        from django.db import transaction
        obra_id = validated_data['obra'].pk
        with transaction.atomic():
            obra = Obra.objects.select_for_update().get(pk=obra_id)
            validated_data['obra'] = obra
            # Revalidate under the work-row lock to prevent concurrent overbilling.
            self.validate(validated_data)
            validated_data.pop('aplica_iva', None)
            validated_data['numero_factura'] = f'TMP-{uuid.uuid4().hex[:20]}'
            return self._create_factura(validated_data)

    def _create_factura(self, validated_data):
        validated_data['saldo_pendiente'] = validated_data['monto_total']
        validated_data['estado_pago'] = 'PENDIENTE'
        factura = super().create(validated_data)
        factura.numero_factura = f'FAC-{timezone.localdate().year}-{factura.pk:06d}'
        factura.save(update_fields=['numero_factura', 'updated_at'])
        obra = factura.obra
        obra.estado_comercial = 'pendiente_cobro'
        obra.updated_by = getattr(self.context.get('request'), 'user', None)
        obra.save(update_fields=['estado_comercial', 'updated_by', 'updated_at'])
        return factura


class PagoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pago
        fields = '__all__'
        read_only_fields = ['deleted_at']

    def get_fields(self):
        fields = super().get_fields()
        if self.instance:
            for field in fields.values():
                field.read_only = True
        return fields

    def validate_monto(self, value):
        if value <= 0:
            raise serializers.ValidationError('El monto del pago debe ser mayor que cero.')
        return value


class NotaCreditoSerializer(serializers.Serializer):
    numero = serializers.CharField(max_length=40)
    monto = serializers.DecimalField(max_digits=12, decimal_places=0, min_value=1)
    motivo = serializers.CharField()

    def validate_numero(self, value):
        if NotaCredito.objects.filter(numero=value).exists():
            raise serializers.ValidationError('Ya existe una nota de crédito con ese número.')
        return value


class ReversaPagoSerializer(serializers.Serializer):
    monto = serializers.DecimalField(max_digits=12, decimal_places=0, min_value=1)
    motivo = serializers.CharField()


class AuditoriaLogSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.CharField(source='usuario.get_full_name', read_only=True, allow_null=True)

    class Meta:
        model = AuditoriaLog
        fields = ['id', 'usuario', 'usuario_nombre', 'modulo', 'accion', 'resultado', 'entidad', 'entidad_id', 'detalle', 'metadata', 'ip_address', 'user_agent', 'valores_anteriores', 'valores_nuevos', 'fecha']
        read_only_fields = fields
