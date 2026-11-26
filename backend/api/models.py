from django.contrib.auth.models import AbstractUser, UserManager
from django.conf import settings
from django.db import models, transaction
from django.utils import timezone


class SoftDeleteQuerySet(models.QuerySet):
    @transaction.atomic
    def delete(self):
        active = list(self.filter(deleted_at__isnull=True))
        count = len(active)
        for instance in active:
            instance.soft_delete()
        return count, {self.model._meta.label: count}

    def hard_delete(self):
        return super().delete()


class ActiveUserManager(UserManager.from_queryset(SoftDeleteQuerySet)):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('rol', 'ADMIN_GENERAL')
        extra_fields.setdefault('estado', 'activo')
        extra_fields.setdefault('is_active', True)
        return super().create_superuser(username, email, password, **extra_fields)


class AllUserManager(UserManager.from_queryset(SoftDeleteQuerySet)):
    pass


class SoftDeleteManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class AllObjectsManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    pass


class SoftDeleteModel(models.Model):
    deleted_at = models.DateTimeField(null=True, blank=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, editable=False, on_delete=models.SET_NULL, related_name='%(app_label)s_%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, editable=False, on_delete=models.SET_NULL, related_name='%(app_label)s_%(class)s_updated')
    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True
        base_manager_name = 'all_objects'

    @property
    def is_deleted(self):
        return self.deleted_at is not None

    def soft_delete(self):
        if not self.is_deleted:
            self.deleted_at = timezone.now()
            fields = ['deleted_at', 'updated_at']
            if hasattr(self, 'updated_by_id'):
                fields.append('updated_by')
            self.save(update_fields=fields)

    def delete(self, using=None, keep_parents=False):
        self.soft_delete()
        return 1, {self._meta.label: 1}


class Usuario(AbstractUser):
    ROLES = (
        ('ADMIN_GENERAL', 'Administrador general'),
        ('GERENCIA', 'Gerencia'),
        ('FINANZAS', 'Finanzas'),
        ('SUPERVISOR', 'Supervisor de Obras'),
        ('TECNICO', 'Técnico'),
    )
    ESTADOS = (
        ('pendiente', 'Pendiente de activación'),
        ('activo', 'Activo'),
        ('bloqueado', 'Bloqueado'),
    )
    rut_usuario = models.CharField(max_length=15, unique=True, null=True, blank=True)
    email = models.EmailField(unique=True)
    cargo = models.CharField(max_length=100, null=True, blank=True)
    rol = models.CharField(max_length=20, choices=ROLES, default='TECNICO')
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    deleted_at = models.DateTimeField(null=True, blank=True, editable=False)

    objects = ActiveUserManager()
    all_objects = AllUserManager()

    class Meta:
        base_manager_name = 'all_objects'

    def soft_delete(self):
        if self.deleted_at is None:
            self.deleted_at = timezone.now()
            self.estado = 'bloqueado'
            self.is_active = False
            self.save(update_fields=['deleted_at', 'estado', 'is_active'])

    def delete(self, using=None, keep_parents=False):
        self.soft_delete()
        return 1, {self._meta.label: 1}

    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"


class Cliente(SoftDeleteModel):
    codigo_cliente = models.CharField(max_length=20, unique=True)
    rut_cliente = models.CharField(max_length=15, unique=True)
    razon_social = models.CharField(max_length=150)
    giro_comercial = models.CharField(max_length=150)
    direccion = models.CharField(max_length=200, blank=True, null=True)
    contacto_principal = models.CharField(max_length=100)
    cargo_contacto = models.CharField(max_length=100, blank=True)
    correo_contacto = models.EmailField()
    telefono_contacto = models.CharField(max_length=30)
    sector = models.CharField(max_length=50, default='general')
    estado = models.CharField(max_length=20, default='activo')
    habilitar_emision = models.BooleanField(default=True)

    def soft_delete(self):
        if self.contratos.exists() or self.presupuestos.exists():
            from django.core.exceptions import ValidationError
            raise ValidationError('No se puede desactivar un cliente con contratos o presupuestos asociados.')
        super().soft_delete()

    def __str__(self):
        return f"{self.codigo_cliente} - {self.razon_social}"


class Contrato(SoftDeleteModel):
    ESTADOS = (
        ('vigente', 'Vigente'),
        ('finalizado', 'Finalizado'),
        ('cancelado', 'Cancelado'),
    )
    numero_contrato = models.CharField(max_length=30, unique=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='contratos')
    nombre = models.CharField(max_length=150)
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_termino = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='vigente')
    observaciones = models.TextField(blank=True)

    def soft_delete(self):
        if self.presupuestos.exists():
            from django.core.exceptions import ValidationError
            raise ValidationError('No se puede desactivar un contrato asociado a presupuestos.')
        super().soft_delete()

    def __str__(self):
        return f"{self.numero_contrato} - {self.nombre}"


