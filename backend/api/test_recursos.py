from decimal import Decimal

from django.utils import timezone

from .models import Material, MermaMaterial, MovimientoMaterial, Obra, ObraMaterial
from .tests import FyagAPITestCase


class RecursosTests(FyagAPITestCase):
    def setUp(self):
        super().setUp()
        self.autenticar(self.supervisor)
        self.presupuesto = self.crear_presupuesto(estado='aprobado')
        self.materiales = list(Material.objects.filter(activo=True)[:11])
        self.payload = {
            'presupuesto': self.presupuesto.pk,
            'clasificacion_servicio': self.categoria.pk,
            'nombre_obra': 'Obra con recursos',
            'tecnico_responsable': self.tecnico.pk,
            'inicio_programado': '2026-11-16T08:00',
            'fin_estimado': '2026-11-16T18:00',
        }

    def crear_con_materiales(self, materiales):
        return self.api.post('/api/obras/', {
            **self.payload,
            'materiales': [{'material': item.pk, 'cantidad_planificada': '15.500'} for item in materiales],
        }, format='json')

    def test_rechaza_duplicados_limite_e_inactivos_sin_crear_obra(self):
        material = self.materiales[0]
        for seleccion in (self.materiales, [material, material]):
            response = self.crear_con_materiales(seleccion)
            self.assertEqual(response.status_code, 400, response.data)
            self.assertIn('materiales', response.data)
        material.activo = False
        material.save(update_fields=['activo'])
        self.assertEqual(self.crear_con_materiales([material]).status_code, 400)
        self.assertFalse(Obra.objects.filter(presupuesto=self.presupuesto).exists())

    def test_saldos_totales_consolidan_obras_y_distinguen_saldos_desconocidos(self):
        material = self.materiales[0]
        for indice, entrada in enumerate(('10.250', '5.000', None), start=1):
            presupuesto = self.crear_presupuesto(estado='aprobado', numero=f'PRE-SALDOS-{indice}')
            obra = self.crear_obra(presupuesto=presupuesto)
            asignacion = ObraMaterial.objects.create(obra=obra, material=material, cantidad_planificada=20)
            if entrada is not None:
                MovimientoMaterial.objects.create(
                    asignacion=asignacion, tipo='entrada', cantidad=entrada,
                    motivo='Despacho', registrado_por=self.supervisor,
                )
                MovimientoMaterial.objects.create(
                    asignacion=asignacion, tipo='consumo', cantidad='2.000',
                    motivo='Instalación', registrado_por=self.supervisor,
                )
                MermaMaterial.objects.create(
                    asignacion=asignacion, cantidad='0.500', motivo='Corte', registrado_por=self.supervisor,
                )

        path = '/api/materiales/saldos-totales/'
        response = self.api.get(path)
        self.assertEqual(response.status_code, 200, response.data)
        fila = next(item for item in response.data if item['id'] == material.pk)
        self.assertEqual(fila['saldo'], '10.250')
        self.assertEqual(fila['unidad'], material.unidad)
        self.assertEqual(fila['sin_entradas'], 1)
        self.assertCountEqual([obra['saldo'] for obra in fila['obras']], ['7.750', '2.500', None])
        self.autenticar(self.finanzas)
        self.assertEqual(self.api.get(path).status_code, 403)

    def test_asignacion_merma_y_acceso_por_rol(self):
        response = self.crear_con_materiales(self.materiales[:10])
        self.assertEqual(response.status_code, 201, response.data)
        obra_id = response.data['id']
        path = f'/api/obras/{obra_id}/materiales/'
        asignaciones = self.api.get(path).data
        self.assertEqual(len(asignaciones), 10)
        self.assertEqual(asignaciones[0]['cantidad_planificada'], '15.500')
        merma_path = f"{path}{asignaciones[0]['id']}/mermas/"
        merma = {'cantidad': '2.250', 'motivo': 'Corte'}
        response = self.api.post(merma_path, merma, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(self.api.get(path).data[0]['mermas'][0]['motivo'], 'Corte')
        self.assertEqual(self.api.post('/api/materiales/', {}, format='json').status_code, 403)
        hoy = timezone.localdate().isoformat()
        filtros = {'desde': hoy, 'hasta': hoy, 'actualizar': '1'}
        self.autenticar(self.gerencia)
        response = self.api.get('/api/dashboard/resumen/', filtros)
        self.assertEqual(response.status_code, 200, response.data)
        metrica = response.data['merma_materiales']
        self.assertEqual(metrica['obras_con_merma'], 1)
        self.assertEqual(Decimal(metrica['por_material'][0]['cantidad']), Decimal('2.250'))

        self.autenticar(self.finanzas)
        self.assertEqual(self.api.get('/api/materiales/').status_code, 403)
        self.assertEqual(self.api.get(path).status_code, 403)
        self.assertEqual(self.api.post(merma_path, merma, format='json').status_code, 403)
        self.assertNotIn('merma_materiales', self.api.get('/api/dashboard/resumen/', filtros).data)

    def test_saldo_por_asignacion_con_entradas_consumos_y_mermas(self):
        response = self.crear_con_materiales(self.materiales[:2])
        self.assertEqual(response.status_code, 201, response.data)
        path = f"/api/obras/{response.data['id']}/materiales/"
        primera, segunda = self.api.get(path).data
        self.assertIsNone(primera['saldo'])
        asignacion_path = f"{path}{primera['id']}/"
        movimiento_path = f'{asignacion_path}movimientos/'
        merma_path = f'{asignacion_path}mermas/'
        merma = {'cantidad': '2.250', 'motivo': 'Corte'}
        consumo = {'tipo': 'consumo', 'cantidad': '3.125', 'motivo': 'Instalación'}

        self.assertEqual(self.api.post(merma_path, merma, format='json').status_code, 201)
        self.assertEqual(self.api.post(movimiento_path, consumo, format='json').status_code, 400)
        entrada = {'tipo': 'entrada', 'cantidad': '15.500', 'motivo': 'Recepción'}
        response = self.api.post(movimiento_path, entrada, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['saldo'], '13.250')
        self.assertEqual(response.data['movimientos'][0]['registrado_por'], self.supervisor.pk)

        response = self.api.post(movimiento_path, consumo, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['saldo'], '10.125')
        response = self.api.post(merma_path, {**merma, 'cantidad': '10.126'}, format='json')
        self.assertEqual(response.status_code, 400, response.data)
        response = self.api.post(merma_path, {**merma, 'cantidad': '10.125'}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['saldo'], '0.000')
        self.assertEqual(self.api.post(movimiento_path, consumo, format='json').status_code, 400)
        saldos = {asignacion['id']: asignacion['saldo'] for asignacion in self.api.get(path).data}
        self.assertEqual(saldos, {primera['id']: '0.000', segunda['id']: None})
