"""Carga datos de demostración alineados con los flujos reales del MVP.

Uso:
    python manage.py seed_demo
    python manage.py seed_demo --password "OtraClave2026!"

Es idempotente: los registros demo usan numeración reservada (900) y, si ya
existen, se omiten en lugar de duplicarse.

Los usuarios demo se crean con login por email (API). El admin de Django usa
username + password, y esas cuentas demo no son staff: para el admin usa tu
propio superusuario.
"""

from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from api.models import (
    CategoriaServicio, Cliente, Contrato, CostoMaterial, Factura, ItemPresupuesto,
    Obra, Presupuesto, Usuario,
)
from api.services import (
    actualizar_totales_presupuesto, enviar_presupuesto, guardar_version_presupuesto,
    registrar_decision_cliente, registrar_pago, transicionar_obra,
)

CLAVE_POR_DEFECTO = 'Fyag2026!'

CUENTAS = (
    ('admin@fyag.cl', 'Andrea', 'Vargas', None, 'Administrador general', 'ADMIN_GENERAL'),
    ('gerencia@fyag.cl', 'Rocío', 'Morales', '11.111.111-1', 'Gerencia General', 'GERENCIA'),
    ('finanzas@fyag.cl', 'Felipe', 'Rojas', '12.222.222-2', 'Analista de Finanzas', 'FINANZAS'),
    ('supervisor@fyag.cl', 'Sergio', 'Cáceres', '13.333.333-3', 'Supervisor de Obras', 'SUPERVISOR'),
    ('tecnico@fyag.cl', 'Carlos', 'Araya', '16.892.441-K', 'Técnico de Climatización', 'TECNICO'),
    ('tecnico2@fyag.cl', 'Eduardo', 'Vera', '15.234.890-2', 'Técnico de Mantención', 'TECNICO'),
    ('tecnico3@fyag.cl', 'Camila', 'Fuentes', None, 'Técnica de Refrigeración', 'TECNICO'),
    ('tecnico4@fyag.cl', 'Matías', 'Silva', None, 'Técnico Eléctrico', 'TECNICO'),
    ('tecnico5@fyag.cl', 'Valentina', 'Muñoz', None, 'Técnica de Mantención', 'TECNICO'),
)

CLIENTES = (
    ('CLI-2026-001', '96.540.000-1', 'CMPC Celulosa S.A.',
     'Elaboración de celulosa y papel', 'Camino Planta Pacífico s/n, Laja',
     'Ing. Rodrigo Sepúlveda', 'Jefe de Proyectos', 'rsepulveda@cmpc.cl',
     '+56 9 8412 3390', 'celulosa'),
    ('CLI-2026-002', '77.204.300-4', 'Antofagasta Minerals S.A.',
     'Extracción y concentración de cobre', 'Minera Los Pelambres, Salamanca',
     'Carlos Henríquez', 'Superintendente de Mantención', 'chenriquez@aminerals.cl',
     '+56 9 7201 4455', 'mineria'),
    ('CLI-2026-003', '90.227.000-4', 'Viña Concha y Toro S.A.',
     'Producción vitivinícola', 'Av. Nueva Tajamar 481, Santiago',
     'María José Fuentes', 'Encargada de Infraestructura', 'mjfuentes@conchaytoro.cl',
     '+56 9 6655 1122', 'agroindustria'),
)