class CategoriaServicio(SoftDeleteModel):
    nombre = models.CharField(max_length=80, unique=True)
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['orden', 'nombre']
        verbose_name = 'categoría de servicio'
        verbose_name_plural = 'categorías de servicio'

    def __str__(self):
        return self.nombre

    def soft_delete(self):
        if self.presupuestos.exists() or self.obras.exists():
            from django.core.exceptions import ValidationError
            raise ValidationError('No se puede desactivar una categoría asociada a presupuestos u obras.')
        super().soft_delete()


class Presupuesto(SoftDeleteModel):
    ESTADOS = (
        ('borrador', 'Borrador'),
        ('pendiente_gerencia', 'Pendiente de aprobación interna'),
        ('enviado', 'Enviado al cliente'),
        ('aprobado', 'Aprobado por el cliente'),
        ('rechazado', 'Rechazado por el cliente'),
    )
    ESTADOS_GERENCIA = (
        ('no_requerida', 'No requerida'),
        ('pendiente', 'Pendiente'),
        ('aprobada', 'Aprobada'),
        ('rechazada', 'Rechazada'),
    )
    numero_presupuesto = models.CharField(max_length=30, unique=True, blank=True, default='')
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='presupuestos')
    contrato = models.ForeignKey(Contrato, on_delete=models.PROTECT, null=True, blank=True, related_name='presupuestos')
    categoria_servicio = models.ForeignKey(CategoriaServicio, on_delete=models.PROTECT, related_name='presupuestos')
    contacto = models.CharField(max_length=100)
    fecha_emision = models.DateField(auto_now_add=True)
    fecha_vencimiento = models.DateField(null=True, blank=True)
    monto_neto = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    iva = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    monto_total = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    contingencia_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    margen_objetivo = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    costo_base = models.DecimalField(max_digits=12, decimal_places=0, null=True, blank=True)
    reserva_imprevistos = models.DecimalField(max_digits=12, decimal_places=0, null=True, blank=True)
    ganancia_prevista = models.DecimalField(max_digits=12, decimal_places=0, null=True, blank=True)
    estado = models.CharField(max_length=24, choices=ESTADOS, default='borrador')
    requiere_aprobacion_gerencia = models.BooleanField(default=False)
    aprobacion_gerencia = models.CharField(max_length=20, choices=ESTADOS_GERENCIA, default='no_requerida')
    fecha_decision_cliente = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['estado', 'fecha_emision'], name='pres_estado_emision_idx'),
            models.Index(fields=['estado', 'fecha_decision_cliente'], name='pres_estado_decision_idx'),
        ]

    def __str__(self):
        return f"{self.numero_presupuesto} - {self.cliente.razon_social}"


class ItemPresupuesto(SoftDeleteModel):
    presupuesto = models.ForeignKey(Presupuesto, on_delete=models.PROTECT, related_name='items')
    descripcion = models.CharField(max_length=255)
    cantidad = models.PositiveIntegerField(default=1)
    unidad = models.CharField(max_length=10, default='un')
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=0)
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=0, null=True, blank=True)

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario


class VersionPresupuesto(models.Model):
    presupuesto = models.ForeignKey(Presupuesto, on_delete=models.PROTECT, related_name='historial_versiones')
    numero_version = models.PositiveIntegerField()
    snapshot = models.JSONField()
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-numero_version']
        constraints = [models.UniqueConstraint(fields=['presupuesto', 'numero_version'], name='presupuesto_version_unica')]

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValueError('Las versiones de presupuesto son inmutables.')
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError('El historial de versiones no se puede eliminar.')


