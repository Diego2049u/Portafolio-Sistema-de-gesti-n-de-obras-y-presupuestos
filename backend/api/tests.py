from django.test import TestCase
from rest_framework.exceptions import ValidationError
from .models import Obra, Factura, Cliente
from .services import validar_cierre_obra

class MotorReglasTestCase(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(
            razon_social="Empresa Test SpA",
            rut_cliente="76123456-7"
        )
        self.obra = Obra.objects.create(
            codigo_obra="OB-2026-001",
            nombre_obra="Instalación Frigorífica Test",
            cliente=self.cliente,
            estado_operativo='en_ejecucion'
        )

    def test_bloqueo_cierre_obra_con_factura_pendiente(self):
        # Crear factura no pagada para la obra
        Factura.objects.create(
            obra=self.obra,
            numero_factura="F-101",
            monto_total=1500000,
            saldo_pendiente=1500000,
            estado_pago='PENDIENTE'
        )
        
        # Debe lanzar error al intentar cerrar la obra (RF-07)
        with self.assertRaises(ValidationError):
            validar_cierre_obra(self.obra)

    def test_permite_cierre_obra_sin_deudas(self):
        # Crear factura completamente pagada
        Factura.objects.create(
            obra=self.obra,
            numero_factura="F-102",
            monto_total=1500000,
            saldo_pendiente=0,
            estado_pago='PAGADO'
        )
        
        # Debe retornar True sin errores
        self.assertTrue(validar_cierre_obra(self.obra))