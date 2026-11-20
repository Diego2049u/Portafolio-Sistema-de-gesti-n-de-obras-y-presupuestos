from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless

from django.db import close_old_connections, connection
from django.test import TransactionTestCase
from rest_framework.test import APIClient

from .tests import FyagAPITestCase
from .disponibilidad import CHILE, evaluar, franjas


def fecha(texto):
    return datetime.fromisoformat(texto).replace(tzinfo=CHILE)


class DisponibilidadTests(FyagAPITestCase):
    def reservar(self, inicio='2026-11-16T08:00', fin='2026-11-18T18:00', tecnico=None, numero='RESERVA'):
        obra = self.crear_obra(presupuesto=self.crear_presupuesto(estado='aprobado', numero=numero), tecnico=tecnico or self.tecnico)
        obra.inicio_programado, obra.fin_estimado = fecha(inicio), fecha(fin)
        obra.save()
        return obra

    def payload(self, inicio, fin, numero='NUEVA'):
        presupuesto = self.crear_presupuesto(estado='aprobado', numero=numero)
        return {'presupuesto': presupuesto.pk, 'clasificacion_servicio': self.categoria.pk,
                'nombre_obra': numero, 'tecnico_responsable': self.tecnico.pk,
                'inicio_programado': inicio, 'fin_estimado': fin}

    def test_franjas_excluyen_colacion_y_fin_de_semana(self):
        bloques = list(franjas(fecha('2026-11-20T12:00'), fecha('2026-11-23T15:00')))
        self.assertEqual([(a.strftime('%a %H:%M'), b.strftime('%H:%M')) for a, b in bloques],
                         [('Fri 12:00', '13:00'), ('Fri 14:00', '18:00'), ('Mon 08:00', '13:00'), ('Mon 14:00', '15:00')])

    def test_asignacion_noviembre_diciembre_no_ocupa_enero_febrero(self):
        self.reservar('2026-11-16T08:00', '2026-12-31T18:00')
        self.autenticar(self.supervisor)
        r = self.api.post('/api/obras/', self.payload('2027-01-04T08:00', '2027-02-26T18:00'), format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['fecha_inicio'], '2027-01-04')

    def test_api_bloquea_cruce_aunque_se_omita_consulta_previa(self):
        self.reservar()
        self.autenticar(self.supervisor)
        r = self.api.post('/api/obras/', self.payload('2026-11-17T10:00', '2026-11-19T16:00'), format='json')
        self.assertEqual(r.status_code, 400)
        self.assertTrue(r.data['conflictos'])
        self.assertEqual(self.tecnico.obras_asignadas.count(), 1)

    def test_horas_contiguas_y_colacion_no_son_cruces(self):
        self.reservar('2026-11-16T08:00', '2026-11-16T13:00')
        self.autenticar(self.supervisor)
        r = self.api.post('/api/obras/', self.payload('2026-11-16T13:00', '2026-11-16T18:00'), format='json')
        self.assertEqual(r.status_code, 201, r.data)

    def test_rangos_invalidos_y_sin_jornada_se_rechazan(self):
        self.autenticar(self.supervisor)
        for i, (inicio, fin) in enumerate([('2026-11-16T18:00', '2026-11-16T08:00'),
                                         ('2026-11-21T08:00', '2026-11-22T18:00'),
                                         ('2026-11-16T13:00', '2026-11-16T14:00')]):
            r = self.api.post('/api/obras/', self.payload(inicio, fin, str(i)), format='json')
            self.assertEqual(r.status_code, 400, r.data)

    def test_tarjetas_disponible_parcial_y_ocupado(self):
        inicio, fin = fecha('2026-11-16T08:00'), fecha('2026-11-16T18:00')
        self.assertEqual(evaluar(self.tecnico.pk, inicio, fin)['estado'], 'disponible')
        obra = self.reservar('2026-11-16T08:00', '2026-11-16T13:00')
        self.assertEqual(evaluar(self.tecnico.pk, inicio, fin)['estado'], 'parcial')
        obra.fin_estimado = fin
        obra.save()
        self.assertEqual(evaluar(self.tecnico.pk, inicio, fin)['estado'], 'ocupado')

    def test_actualizar_excluye_la_propia_obra_pero_impide_otro_cruce(self):
        obra = self.reservar('2026-11-16T08:00', '2026-11-16T13:00')
        otra = self.reservar('2026-11-17T08:00', '2026-11-17T18:00', numero='OTRA')
        self.autenticar(self.supervisor)
        r = self.api.patch(f'/api/obras/{obra.pk}/', {'fin_estimado': '2026-11-16T18:00'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        r = self.api.patch(f'/api/obras/{obra.pk}/', {'fin_estimado': '2026-11-17T18:00'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertEqual(int(r.data['conflictos'][0]['obra_id']), otra.pk)

    def test_suspendida_libera_y_reanudar_revalida(self):
        obra = self.reservar()
        self.autenticar(self.supervisor)
        r = self.api.post(f'/api/obras/{obra.pk}/transicionar/', {'estado_operativo': 'suspendida', 'motivo': 'Pausa'}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(evaluar(self.tecnico.pk, fecha('2026-11-16T08:00'), fecha('2026-11-18T18:00'))['asignable'])
        self.reservar(numero='OTRA')
        r = self.api.post(f'/api/obras/{obra.pk}/transicionar/', {'estado_operativo': 'en-proceso'}, format='json')
        self.assertEqual(r.status_code, 400)
        obra.refresh_from_db()
        self.assertEqual(obra.estado_operativo, 'suspendida')

    def test_finalizadas_canceladas_y_eliminadas_no_reservan(self):
        obra = self.reservar()
        for estado in ['finalizada', 'cancelada']:
            obra.estado_operativo = estado
            obra.save()
            self.assertTrue(evaluar(self.tecnico.pk, fecha('2026-11-16T08:00'), fecha('2026-11-18T18:00'))['asignable'])
        obra.estado_operativo = 'en-proceso'
        obra.save()
        obra.soft_delete()
        self.assertTrue(evaluar(self.tecnico.pk, fecha('2026-11-16T08:00'), fecha('2026-11-18T18:00'))['asignable'])

    def test_obra_sin_planificar_no_se_interpreta_como_disponible(self):
        obra = self.crear_obra(tecnico=self.tecnico)
        resultado = evaluar(self.tecnico.pk, fecha('2027-01-04T08:00'), fecha('2027-01-04T18:00'))
        self.assertEqual(resultado['estado'], 'sin_determinar')
        self.assertFalse(resultado['asignable'])
        self.assertEqual(resultado['sin_planificar'][0]['id'], obra.pk)

    def test_agenda_respeta_fechas_y_no_expone_otros_tecnicos(self):
        obra = self.reservar()
        self.reservar(tecnico=self.otro_tecnico, numero='AJENA')
        self.autenticar(self.tecnico)
        params = {'desde': '2026-11-15', 'hasta': '2026-11-21', 'tecnico_id': self.otro_tecnico.pk}
        r = self.api.get('/api/obras/agenda-tecnico/', params)
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['tecnico']['id'], self.tecnico.pk)
        self.assertEqual(len(r.data['eventos']), 6)
        self.assertTrue(all(e['titulo'] == obra.nombre_obra for e in r.data['eventos']))
        params.update(desde='2027-01-01', hasta='2027-01-31')
        self.assertEqual(self.api.get('/api/obras/agenda-tecnico/', params).data['eventos'], [])
        self.assertEqual(self.api.get('/api/obras/tecnicos-disponibles/').status_code, 403)

    def test_rango_agenda_invalido(self):
        self.autenticar(self.tecnico)
        r = self.api.get('/api/obras/agenda-tecnico/', {'desde': 'mal', 'hasta': '2026-11-21'})
        self.assertEqual(r.status_code, 400)

    def test_consulta_disponibilidad_y_exclusion_de_obra_en_edicion(self):
        obra = self.reservar()
        self.autenticar(self.supervisor)
        params = {'inicio': '2026-11-17T08:00', 'fin': '2026-11-17T18:00'}
        r = self.api.get('/api/obras/tecnicos-disponibles/', params)
        self.assertEqual(r.status_code, 200, r.data)
        tecnico = next(t for t in r.data if t['id'] == self.tecnico.pk)
        self.assertFalse(tecnico['asignable'])
        self.assertEqual(tecnico['estado'], 'ocupado')
        params['excluir'] = obra.pk
        r = self.api.get('/api/obras/tecnicos-disponibles/', params)
        self.assertTrue(next(t for t in r.data if t['id'] == self.tecnico.pk)['asignable'])
        params['excluir'] = 'incorrecto'
        self.assertEqual(self.api.get('/api/obras/tecnicos-disponibles/', params).status_code, 400)

    def test_reasignar_a_otro_tecnico_valida_su_agenda(self):
        obra = self.reservar()
        self.reservar(tecnico=self.otro_tecnico, numero='OTRO')
        self.autenticar(self.supervisor)
        r = self.api.patch(f'/api/obras/{obra.pk}/', {'tecnico_responsable': self.otro_tecnico.pk}, format='json')
        self.assertEqual(r.status_code, 400)
        obra.refresh_from_db()
        self.assertEqual(obra.tecnico_responsable_id, self.tecnico.pk)


@skipUnless(connection.vendor == 'postgresql', 'Requiere bloqueos de fila de PostgreSQL')
class DisponibilidadConcurrenciaTests(TransactionTestCase):
    def test_dos_supervisores_no_reservan_el_mismo_tecnico_a_la_vez(self):
        supervisor = FyagAPITestCase.crear_usuario('supervisor-race', 'SUPERVISOR')
        tecnico = FyagAPITestCase.crear_usuario('tecnico-race', 'TECNICO')
        self.cliente = FyagAPITestCase.crear_cliente('CLI-RACE', '76123456-7')
        from .models import CategoriaServicio
        self.categoria = CategoriaServicio.objects.create(nombre='Concurrencia')
        presupuestos = [FyagAPITestCase.crear_presupuesto(self, numero=f'RACE-{i}', estado='aprobado') for i in range(2)]
        barrera = Barrier(2)

        def crear(presupuesto):
            close_old_connections()
            try:
                cliente = APIClient()
                cliente.force_authenticate(user=supervisor)
                barrera.wait(timeout=10)
                respuesta = cliente.post('/api/obras/', {
                    'presupuesto': presupuesto.pk, 'nombre_obra': f'Obra {presupuesto.pk}',
                    'clasificacion_servicio': self.categoria.pk, 'tecnico_responsable': tecnico.pk,
                    'inicio_programado': '2027-01-04T08:00', 'fin_estimado': '2027-02-26T18:00',
                }, format='json')
                return respuesta.status_code
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            resultados = list(executor.map(crear, presupuestos))
        self.assertEqual(sorted(resultados), [201, 400])
        self.assertEqual(tecnico.obras_asignadas.count(), 1)