class Obra(SoftDeleteModel):
    ESTADOS = (
        ('en-proceso', 'En proceso'),
        ('finalizada', 'Finalizada'),
        ('suspendida', 'Suspendida'),
        ('cancelada', 'Cancelada'),
    )
    ESTADOS_COMERCIALES = (
        ('en_curso', 'En curso'),
        ('pendiente_facturacion', 'Pendiente de facturación'),
        ('pendiente_cobro', 'Pendiente de cobro'),
        ('cerrada', 'Cerrada comercialmente'),
    )
    codigo_obra = models.CharField(max_length=30, unique=True, blank=True, default='')
    nombre_obra = models.CharField(max_length=150)
    presupuesto = models.OneToOneField(Presupuesto, on_delete=models.PROTECT, related_name='obra')
    tecnico_responsable = models.ForeignKey(Usuario, on_delete=models.PROTECT, null=True, blank=True, related_name='obras_asignadas')
    clasificacion_servicio = models.ForeignKey(CategoriaServicio, on_delete=models.PROTECT, related_name='obras')
    avance_porcentaje = models.PositiveSmallIntegerField(default=0)
    estado_operativo = models.CharField(max_length=20, choices=ESTADOS, default='en-proceso')
    estado_comercial = models.CharField(max_length=30, choices=ESTADOS_COMERCIALES, default='en_curso')
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_termino = models.DateField(null=True, blank=True)
    fecha_cierre_comercial = models.DateTimeField(null=True, blank=True)
    observaciones_tecnicas = models.TextField(blank=True, null=True)
    inicio_programado = models.DateTimeField(null=True, blank=True)
    fin_estimado = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['estado_operativo', 'tecnico_responsable'], name='obra_estado_tecnico_idx'),
            models.Index(fields=['fecha_termino', 'clasificacion_servicio'], name='obra_termino_servicio_idx'),
        ]

    def __str__(self):
        return f"{self.codigo_obra} - {self.nombre_obra}"


