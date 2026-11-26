from datetime import timedelta

from django.utils import timezone

from .models import Material, ObraMaterial
from .tests import FyagAPITestCase


class EntradasLimiteTests(FyagAPITestCase):
    def test_documentos_repetidos_no_modifican_el_saldo(self):
        obra = self.crear_obra(estado='finalizada', comercial='pendiente_cobro')
        factura = self.crear_factura(obra)
        self.autenticar(self.finanzas)
        pago = {'factura': factura.pk, 'monto': '5000', 'fecha_pago': timezone.localdate(),
                'metodo_pago': 'Transferencia', 'folio_recibo': 'Pago-1'}
        self.assertEqual(self.api.post('/api/pagos/', pago, format='json').status_code, 201)
        repetido = self.api.post('/api/pagos/', {**pago, 'folio_recibo': 'pago-1'}, format='json')
        self.assertEqual(repetido.status_code, 400, repetido.data)
        self.assertIn('comprobante', repetido.data)
        self.assertEqual(self.api.post('/api/pagos/', {**pago, 'folio_recibo': 'Pago-2'}, format='json').status_code, 201)
        ruta = f'/api/facturas/{factura.pk}/notas-credito/'
        nota = {'numero': 'NC-LIMITE', 'monto': '1000', 'motivo': 'Ajuste'}
        self.assertEqual(self.api.post(ruta, nota, format='json').status_code, 200)
        repetida = self.api.post(ruta, nota, format='json')
        self.assertEqual(repetida.status_code, 400)
        self.assertIn('numero', repetida.data)
        factura.refresh_from_db()
        self.assertEqual(factura.saldo_pendiente, 39000)

    def test_entrada_repetida_no_aumenta_el_saldo_y_otra_referencia_si(self):
        obra = self.crear_obra()
        asignacion = ObraMaterial.objects.create(obra=obra, material=Material.objects.first(), cantidad_planificada=10)
        self.autenticar(self.supervisor)
        ruta = f'/api/obras/{obra.pk}/materiales/{asignacion.pk}/movimientos/'
        entrada = {'tipo': 'entrada', 'cantidad': '2.000', 'motivo': 'Recepción', 'referencia': 'GD-1'}
        self.assertEqual(self.api.post(ruta, entrada, format='json').status_code, 201)
        self.assertEqual(self.api.post(ruta, {**entrada, 'referencia': 'gd-1'}, format='json').status_code, 400)
        self.assertEqual(self.api.post(ruta, {**entrada, 'referencia': ''}, format='json').status_code, 400)
        resultado = self.api.post(ruta, {**entrada, 'referencia': 'GD-2'}, format='json')
        self.assertEqual(resultado.status_code, 201, resultado.data)
        self.assertEqual(resultado.data['saldo'], '4.000')

    def test_facturas_validan_neto_y_total_segun_iva(self):
        obra = self.crear_obra(estado='finalizada', comercial='pendiente_facturacion')
        self.autenticar(self.finanzas)
        datos = {'obra': obra.pk, 'fecha_vencimiento': timezone.localdate() + timedelta(days=30)}
        for neto, total, iva in ((0, 5, False), (100, 101, True), (100, 119, False), (100, 100, True)):
            response = self.api.post('/api/facturas/', {
                **datos, 'monto_neto': neto, 'monto_total': total, 'aplica_iva': iva,
            }, format='json')
            self.assertEqual(response.status_code, 400, response.data)
        for neto, total, iva in ((150, 178, True), (100, 100, False)):
            response = self.api.post('/api/facturas/', {
                **datos, 'monto_neto': neto, 'monto_total': total, 'aplica_iva': iva,
            }, format='json')
            self.assertEqual(response.status_code, 201, response.data)

    def test_fechas_invalidas_o_fuera_de_rango_devuelven_error_de_validacion(self):
        self.autenticar(self.supervisor)
        response = self.api.get('/api/obras/', {'desde': '2026-02-30'})
        self.assertEqual(response.status_code, 400)
        self.assertIn('desde', response.data)
        response = self.api.get('/api/obras/tecnicos-disponibles/', {
            'inicio': '2026-01-05T08:00', 'fin': '2028-01-10T18:00',
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn('planificacion', response.data)
        response = self.api.get('/api/obras/agenda-tecnico/', {
            'tecnico_id': self.tecnico.pk, 'desde': '9999-12-30', 'hasta': '9999-12-31',
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn('hasta', response.data)

    def test_costo_en_el_umbral_de_redondeo_a_un_peso(self):
        obra = self.crear_obra()
        self.autenticar(self.finanzas)
        datos = {'obra': obra.pk, 'categoria': 'MATERIALES', 'descripcion': 'Costo fraccional',
                 'unidad_real': 'm', 'cantidad_real': '0.050'}
        bajo = self.api.post('/api/costos/', {**datos, 'costo_unitario_real': '9.99'}, format='json')
        self.assertEqual(bajo.status_code, 400, bajo.data)
        valido = self.api.post('/api/costos/', {**datos, 'costo_unitario_real': '10.00'}, format='json')
        self.assertEqual(valido.status_code, 201, valido.data)
        self.assertEqual(valido.data['monto'], '1')
