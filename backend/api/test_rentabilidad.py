from django.utils import timezone

from .models import CostoMaterial, Factura, Material, NotaCredito, ObraMaterial
from .tests import FyagAPITestCase


class RentabilidadTests(FyagAPITestCase):
    def test_finalizacion_exige_despachos_conciliados_horas_y_confirmacion(self):
        obra = self.crear_obra(tecnico=self.tecnico)
        asignacion = ObraMaterial.objects.create(
            obra=obra, material=Material.objects.first(), cantidad_planificada='8.000',
        )
        self.autenticar(self.supervisor)
        path = f'/api/obras/{obra.pk}/transicionar/'
        cierre = {'estado_operativo': 'finalizada', 'costos_confirmados': True}
        response = self.api.post(path, cierre, format='json')
        self.assertEqual(response.data['error'], 'COSTOS_INCOMPLETOS')
        horas = self.api.post('/api/costos/', {
            'obra': obra.pk, 'categoria': 'MANO_DE_OBRA', 'descripcion': 'Instalación',
            'cantidad_real': '2.000', 'unidad_real': 'h', 'costo_unitario_real': '12000',
        }, format='json')
        self.assertEqual(horas.status_code, 201, horas.data)
        movimiento_path = f'/api/obras/{obra.pk}/materiales/{asignacion.pk}/movimientos/'
        entrada = self.api.post(movimiento_path, {
            'tipo': 'entrada', 'cantidad': '8.000', 'motivo': 'Despacho a obra',
        }, format='json')
        self.assertEqual(entrada.status_code, 201, entrada.data)
        despacho = entrada.data['movimientos'][0]['id']
        pendientes = self.api.get(f'/api/costos/despachos/{obra.pk}/')
        self.assertEqual([mov['id'] for mov in pendientes.data], [despacho])
        response = self.api.post(path, cierre, format='json')
        self.assertIn('despachos', str(response.data['detalle']))
        payload = {'obra': obra.pk, 'categoria': 'MATERIALES', 'descripcion': 'Material despachado',
                   'despacho': despacho, 'costo_unitario_real': '3000'}
        costo = self.api.post('/api/costos/', payload, format='json')
        self.assertEqual(costo.status_code, 201, costo.data)
        self.assertEqual(costo.data['monto'], '24000')
        self.assertEqual(self.api.post('/api/costos/', payload, format='json').status_code, 400)
        self.assertEqual(self.api.post(path, {'estado_operativo': 'finalizada'}, format='json').status_code, 400)
        response = self.api.post(path, cierre, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.api.post('/api/costos/', payload, format='json').status_code, 400)
        self.assertIn('confirmados', obra.historial_estados.last().observacion)

        self.autenticar(self.gerencia)
        dashboard = self.api.get('/api/dashboard/resumen/', {'actualizar': '1'}).data
        fila = next(fila for fila in dashboard['rentabilidad']['obras'] if fila['id'] == obra.pk)
        self.assertEqual(fila['presupuesto_neto'], obra.presupuesto.monto_neto)
        self.assertEqual(fila['materiales'], 24000)
        self.assertEqual(fila['costos_directos'], 48000)

    def test_detalle_otros_costos_coincide_con_el_acumulado_de_la_obra(self):
        obra = self.crear_obra()
        incluido = CostoMaterial.objects.create(
            obra=obra, categoria='EQUIPAMIENTO', descripcion='Arriendo de plataforma', monto=18000,
        )
        CostoMaterial.objects.create(obra=obra, categoria='MATERIALES', descripcion='Tubería', monto=3000)
        eliminado = CostoMaterial.objects.create(obra=obra, categoria='VARIOS', descripcion='Duplicado', monto=1000)
        eliminado.soft_delete()

        self.autenticar(self.gerencia)
        path = f'/api/dashboard/obras/{obra.pk}/otros-costos/'
        response = self.api.get(path)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual([costo['id'] for costo in response.data['registros']], [incluido.pk])
        self.assertEqual(response.data['registros'][0]['categoria'], 'Equipamiento')
        dashboard = self.api.get('/api/dashboard/resumen/', {'actualizar': '1'}).data
        fila = next(fila for fila in dashboard['rentabilidad']['obras'] if fila['id'] == obra.pk)
        self.assertEqual(response.data['total'], fila['otros_costos'])
        self.assertEqual(response.data['total'], 18000)

        self.autenticar(self.supervisor)
        self.assertEqual(self.api.get(path).status_code, 403)

    def test_resultado_directo_y_operativo_con_costos_desglosados(self):
        obra = self.crear_obra()
        self.autenticar(self.finanzas)
        for categoria, cantidad, unidad, tarifa, esperado in (
            ('MANO_DE_OBRA', '2.500', 'h', '12000', '30000'),
            ('MATERIALES', '8.250', 'm', '4000', '33000'),
        ):
            response = self.api.post('/api/costos/', {
                'obra': obra.pk, 'categoria': categoria, 'descripcion': categoria,
                'cantidad_real': cantidad, 'unidad_real': unidad, 'costo_unitario_real': tarifa,
            }, format='json')
            self.assertEqual(response.status_code, 201, response.data)
            self.assertEqual(response.data['monto'], esperado)

        factura = self.crear_factura(obra, total=59500)
        Factura.objects.filter(pk=factura.pk).update(monto_neto=50000)
        NotaCredito.objects.create(factura=factura, numero='NC-RENT-001', monto=11900, motivo='Descuento')
        hoy = timezone.localdate().isoformat()
        response = self.api.post('/api/gastos-generales/', {
            'fecha': hoy, 'descripcion': 'Arriendo', 'monto': '5000',
        }, format='json')
        self.assertEqual(response.status_code, 201, response.data)

        self.autenticar(self.gerencia)
        filtros = {'desde': hoy, 'hasta': hoy, 'actualizar': '1'}
        response = self.api.get('/api/dashboard/resumen/', filtros)
        self.assertEqual(response.status_code, 200, response.data)
        rentabilidad = response.data['rentabilidad']
        fila = next(fila for fila in rentabilidad['obras'] if fila['id'] == obra.pk)
        self.assertEqual(fila['ingresos'], 40000)
        self.assertEqual(fila['resultado'], -23000)
        self.assertEqual(fila['pendientes'], ['Cierre comercial pendiente'])
        self.assertEqual(rentabilidad['periodo']['resultado'], -23000)
        self.assertEqual(rentabilidad['empresa']['resultado'], -28000)
        limitado = self.api.get('/api/dashboard/resumen/', {**filtros, 'estado_obra': 'en-proceso'})
        self.assertIsNone(limitado.data['rentabilidad']['empresa'])
        self.assertEqual(self.api.post('/api/gastos-generales/', {}, format='json').status_code, 403)
