from datetime import timedelta

from django.utils import timezone

from .models import Factura, Obra
from .tests import FyagAPITestCase


class PendientesProveedoresTests(FyagAPITestCase):
    def test_pendientes_priorizan_antiguedad_y_separan_vencimientos(self):
        hoy = timezone.localdate()
        antigua = self.crear_obra(estado='finalizada', comercial='pendiente_facturacion')
        reciente = self.crear_obra(
            presupuesto=self.crear_presupuesto(estado='aprobado', numero='PRE-RECIENTE'),
            estado='finalizada', comercial='pendiente_cobro',
        )
        Obra.objects.filter(pk=antigua.pk).update(fecha_termino=hoy - timedelta(days=15))
        Obra.objects.filter(pk=reciente.pk).update(fecha_termino=hoy - timedelta(days=2))
        factura = self.crear_factura(reciente, total=50000)
        Factura.objects.filter(pk=factura.pk).update(fecha_vencimiento=hoy - timedelta(days=3))
        fuera_de_plazo = self.crear_factura(reciente, total=10000, numero='FAC-FUTURA')
        self.autenticar(self.gerencia)
        response = self.api.get('/api/facturas/pendientes/')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual([item['id'] for item in response.data['facturacion']], [antigua.pk, reciente.pk])
        self.assertEqual(response.data['facturacion'][0]['dias'], 15)
        self.assertEqual(response.data['facturacion'][1]['saldo'], reciente.presupuesto.monto_total - 60000)
        self.assertEqual([item['id'] for item in response.data['cobranza']], [factura.pk])
        self.assertEqual(response.data['cobranza'][0]['dias'], -3)
        self.assertNotEqual(factura.pk, fuera_de_plazo.pk)
        self.autenticar(self.supervisor)
        self.assertEqual(self.api.get('/api/facturas/pendientes/').status_code, 403)

    def test_proveedor_normalizado_y_vinculado_a_costo(self):
        obra = self.crear_obra()
        self.autenticar(self.finanzas)
        datos = {'rut': '12.345.678-5', 'razon_social': 'Proveedor de prueba'}
        proveedor = self.api.post('/api/proveedores/', datos, format='json')
        self.assertEqual(proveedor.status_code, 201, proveedor.data)
        self.assertEqual(proveedor.data['rut'], '12345678-5')
        self.assertEqual(self.api.post('/api/proveedores/', datos, format='json').status_code, 400)
        response = self.api.post('/api/costos/', {
            'obra': obra.pk, 'categoria': 'EQUIPAMIENTO', 'monto': '1000',
            'descripcion': 'Arriendo', 'proveedor': proveedor.data['id'],
        }, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['proveedor_nombre'], datos['razon_social'])
        self.autenticar(self.supervisor)
        self.assertEqual(self.api.get('/api/proveedores/').status_code, 200)
        self.assertEqual(self.api.post('/api/proveedores/', datos, format='json').status_code, 403)
