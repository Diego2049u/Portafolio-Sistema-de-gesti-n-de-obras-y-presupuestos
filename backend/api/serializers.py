import uuid

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from .models import (
    AuditoriaLog, CategoriaServicio, Cliente, Contrato, CostoMaterial,
    Factura, ItemPresupuesto, NotaCredito, Obra, Pago, Presupuesto, Usuario,
)
from .services import actualizar_totales_presupuesto, guardar_version_presupuesto


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

    class Meta:
        model = ItemPresupuesto
        fields = ['id', 'descripcion', 'cantidad', 'unidad', 'precio_unitario', 'subtotal']
        read_only_fields = ['id', 'subtotal']

    def validate_cantidad(self, value):
        if value <= 0:
            raise serializers.ValidationError('La cantidad debe ser mayor que cero.')
        return value

    def validate_precio_unitario(self, value):
        if value < 0:
            raise serializers.ValidationError('El precio unitario no puede ser negativo.')
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

    @transaction.atomic
    def create(self, validated_data):
        items = validated_data.pop('items', [])
        cliente = validated_data.get('cliente')
        contrato = validated_data.get('contrato')
        if cliente and not cliente.habilitar_emision:
            raise serializers.ValidationError({'cliente': 'El cliente tiene deshabilitada la emisión de presupuestos y documentos de cobro.'})
        if contrato and contrato.cliente_id != cliente.pk:
            raise serializers.ValidationError({'contrato': 'El contrato debe pertenecer al mismo cliente del presupuesto.'})
        validated_data['numero_presupuesto'] = f'TMP-{uuid.uuid4().hex}'
        presupuesto = Presupuesto.objects.create(**validated_data)
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
        items = validated_data.pop('items', None)
        if instance.estado != 'borrador':
            raise serializers.ValidationError({'estado': 'Solo se pueden editar presupuestos en borrador.'})
        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
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
        if request and getattr(request.user, 'rol', None) != 'GERENCIA':
            fields['requiere_aprobacion_gerencia'].read_only = True
        return fields


class ObraSerializer(serializers.ModelSerializer):
    tecnico_nombre = serializers.CharField(source='tecnico_responsable.get_full_name', read_only=True)
    cliente_nombre = serializers.CharField(source='presupuesto.cliente.razon_social', read_only=True)
    categoria_servicio_nombre = serializers.CharField(source='clasificacion_servicio.nombre', read_only=True)
    estado_operativo = serializers.CharField(read_only=True)
    estado_comercial = serializers.CharField(read_only=True)
    fecha_termino = serializers.DateField(read_only=True)
    fecha_cierre_comercial = serializers.DateTimeField(read_only=True)
    deleted_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Obra
        fields = '__all__'

    @transaction.atomic
    def create(self, validated_data):
        validated_data['codigo_obra'] = f'TMP-{uuid.uuid4().hex}'
        obra = super().create(validated_data)
        obra.codigo_obra = f'OBR-{timezone.localdate().year}-{obra.pk:06d}'
        obra.save(update_fields=['codigo_obra', 'updated_at'])
        return obra

    def update(self, instance, validated_data):
        if instance.estado_operativo in {'finalizada', 'cancelada'} or instance.estado_comercial == 'cerrada':
            campos_editables = {'observaciones_tecnicas', 'updated_by'}
            if set(validated_data) - campos_editables:
                raise serializers.ValidationError({'estado': 'La obra está finalizada o cerrada; no se permiten cambios operativos ni financieros.'})
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
            for name in ('presupuesto', 'estado_comercial', 'fecha_cierre_comercial'):
                fields.pop(name, None)
        if self.instance:
            fields['codigo_obra'].read_only = True
            if 'presupuesto' in fields:
                fields['presupuesto'].read_only = True
        return fields

    def validate(self, attrs):
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


class CostoMaterialSerializer(serializers.ModelSerializer):
    obra_codigo = serializers.CharField(source='obra.codigo_obra', read_only=True)
    fecha = serializers.DateField(read_only=True)

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

    def validate(self, attrs):
        obra = attrs.get('obra', getattr(self.instance, 'obra', None))
        if obra and (obra.estado_operativo in {'finalizada', 'cancelada'} or obra.estado_comercial == 'cerrada'):
            raise serializers.ValidationError({'obra': 'No se pueden registrar ni modificar costos de una obra finalizada, cancelada o cerrada comercialmente.'})
        return attrs


class FacturaSerializer(serializers.ModelSerializer):
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
            for name in ('obra', 'monto_neto', 'monto_total'):
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
        if neto is not None and neto < 0:
            raise serializers.ValidationError({'monto_neto': 'El monto neto no puede ser negativo.'})
        if total is not None and (total <= 0 or (neto is not None and total < neto)):
            raise serializers.ValidationError({'monto_total': 'El total debe ser positivo y no menor que el monto neto.'})
        if obra:
            cliente = obra.presupuesto.cliente
            if not cliente.habilitar_emision:
                raise serializers.ValidationError({'obra': 'El cliente tiene deshabilitada la emisión de facturas.'})
            from django.db.models import Sum
            facturas_obra = Factura.objects.filter(obra=obra)
            if self.instance:
                facturas_obra = facturas_obra.exclude(pk=self.instance.pk)
            facturado_bruto = facturas_obra.aggregate(total=Sum('monto_total'))['total'] or 0
            notas_credito = NotaCredito.objects.filter(factura__obra=obra).aggregate(total=Sum('monto'))['total'] or 0
            ya_facturado = facturado_bruto - notas_credito
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
            validated_data['numero_factura'] = f'TMP-{uuid.uuid4().hex}'
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


class ReversaPagoSerializer(serializers.Serializer):
    monto = serializers.DecimalField(max_digits=12, decimal_places=0, min_value=1)
    motivo = serializers.CharField()


class AuditoriaLogSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.CharField(source='usuario.get_full_name', read_only=True, allow_null=True)

    class Meta:
        model = AuditoriaLog
        fields = ['id', 'usuario', 'usuario_nombre', 'modulo', 'accion', 'resultado', 'entidad', 'entidad_id', 'detalle', 'metadata', 'ip_address', 'user_agent', 'valores_anteriores', 'valores_nuevos', 'fecha']
        read_only_fields = fields