class Command(BaseCommand):
    help = 'Crea usuarios, clientes, presupuestos, obras, costos y facturas de demostración.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--password',
            default=CLAVE_POR_DEFECTO,
            help=f'Clave para los usuarios demo (por defecto: {CLAVE_POR_DEFECTO})',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        self.password = options['password']
        self.hoy = timezone.localdate()

        self.stdout.write(self.style.MIGRATE_HEADING('Datos demo FYAG'))

        usuarios = self._crear_usuarios()
        categorias = self._crear_catalogos()
        clientes = self._crear_clientes()
        contrato = self._crear_contrato(clientes)

        finanzas = usuarios['finanzas@fyag.cl']
        gerencia = usuarios['gerencia@fyag.cl']
        supervisor = usuarios['supervisor@fyag.cl']
        tecnico_1 = usuarios['tecnico@fyag.cl']
        tecnico_2 = usuarios['tecnico2@fyag.cl']

        # 1) Presupuesto aprobado -> obra finalizada con pago parcial.
        p1 = self._crear_presupuesto(
            'PRE-2026-900001', clientes['CLI-2026-001'], categorias['Climatización'],
            contrato, 'Ing. Rodrigo Sepúlveda', finanzas,
            [
                ('Suministro e instalación de unidad VRF 24 HP', 2, 'un', Decimal('4500000')),
                ('Ductería y aislación térmica', 1, 'gl', Decimal('3200000')),
                ('Puesta en marcha y certificación', 1, 'gl', Decimal('850000')),
            ],
            destino='aprobado',
        )
        obra_1 = self._crear_obra(
            'OBR-2026-900001', p1, 'Climatización Planta Pacífico',
            tecnico_1, categorias['Climatización'], 100, supervisor,
        )
        self._crear_costos(obra_1, supervisor, [
            ('MATERIALES', Decimal('1850000'), 'Insumos de ductería y aislación', 100, 'm'),
            ('MANO_DE_OBRA', Decimal('2400000'), 'Cuadrilla de instalación (12 días)', 96, 'h'),
        ])
        self._finalizar(obra_1, supervisor)
        factura_1 = self._crear_factura(
            'FAC-2026-900001', obra_1, p1.monto_neto, p1.monto_total, finanzas,
        )
        self._registrar_pago(factura_1, (factura_1.monto_total * Decimal('0.40')).quantize(Decimal('1')),
                             finanzas, 'TRF-2026-0001', 'REC-2026-0001')

        # 2) Presupuesto aprobado -> obra en proceso (sin facturar).
        p2 = self._crear_presupuesto(
            'PRE-2026-900002', clientes['CLI-2026-002'], categorias['Mantención'],
            None, 'Carlos Henríquez', finanzas,
            [
                ('Mantención preventiva de chillers', 4, 'un', Decimal('780000')),
                ('Repuestos y filtros', 1, 'gl', Decimal('640000')),
            ],
            destino='aprobado',
        )
        obra_2 = self._crear_obra(
            'OBR-2026-900002', p2, 'Mantención Minera Los Pelambres',
            tecnico_2, categorias['Mantención'], 35, supervisor,
        )
        self._crear_costos(obra_2, supervisor, [
            ('MATERIALES', Decimal('420000'), 'Filtros y consumibles'),
        ])

        # 3) Presupuesto aprobado -> obra finalizada, pagada y cerrada comercialmente.
        p3 = self._crear_presupuesto(
            'PRE-2026-900003', clientes['CLI-2026-003'], categorias['Proyecto eléctrico'],
            None, 'María José Fuentes', finanzas,
            [
                ('Tablero eléctrico de fuerza', 1, 'un', Decimal('2850000')),
                ('Cableado y canalización', 1, 'gl', Decimal('1900000')),
                ('Certificación TE1', 1, 'gl', Decimal('420000')),
            ],
            destino='aprobado',
        )
        obra_3 = self._crear_obra(
            'OBR-2026-900003', p3, 'Proyecto eléctrico Viña Concha y Toro',
            tecnico_2, categorias['Proyecto eléctrico'], 100, supervisor,
        )
        self._crear_costos(obra_3, supervisor, [
            ('MATERIALES', Decimal('1450000'), 'Tablero, cables y canalizaciones', 1, 'lote'),
            ('SUBCONTRATO', Decimal('780000'), 'Instalación eléctrica autorizada'),
            ('MANO_DE_OBRA', Decimal('60000'), 'Supervisión técnica', 4, 'h'),
        ])
        self._finalizar(obra_3, supervisor)
        factura_2 = self._crear_factura(
            'FAC-2026-900003', obra_3, p3.monto_neto, p3.monto_total, finanzas,
        )
        self._registrar_pago(factura_2, factura_2.monto_total, finanzas,
                             'TRF-2026-0002', 'REC-2026-0002')

        # 4) Presupuesto aprobado sin obra: sirve para crear una obra desde la API.
        self._crear_presupuesto(
            'PRE-2026-900004', clientes['CLI-2026-001'], categorias['Proyecto'],
            contrato, 'Ing. Rodrigo Sepúlveda', finanzas,
            [
                ('Ingeniería de detalle', 1, 'gl', Decimal('1250000')),
                ('Montaje de equipos', 1, 'gl', Decimal('4800000')),
            ],
            destino='aprobado',
        )

        # 5) Presupuesto en borrador.
        self._crear_presupuesto(
            'PRE-2026-900005', clientes['CLI-2026-002'], categorias['Mantención'],
            None, 'Carlos Henríquez', finanzas,
            [
                ('Diagnóstico de red de aire comprimido', 1, 'gl', Decimal('950000')),
            ],
            destino='borrador',
        )

        # 6) Presupuesto con aprobación interna de Gerencia pendiente.
        self._crear_presupuesto(
            'PRE-2026-900006', clientes['CLI-2026-001'], categorias['Proyecto'],
            contrato, 'Ing. Rodrigo Sepúlveda', finanzas,
            [
                ('Ampliación de sala de máquinas', 1, 'gl', Decimal('8400000')),
                ('Automatización y control', 1, 'gl', Decimal('2100000')),
            ],
            destino='pendiente_gerencia', requiere_gerencia=True,
        )

        # 7) Presupuesto enviado, a la espera de la decisión del cliente.
        self._crear_presupuesto(
            'PRE-2026-900007', clientes['CLI-2026-003'], categorias['Emergencia'],
            None, 'María José Fuentes', finanzas,
            [
                ('Atención de emergencia por fuga de refrigerante', 1, 'gl', Decimal('1480000')),
            ],
            destino='enviado',
        )

        self._resumen()
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Datos demo cargados.'))
        self.stdout.write('Login de la API con email + password en /api/auth/login/')
        for email, nombre, _, _, _, rol in CUENTAS:
            self.stdout.write(f'  - {email:<22} {rol:<10} clave: {self.password}')
        self.stdout.write('')
        self.stdout.write('Presupuestos demo: PRE-2026-900001 .. PRE-2026-900007')
        self.stdout.write('Obras demo: OBR-2026-900001, OBR-2026-900002, OBR-2026-900003')
        self.stdout.write(f'Gerencia demo: {gerencia.email}')

    # ------------------------------------------------------------------ datos

    def _crear_usuarios(self):
        usuarios = {}
        for email, nombre, apellido, rut, cargo, rol in CUENTAS:
            usuario, creado = Usuario.all_objects.update_or_create(
                email=email,
                defaults={
                    'username': email,
                    'first_name': nombre,
                    'last_name': apellido,
                    'rut_usuario': rut,
                    'cargo': cargo,
                    'rol': rol,
                    'estado': 'activo',
                    'is_active': True,
                    'is_staff': False,
                    'deleted_at': None,
                },
            )
            usuario.set_password(self.password)
            usuario.save()
            usuarios[email] = usuario
            self.stdout.write(f'  {"+" if creado else "="} usuario {email} ({rol})')
        return usuarios

    def _crear_catalogos(self):
        call_command('seed_catalogs', stdout=StringIO())
        categorias = {categoria.nombre: categoria for categoria in CategoriaServicio.objects.all()}
        self.stdout.write(f'  = categorías disponibles: {len(categorias)}')
        return categorias

    def _crear_clientes(self):
        clientes = {}
        for codigo, rut, razon, giro, direccion, contacto, cargo, correo, telefono, sector in CLIENTES:
            cliente, creado = Cliente.all_objects.update_or_create(
                codigo_cliente=codigo,
                defaults={
                    'rut_cliente': rut,
                    'razon_social': razon,
                    'giro_comercial': giro,
                    'direccion': direccion,
                    'contacto_principal': contacto,
                    'cargo_contacto': cargo,
                    'correo_contacto': correo,
                    'telefono_contacto': telefono,
                    'sector': sector,
                    'estado': 'activo',
                    'habilitar_emision': True,
                    'deleted_at': None,
                },
            )
            clientes[codigo] = cliente
            self.stdout.write(f'  {"+" if creado else "="} cliente {codigo} {razon}')
        return clientes

    def _crear_contrato(self, clientes):
        contrato, creado = Contrato.all_objects.update_or_create(
            numero_contrato='CT-2026-001',
            defaults={
                'cliente': clientes['CLI-2026-001'],
                'nombre': 'Mantención integral de climatización 2026',
                'fecha_inicio': self.hoy - timedelta(days=60),
                'fecha_termino': self.hoy + timedelta(days=300),
                'estado': 'vigente',
                'observaciones': 'Contrato marco de mantención preventiva y correctiva.',
                'deleted_at': None,
            },
        )
        self.stdout.write(f'  {"+" if creado else "="} contrato CT-2026-001')
        return contrato

    # ------------------------------------------------------------ presupuesto

    def _crear_presupuesto(self, numero, cliente, categoria, contrato, contacto,
                           autor, partidas, destino='borrador', requiere_gerencia=False):
        existente = Presupuesto.all_objects.filter(numero_presupuesto=numero).first()
        if existente:
            self._avanzar_presupuesto(existente, destino, autor)
            self.stdout.write(f'  = presupuesto {numero} ya existe')
            return existente

        presupuesto = Presupuesto.objects.create(
            numero_presupuesto=numero,
            cliente=cliente,
            contrato=contrato,
            categoria_servicio=categoria,
            contacto=contacto,
            fecha_vencimiento=self.hoy + timedelta(days=30),
            requiere_aprobacion_gerencia=requiere_gerencia,
            created_by=autor,
            updated_by=autor,
        )
        for descripcion, cantidad, unidad, precio in partidas:
            ItemPresupuesto.objects.create(
                presupuesto=presupuesto,
                descripcion=descripcion,
                cantidad=cantidad,
                unidad=unidad,
                precio_unitario=precio,
                created_by=autor,
                updated_by=autor,
            )
        actualizar_totales_presupuesto(presupuesto)
        guardar_version_presupuesto(presupuesto, autor)
        self._avanzar_presupuesto(presupuesto, destino, autor)
        self.stdout.write(
            f'  + presupuesto {numero} (${presupuesto.monto_total:,.0f} CLP, {presupuesto.estado})'
        )
        return presupuesto

    def _avanzar_presupuesto(self, presupuesto, destino, autor):
        """Lleva el presupuesto a `destino` respetando el workflow real."""
        if destino == 'borrador':
            return
        if destino in {'enviado', 'pendiente_gerencia'} and presupuesto.estado == 'borrador':
            enviar_presupuesto(presupuesto, autor)
        if destino == 'aprobado':
            if presupuesto.estado == 'borrador':
                enviar_presupuesto(presupuesto, autor)
            if presupuesto.estado == 'enviado':
                registrar_decision_cliente(presupuesto, 'aprobado', autor)

    # ------------------------------------------------------------------ obra

    def _crear_obra(self, codigo, presupuesto, nombre, tecnico, categoria, avance, autor):
        existente = Obra.all_objects.filter(codigo_obra=codigo).first()
        if existente:
            self.stdout.write(f'  = obra {codigo} ya existe')
            return existente

        obra = Obra.objects.create(
            codigo_obra=codigo,
            nombre_obra=nombre,
            presupuesto=presupuesto,
            tecnico_responsable=tecnico,
            clasificacion_servicio=categoria,
            avance_porcentaje=avance,
            fecha_inicio=self.hoy - timedelta(days=20),
            created_by=autor,
            updated_by=autor,
        )
        self.stdout.write(f'  + obra {codigo} ({nombre})')
        return obra

    def _crear_costos(self, obra, autor, costos):
        if obra.costos.exists():
            self.stdout.write(f'  = costos de {obra.codigo_obra} ya existen')
            return
        for categoria, monto, descripcion, *desglose in costos:
            datos_reales = {}
            if desglose:
                cantidad, unidad = desglose
                datos_reales = {
                    'cantidad_real': cantidad, 'unidad_real': unidad, 'costo_unitario_real': monto / cantidad,
                }
            CostoMaterial.objects.create(
                obra=obra,
                categoria=categoria,
                monto=monto,
                descripcion=descripcion,
                created_by=autor,
                updated_by=autor,
                **datos_reales,
            )
        self.stdout.write(f'  + {len(costos)} costo(s) en {obra.codigo_obra}')

    def _finalizar(self, obra, autor):
        if obra.estado_operativo == 'finalizada':
            return
        transicionar_obra(obra, 'finalizada', autor, costos_confirmados=True)
        self.stdout.write(f'  + obra {obra.codigo_obra} finalizada')

    # ------------------------------------------------------------- facturación

    def _crear_factura(self, numero, obra, monto_neto, monto_total, autor):
        existente = Factura.all_objects.filter(numero_factura=numero).first()
        if existente:
            self.stdout.write(f'  = factura {numero} ya existe')
            return existente

        factura = Factura.objects.create(
            numero_factura=numero,
            obra=obra,
            fecha_vencimiento=self.hoy + timedelta(days=15),
            monto_neto=monto_neto,
            monto_total=monto_total,
            saldo_pendiente=monto_total,
            estado_pago='PENDIENTE',
            created_by=autor,
            updated_by=autor,
        )
        obra.estado_comercial = 'pendiente_cobro'
        obra.updated_by = autor
        obra.save(update_fields=['estado_comercial', 'updated_by', 'updated_at'])
        self.stdout.write(f'  + factura {numero} (${monto_total:,.0f} CLP)')
        return factura

    def _registrar_pago(self, factura, monto, autor, comprobante, folio):
        if factura.pagos.exists():
            self.stdout.write(f'  = factura {factura.numero_factura} ya tiene pagos')
            return
        registrar_pago(
            factura,
            {
                'monto': monto,
                'fecha_pago': self.hoy,
                'metodo_pago': 'Transferencia bancaria',
                'comprobante': comprobante,
                'folio_recibo': folio,
            },
            autor,
        )
        factura.refresh_from_db()
        self.stdout.write(
            f'  + pago ${monto:,.0f} en {factura.numero_factura} '
            f'(saldo ${factura.saldo_pendiente:,.0f})'
        )

    # ------------------------------------------------------------------ salida

    def _resumen(self):
        self.stdout.write('')
        self.stdout.write('Resumen:')
        self.stdout.write(f'  presupuestos: {Presupuesto.objects.count()}')
        self.stdout.write(f'  obras: {Obra.objects.count()}')
        self.stdout.write(f'  facturas: {Factura.objects.count()}')
        self.stdout.write(f'  costos: {CostoMaterial.objects.count()}')
