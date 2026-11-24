from django.utils import timezone

from .models import Material, Obra
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
        self.assertEqual(metrica['por_material'][0]['cantidad'], '2.250')

        self.autenticar(self.finanzas)
        self.assertEqual(self.api.get('/api/materiales/').status_code, 403)
        self.assertEqual(self.api.get(path).status_code, 403)
        self.assertEqual(self.api.post(merma_path, merma, format='json').status_code, 403)
        self.assertNotIn('merma_materiales', self.api.get('/api/dashboard/resumen/', filtros).data)