class Material(models.Model):
    nombre = models.CharField(max_length=120, unique=True)
    unidad = models.CharField(max_length=20)
    servicios = models.JSONField(default=list, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['nombre', 'pk']

    def __str__(self):
        return self.nombre


class ObraMaterial(models.Model):
    obra = models.ForeignKey(Obra, on_delete=models.PROTECT, related_name='materiales')
    material = models.ForeignKey(Material, on_delete=models.PROTECT)
    cantidad_planificada = models.DecimalField(max_digits=12, decimal_places=3)

    class Meta:
        ordering = ['pk']
        constraints = [
            models.UniqueConstraint(fields=['obra', 'material'], name='obra_material_unico'),
            models.CheckConstraint(check=models.Q(cantidad_planificada__gt=0), name='obra_material_cantidad_positiva'),
        ]


    def saldo_registrado(self):
        movimientos = list(self.movimientos.all())
        if not movimientos:
            return None
        entradas_netas = sum(
            movimiento.cantidad if movimiento.tipo == MovimientoMaterial.Tipo.ENTRADA else -movimiento.cantidad
            for movimiento in movimientos
        )
        return entradas_netas - sum(merma.cantidad for merma in self.mermas.all())


class MermaMaterial(models.Model):
    asignacion = models.ForeignKey(ObraMaterial, on_delete=models.PROTECT, related_name='mermas')
    cantidad = models.DecimalField(max_digits=12, decimal_places=3)
    motivo = models.CharField(max_length=255)
    fecha = models.DateField(auto_now_add=True, db_index=True)
    registrado_por = models.ForeignKey(Usuario, on_delete=models.PROTECT)

    class Meta:
        ordering = ['-fecha', '-pk']
        constraints = [
            models.CheckConstraint(check=models.Q(cantidad__gt=0), name='merma_material_cantidad_positiva'),
        ]


class MovimientoMaterial(models.Model):
    class Tipo(models.TextChoices):
        ENTRADA = 'entrada', 'Entrada'
        CONSUMO = 'consumo', 'Consumo'

    asignacion = models.ForeignKey(ObraMaterial, on_delete=models.PROTECT, related_name='movimientos')
    tipo = models.CharField(max_length=7, choices=Tipo.choices)
    cantidad = models.DecimalField(max_digits=12, decimal_places=3)
    motivo = models.CharField(max_length=255)
    referencia = models.CharField(max_length=100, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)
    registrado_por = models.ForeignKey(Usuario, on_delete=models.PROTECT)

    class Meta:
        ordering = ['-fecha', '-pk']
        constraints = [
            models.CheckConstraint(condition=models.Q(cantidad__gt=0), name='mov_material_cantidad_positiva'),
            models.CheckConstraint(condition=models.Q(tipo__in=['entrada', 'consumo']), name='mov_material_tipo_valido'),
            models.UniqueConstraint(
                models.functions.Lower('referencia'), 'asignacion',
                condition=models.Q(tipo='entrada') & ~models.Q(referencia=''),
                name='referencia_unica_por_asignacion',
            ),
        ]


class Proveedor(SoftDeleteModel):
    rut = models.CharField(max_length=15, unique=True)
    razon_social = models.CharField(max_length=150)
    correo = models.EmailField(blank=True)
    telefono = models.CharField(max_length=30, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['razon_social', 'pk']

    def __str__(self):
        return self.razon_social


class CostoMaterial(SoftDeleteModel):
    CATEGORIAS = (
        ('MATERIALES', 'Materiales'),
        ('MANO_DE_OBRA', 'Mano de obra'),
        ('SUBCONTRATO', 'Subcontrato'),
        ('EQUIPAMIENTO', 'Equipamiento'),
        ('VARIOS', 'Varios'),
    )
    obra = models.ForeignKey(Obra, on_delete=models.PROTECT, related_name='costos')
    categoria = models.CharField(max_length=30, choices=CATEGORIAS)
    monto = models.DecimalField(max_digits=12, decimal_places=0)
    descripcion = models.TextField()
    comprobante = models.URLField(blank=True, null=True)
    fecha = models.DateField(auto_now_add=True)
    cantidad_real = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    unidad_real = models.CharField(max_length=20, blank=True)
    costo_unitario_real = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    despacho = models.ForeignKey(MovimientoMaterial, null=True, blank=True, on_delete=models.PROTECT)
    proveedor = models.ForeignKey(Proveedor, null=True, blank=True, on_delete=models.PROTECT)

    class Meta:
        indexes = [models.Index(fields=['fecha', 'obra'], name='costo_fecha_obra_idx')]
        constraints = [
            models.UniqueConstraint(
                fields=['despacho'], condition=models.Q(deleted_at__isnull=True),
                name='un_costo_activo_por_despacho',
            ),
        ]

    def soft_delete(self):
        if self.obra.estado_operativo in {'finalizada', 'cancelada'} or self.obra.estado_comercial == 'cerrada':
            from django.core.exceptions import ValidationError
            raise ValidationError('No se pueden modificar costos de una obra finalizada, cancelada o cerrada comercialmente.')
        super().soft_delete()


class GastoGeneral(SoftDeleteModel):
    fecha = models.DateField(db_index=True)
    descripcion = models.CharField(max_length=255)
    monto = models.DecimalField(max_digits=12, decimal_places=0)

    class Meta:
        ordering = ['-fecha', '-pk']
        constraints = [
            models.CheckConstraint(condition=models.Q(monto__gt=0), name='gasto_general_monto_positivo'),
        ]

    def __str__(self):
        return self.descripcion


class Factura(SoftDeleteModel):
    ESTADOS_PAGO = (
        ('PENDIENTE', 'Pendiente de cobro'),
        ('PARCIAL', 'Pago parcial'),
        ('PAGADO', 'Pagado'),
        ('SALDADO', 'Saldo cubierto con nota de crédito'),
    )
    numero_factura = models.CharField(max_length=30, unique=True, blank=True, default='')
    obra = models.ForeignKey(Obra, on_delete=models.PROTECT, related_name='facturas')
    fecha_emision = models.DateField(auto_now_add=True)
    fecha_vencimiento = models.DateField()
    monto_neto = models.DecimalField(max_digits=12, decimal_places=0)
    monto_total = models.DecimalField(max_digits=12, decimal_places=0)
    saldo_pendiente = models.DecimalField(max_digits=12, decimal_places=0)
    estado_pago = models.CharField(max_length=20, choices=ESTADOS_PAGO, default='PENDIENTE')

    class Meta:
        indexes = [models.Index(fields=['fecha_emision', 'obra'], name='factura_fecha_obra_idx')]

    def __str__(self):
        return f"{self.numero_factura} ({self.estado_pago})"


class Pago(SoftDeleteModel):
    factura = models.ForeignKey(Factura, on_delete=models.PROTECT, related_name='pagos')
    monto = models.DecimalField(max_digits=12, decimal_places=0)
    fecha_pago = models.DateField()
    metodo_pago = models.CharField(max_length=50)
    comprobante = models.CharField(max_length=100, blank=True)
    folio_recibo = models.CharField(max_length=30, blank=True)


class AuditoriaLogQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValueError('Los eventos de auditoría son inmutables.')

    def delete(self):
        raise ValueError('Los eventos de auditoría no se pueden eliminar.')


class AuditoriaLog(models.Model):
    RESULTADOS = (
        ('exito', 'Correcto'),
        ('error', 'Error'),
        ('incompleto', 'Datos incompletos'),
    )
    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True)
    modulo = models.CharField(max_length=80)
    accion = models.CharField(max_length=100)
    resultado = models.CharField(max_length=20, choices=RESULTADOS)
    entidad = models.CharField(max_length=80, blank=True)
    entidad_id = models.CharField(max_length=64, blank=True)
    detalle = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)
    valores_anteriores = models.JSONField(default=dict, blank=True)
    valores_nuevos = models.JSONField(default=dict, blank=True)
    fecha = models.DateTimeField(auto_now_add=True, db_index=True)
    objects = models.Manager.from_queryset(AuditoriaLogQuerySet)()

    class Meta:
        ordering = ['-fecha', '-id']

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValueError('Los eventos de auditoría son inmutables.')
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError('Los eventos de auditoría no se pueden eliminar.')


