from django.db import models
from django.contrib.auth.models import AbstractUser

class Usuario(AbstractUser):
    ROLES = (
        ('GERENCIA', 'Gerencia / Admin General'),
        ('FINANZAS', 'Finanzas & Facturación'),
        ('SUPERVISOR', 'Supervisor de Obras'),
        ('TECNICO', 'Técnico Faena'),
    )
    ESTADOS = (
        ('pendiente', 'Pendiente de Aprobación'),
        ('activo', 'Activo'),
        ('bloqueado', 'Bloqueado'),
    )
    rut_usuario = models.CharField(max_length=15, unique=True, null=True, blank=True)
    cargo = models.CharField(max_length=100, null=True, blank=True)
    rol = models.CharField(max_length=20, choices=ROLES, default='TECNICO')
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"


class Cliente(models.Model):
    codigo_cliente = models.CharField(max_length=20, unique=True)
    rut_cliente = models.CharField(max_length=15, unique=True)
    razon_social = models.CharField(max_length=150)
    giro_comercial = models.CharField(max_length=150)
    direccion = models.CharField(max_length=200, blank=True, null=True)
    contacto_principal = models.CharField(max_length=100)
    correo_contacto = models.EmailField()
    telefono_contacto = models.CharField(max_length=30)
    sector = models.CharField(max_length=50, default='general')
    estado = models.CharField(max_length=20, default='activo')
    habilitar_emision = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.codigo_cliente} - {self.razon_social}"


class Presupuesto(models.Model):
    ESTADOS = (
        ('borrador', 'Borrador'),
        ('enviado', 'Enviado'),
        ('aprobado', 'Aprobado'),
        ('rechazado', 'Rechazado'),
    )
    numero_presupuesto = models.CharField(max_length=30, unique=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='presupuestos')
    categoria_servicio = models.CharField(max_length=100)
    contacto = models.CharField(max_length=100)
    fecha_emision = models.DateField(auto_now_add=True)
    fecha_vencimiento = models.DateField(null=True, blank=True)
    monto_neto = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    iva = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    monto_total = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='borrador')

    def __str__(self):
        return f"{self.numero_presupuesto} - {self.cliente.razon_social}"


class ItemPresupuesto(models.Model):
    presupuesto = models.ForeignKey(Presupuesto, on_delete=models.CASCADE, related_name='items')
    descripcion = models.CharField(max_length=255)
    cantidad = models.IntegerField(default=1)
    unidad = models.CharField(max_length=10, default='un')
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=0)

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario


class Obra(models.Model):
    ESTADOS = (
        ('en-proceso', 'En Proceso'),
        ('finalizada', 'Finalizada'),
        ('suspendida', 'Suspendida'),
        ('cancelada', 'Cancelada'),
    )
    codigo_obra = models.CharField(max_length=30, unique=True)
    nombre_obra = models.CharField(max_length=150)
    presupuesto = models.OneToOneField(Presupuesto, on_delete=models.RESTRICT, related_name='obra')
    tecnico_responsable = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name='obras_asignadas')
    clasificacion_servicio = models.CharField(max_length=50)
    avance_porcentaje = models.IntegerField(default=0)
    estado_operativo = models.CharField(max_length=20, choices=ESTADOS, default='en-proceso')
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_termino = models.DateField(null=True, blank=True)
    observaciones_tecnicas = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.codigo_obra} - {self.nombre_obra}"


class CostoMaterial(models.Model):
    CATEGORIAS = (
        ('MATERIALES', 'Materiales'),
        ('MANO_DE_OBRA', 'Mano de Obra'),
        ('SUBCONTRATO', 'Subcontrato'),
        ('EQUIPAMIENTO', 'Equipamiento'),
        ('VARIOS', 'Varios'),
    )
    obra = models.ForeignKey(Obra, on_delete=models.CASCADE, related_name='costos')
    categoria = models.CharField(max_length=30, choices=CATEGORIAS)
    monto = models.DecimalField(max_digits=12, decimal_places=0)
    descripcion = models.TextField()
    comprobante = models.URLField(blank=True, null=True)
    fecha = models.DateField(auto_now_add=True)


class Factura(models.Model):
    ESTADOS_PAGO = (
        ('PENDIENTE', 'Pendiente de Cobro'),
        ('PARCIAL', 'Pago Parcial'),
        ('PAGADO', 'Pagado 100%'),
    )
    numero_factura = models.CharField(max_length=30, unique=True)
    obra = models.ForeignKey(Obra, on_delete=models.CASCADE, related_name='facturas')
    fecha_emision = models.DateField(auto_now_add=True)
    fecha_vencimiento = models.DateField()
    monto_neto = models.DecimalField(max_digits=12, decimal_places=0)
    monto_total = models.DecimalField(max_digits=12, decimal_places=0)
    saldo_pendiente = models.DecimalField(max_digits=12, decimal_places=0)
    estado_pago = models.CharField(max_length=20, choices=ESTADOS_PAGO, default='PENDIENTE')

    def __str__(self):
        return f"{self.numero_factura} ({self.estado_pago})"


class Pago(models.Model):
    factura = models.ForeignKey(Factura, on_delete=models.CASCADE, related_name='pagos')
    monto = models.DecimalField(max_digits=12, decimal_places=0)
    fecha_pago = models.DateField()
    metodo_pago = models.CharField(max_length=50)
    comprobante = models.CharField(max_length=100)
    folio_recibo = models.CharField(max_length=30)


class AuditoriaLog(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True)
    accion = models.CharField(max_length=100)
    detalle = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)


class Material(models.Model):
    codigo = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=150)
    unidad_medida = models.CharField(max_length=20, default='un')
    stock_actual = models.IntegerField(default=0)
    stock_critico = models.IntegerField(default=5)

    def __str__(self):
        return f"{self.codigo} - {self.nombre} (Stock: {self.stock_actual})"


class MovimientoBodega(models.Model):
    TIPOS = (
        ('INGRESO', 'Ingreso / Recepción'),
        ('EGRESO', 'Egreso a Faena'),
    )
    material = models.ForeignKey(Material, on_delete=models.CASCADE, related_name='movimientos')
    obra = models.ForeignKey(Obra, on_delete=models.SET_NULL, null=True, blank=True, related_name='despachos_material')
    tipo = models.CharField(max_length=10, choices=TIPOS)
    cantidad = models.IntegerField()
    fecha = models.DateTimeField(auto_now_add=True)
    responsable = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True)
    observaciones = models.TextField(blank=True, null=True)