class ObraEstadoHistorial(models.Model):
    obra = models.ForeignKey(Obra, on_delete=models.PROTECT, related_name='historial_estados')
    estado_anterior = models.CharField(max_length=20, blank=True)
    estado_nuevo = models.CharField(max_length=20, choices=Obra.ESTADOS)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    usuario_nombre_finalizacion = models.CharField(max_length=301, blank=True)
    usuario_rol_finalizacion = models.CharField(max_length=20, choices=Usuario.ROLES, blank=True)
    fecha = models.DateTimeField(auto_now_add=True, db_index=True)
    observacion = models.TextField(blank=True)

    class Meta:
        ordering = ['fecha', 'id']

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValueError('El historial de estados es inmutable.')
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError('El historial de estados no se puede eliminar.')


class NotaCredito(models.Model):
    factura = models.ForeignKey(Factura, on_delete=models.PROTECT, related_name='notas_credito')
    numero = models.CharField(max_length=40, unique=True)
    monto = models.DecimalField(max_digits=12, decimal_places=0)
    motivo = models.TextField()
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.CheckConstraint(check=models.Q(monto__gt=0), name='nota_credito_monto_positivo')]

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValueError('Las notas de crédito son inmutables.')
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError('Las notas de crédito no se pueden eliminar.')


class ReversaPago(models.Model):
    pago = models.ForeignKey(Pago, on_delete=models.PROTECT, related_name='reversiones')
    monto = models.DecimalField(max_digits=12, decimal_places=0)
    motivo = models.TextField()
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.CheckConstraint(check=models.Q(monto__gt=0), name='reversa_pago_monto_positivo')]

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValueError('Las reversiones de pago son inmutables.')
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError('Las reversiones de pago no se pueden eliminar.')
