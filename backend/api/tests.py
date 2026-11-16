from datetime import date, timedelta
from decimal import Decimal
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from .models import (
    AuditoriaLog,
    CategoriaServicio,
    Cliente,
    Factura,
    ItemPresupuesto,
    Obra,
    Pago,
    Presupuesto,
    Usuario,
)


class FyagAPITestCase(APITestCase):
    """Fixtures comunes para probar permisos, workflows y trazabilidad vía API."""

    def setUp(self):
        self.gerencia = self.crear_usuario('gerencia', 'GERENCIA')
        self.finanzas = self.crear_usuario('finanzas', 'FINANZAS')
        self.supervisor = self.crear_usuario('supervisor', 'SUPERVISOR')
        self.tecnico = self.crear_usuario('tecnico', 'TECNICO')
        self.otro_tecnico = self.crear_usuario('otro-tecnico', 'TECNICO')
        self.categoria = CategoriaServicio.objects.create(nombre='Climatización', orden=1)
        self.cliente = self.crear_cliente('CLI-TEST-001', '76123456-7')
        self.api = APIClient()

    @staticmethod
    def crear_usuario(nombre, rol):
        return Usuario.objects.create_user(
            username=nombre,
            email=f'{nombre}@fyag.test',
            password='Test-Password-2026!',
            first_name=nombre.title(),
            rol=rol,
            estado='activo',
            is_active=True,
        )

    @staticmethod
    def crear_cliente(codigo, rut):
        return Cliente.objects.create(
            codigo_cliente=codigo,
            rut_cliente=rut,
            razon_social=f'Empresa {codigo} SpA',
            giro_comercial='Servicios industriales',
            direccion='Dirección de prueba',
            contacto_principal='Contacto de prueba',
            correo_contacto=f'{codigo.lower()}@example.test',
            telefono_contacto='+56 9 1111 2222',
        )

    def autenticar(self, usuario):
        self.api.force_authenticate(user=usuario)

    def crear_presupuesto(self, *, cliente=None, estado='borrador', monto=100000, numero='PRE-TEST-001'):
        return Presupuesto.objects.create(
            numero_presupuesto=numero,
            cliente=cliente or self.cliente,
            categoria_servicio=self.categoria,
            contacto='Contacto de prueba',
            monto_neto=monto,
            iva=round(monto * 0.19),
            monto_total=monto + round(monto * 0.19),
            estado=estado,
        )

    def crear_obra(self, *, presupuesto=None, tecnico=None, estado='en-proceso', comercial='en_curso'):
        presupuesto = presupuesto or self.crear_presupuesto(estado='aprobado')
        return Obra.objects.create(
            nombre_obra=f'Obra {presupuesto.numero_presupuesto}',
            presupuesto=presupuesto,
            tecnico_responsable=tecnico,
            clasificacion_servicio=self.categoria,
            estado_operativo=estado,
            estado_comercial=comercial,
        )

    @staticmethod
    def crear_factura(obra, *, total=50000, saldo=None, numero='FAC-TEST-001'):
        saldo = total if saldo is None else saldo
        return Factura.objects.create(
            numero_factura=numero,
            obra=obra,
            fecha_vencimiento=date.today() + timedelta(days=30),
            monto_neto=total,
            monto_total=total,
            saldo_pendiente=saldo,
            estado_pago='PENDIENTE' if saldo else 'PAGADO',
        )


class RolePermissionTests(FyagAPITestCase):
    def test_supervisor_puede_leer_clientes_pero_no_crearlos(self):
        self.autenticar(self.supervisor)

        listado = self.api.get('/api/clientes/')
        alta = self.api.post('/api/clientes/', {
            'codigo_cliente': 'CLI-DENEGADO',
            'rut_cliente': '76123456-8',
            'razon_social': 'Cliente no autorizado',
            'giro_comercial': 'Servicios',
            'contacto_principal': 'Contacto',
            'correo_contacto': 'contacto@example.test',
            'telefono_contacto': '+56 9 1111 2222',
        }, format='json')

        self.assertEqual(listado.status_code, status.HTTP_200_OK)
        self.assertEqual(alta.status_code, status.HTTP_403_FORBIDDEN)

    def test_finanzas_ve_presupuestos_y_supervisor_no(self):
        self.autenticar(self.finanzas)
        self.assertEqual(self.api.get('/api/presupuestos/').status_code, status.HTTP_200_OK)

        self.autenticar(self.supervisor)
        self.assertEqual(self.api.get('/api/presupuestos/').status_code, status.HTTP_403_FORBIDDEN)

    def test_tecnico_no_accede_a_modulos_financieros(self):
        self.autenticar(self.tecnico)

        for endpoint in ('/api/presupuestos/', '/api/costos/', '/api/facturas/', '/api/pagos/'):
            with self.subTest(endpoint=endpoint):
                self.assertEqual(self.api.get(endpoint).status_code, status.HTTP_403_FORBIDDEN)

    def test_tecnico_solo_recibe_sus_obras(self):
        propia = self.crear_obra(tecnico=self.tecnico)
        ajena = self.crear_obra(tecnico=self.otro_tecnico, presupuesto=self.crear_presupuesto(
            estado='aprobado', numero='PRE-TEST-002',
        ))
        self.autenticar(self.tecnico)

        response = self.api.get('/api/obras/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = {item['id'] for item in response.data['results']}
        self.assertIn(propia.pk, ids)
        self.assertNotIn(ajena.pk, ids)
        self.assertEqual(self.api.get(f'/api/obras/{ajena.pk}/').status_code, status.HTTP_404_NOT_FOUND)

    def test_dashboard_solo_gerencia_y_finanzas(self):
        self.autenticar(self.finanzas)
        self.assertEqual(self.api.get('/api/dashboard/resumen/').status_code, status.HTTP_200_OK)

        self.autenticar(self.supervisor)
        self.assertEqual(self.api.get('/api/dashboard/resumen/').status_code, status.HTTP_403_FORBIDDEN)

    def test_auditoria_solo_gerencia(self):
        self.autenticar(self.finanzas)
        self.assertEqual(self.api.get('/api/auditoria/').status_code, status.HTTP_403_FORBIDDEN)

        self.autenticar(self.gerencia)
        self.assertEqual(self.api.get('/api/auditoria/').status_code, status.HTTP_200_OK)


class PresupuestoWorkflowTests(FyagAPITestCase):
    def test_no_se_puede_enviar_presupuesto_sin_partidas(self):
        presupuesto = self.crear_presupuesto()
        self.autenticar(self.finanzas)

        response = self.api.post(f'/api/presupuestos/{presupuesto.pk}/enviar/', {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'DATOS_INCOMPLETOS')
        presupuesto.refresh_from_db()
        self.assertEqual(presupuesto.estado, 'borrador')

    def test_aprobacion_interna_y_decision_cliente_siguen_el_orden_acordado(self):
        presupuesto = self.crear_presupuesto()
        ItemPresupuesto.objects.create(
            presupuesto=presupuesto,
            descripcion='Servicio técnico',
            cantidad=1,
            unidad='un',
            precio_unitario=Decimal('100000'),
        )

        self.autenticar(self.gerencia)
        requerir = self.api.post(
            f'/api/presupuestos/{presupuesto.pk}/exigir-aprobacion-gerencia/', {}, format='json',
        )
        self.assertEqual(requerir.status_code, status.HTTP_200_OK)

        self.autenticar(self.finanzas)
        enviar = self.api.post(f'/api/presupuestos/{presupuesto.pk}/enviar/', {}, format='json')
        self.assertEqual(enviar.status_code, status.HTTP_200_OK)
        self.assertEqual(enviar.data['estado'], 'pendiente_gerencia')

        self.autenticar(self.gerencia)
        aprobar_interno = self.api.post(
            f'/api/presupuestos/{presupuesto.pk}/aprobar-gerencia/',
            {'decision': 'aprobada'}, format='json',
        )
        self.assertEqual(aprobar_interno.status_code, status.HTTP_200_OK)
        self.assertEqual(aprobar_interno.data['estado'], 'enviado')

        self.autenticar(self.finanzas)
        decision_cliente = self.api.post(
            f'/api/presupuestos/{presupuesto.pk}/decision-cliente/',
            {'decision': 'aprobado'}, format='json',
        )
        self.assertEqual(decision_cliente.status_code, status.HTTP_200_OK)
        self.assertEqual(decision_cliente.data['estado'], 'aprobado')

    def test_presupuesto_rechazado_por_cliente_no_se_puede_editar(self):
        presupuesto = self.crear_presupuesto(estado='rechazado')
        self.autenticar(self.finanzas)

        response = self.api.patch(
            f'/api/presupuestos/{presupuesto.pk}/', {'contacto': 'Cambio'}, format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ObraWorkflowTests(FyagAPITestCase):
    def test_no_se_finaliza_obra_sin_tecnico(self):
        obra = self.crear_obra()
        self.autenticar(self.supervisor)

        response = self.api.post(
            f'/api/obras/{obra.pk}/transicionar/', {'estado_operativo': 'finalizada'}, format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'TECNICO_REQUERIDO')

    def test_finalizar_obra_no_depende_del_cobro_y_registra_historial(self):
        obra = self.crear_obra(tecnico=self.tecnico)
        self.crear_factura(obra)
        self.autenticar(self.supervisor)

        response = self.api.post(
            f'/api/obras/{obra.pk}/transicionar/', {'estado_operativo': 'finalizada'}, format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        obra.refresh_from_db()
        self.assertEqual(obra.estado_operativo, 'finalizada')
        self.assertEqual(obra.estado_comercial, 'pendiente_facturacion')
        self.assertEqual(obra.historial_estados.count(), 1)

    def test_no_se_cancela_obra_con_factura_pendiente(self):
        obra = self.crear_obra(tecnico=self.tecnico)
        self.crear_factura(obra)
        self.autenticar(self.supervisor)

        response = self.api.post(
            f'/api/obras/{obra.pk}/transicionar/',
            {'estado_operativo': 'cancelada', 'motivo': 'Solicitud de prueba'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'FACTURAS_ASOCIADAS')

    def test_cierre_comercial_rechaza_facturas_con_saldo(self):
        obra = self.crear_obra(tecnico=self.tecnico, estado='finalizada', comercial='pendiente_cobro')
        self.crear_factura(obra)
        self.autenticar(self.finanzas)

        response = self.api.post(f'/api/obras/{obra.pk}/cerrar-comercial/', {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'PAGOS_PENDIENTES')


class FacturacionWorkflowTests(FyagAPITestCase):
    def test_facturas_acumuladas_no_superan_el_presupuesto(self):
        presupuesto = self.crear_presupuesto(estado='aprobado', monto=90000)
        obra = self.crear_obra(presupuesto=presupuesto, tecnico=self.tecnico, estado='finalizada', comercial='pendiente_facturacion')
        self.crear_factura(obra, total=50000)
        self.autenticar(self.finanzas)

        response = self.api.post('/api/facturas/', {
            'obra': obra.pk,
            'fecha_vencimiento': (date.today() + timedelta(days=30)).isoformat(),
            'monto_neto': '60000',
            'monto_total': '60000',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('monto_total', response.data)
        self.assertEqual(Factura.objects.filter(obra=obra).count(), 1)

    def test_pago_mayor_al_saldo_se_rechaza_sin_alterar_factura(self):
        obra = self.crear_obra(tecnico=self.tecnico, estado='finalizada', comercial='pendiente_cobro')
        factura = self.crear_factura(obra, total=50000)
        self.autenticar(self.finanzas)

        response = self.api.post('/api/pagos/', {
            'factura': factura.pk,
            'monto': '50001',
            'fecha_pago': date.today().isoformat(),
            'metodo_pago': 'Transferencia',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        factura.refresh_from_db()
        self.assertEqual(factura.saldo_pendiente, Decimal('50000'))
        self.assertFalse(Pago.objects.filter(factura=factura).exists())

    def test_pago_total_cierra_la_obra_y_crea_evento_auditable(self):
        obra = self.crear_obra(tecnico=self.tecnico, estado='finalizada', comercial='pendiente_cobro')
        factura = self.crear_factura(obra, total=50000)
        self.autenticar(self.finanzas)
        self.api.defaults['REMOTE_ADDR'] = '192.0.2.10'
        self.api.defaults['HTTP_USER_AGENT'] = 'FYAG API test'

        response = self.api.post('/api/pagos/', {
            'factura': factura.pk,
            'monto': '50000',
            'fecha_pago': date.today().isoformat(),
            'metodo_pago': 'Transferencia',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        obra.refresh_from_db()
        factura.refresh_from_db()
        self.assertEqual(factura.saldo_pendiente, Decimal('0'))
        self.assertEqual(factura.estado_pago, 'PAGADO')
        self.assertEqual(obra.estado_comercial, 'cerrada')
        evento = AuditoriaLog.objects.get(entidad='Pago', entidad_id=str(response.data['id']))
        self.assertEqual(evento.resultado, 'exito')
        self.assertEqual(evento.usuario_id, self.finanzas.pk)
        self.assertEqual(evento.ip_address, '192.0.2.10')
        self.assertEqual(evento.user_agent, 'FYAG API test')
        self.assertIn('saldo_pendiente', evento.valores_anteriores)
        self.assertIn('saldo_pendiente', evento.valores_nuevos)

    def test_pago_no_admite_edicion_ni_eliminacion(self):
        obra = self.crear_obra(tecnico=self.tecnico, estado='finalizada', comercial='pendiente_cobro')
        factura = self.crear_factura(obra)
        pago = Pago.objects.create(
            factura=factura,
            monto=Decimal('1000'),
            fecha_pago=date.today(),
            metodo_pago='Transferencia',
        )
        self.autenticar(self.finanzas)

        editar = self.api.patch(f'/api/pagos/{pago.pk}/', {'monto': '500'}, format='json')
        borrar = self.api.delete(f'/api/pagos/{pago.pk}/')

        self.assertEqual(editar.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(borrar.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class AuditTrailTests(FyagAPITestCase):
    def test_alta_de_cliente_registra_actor_ip_user_agent_y_snapshot(self):
        self.autenticar(self.finanzas)
        self.api.defaults['REMOTE_ADDR'] = '192.0.2.20'
        self.api.defaults['HTTP_USER_AGENT'] = 'FYAG audit test'

        response = self.api.post('/api/clientes/', {
            'codigo_cliente': 'CLI-AUDIT-001',
            'rut_cliente': '76123456-9',
            'razon_social': 'Cliente auditado SpA',
            'giro_comercial': 'Servicios',
            'contacto_principal': 'Contacto de auditoría',
            'correo_contacto': 'auditoria@example.test',
            'telefono_contacto': '+56 9 2222 3333',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        evento = AuditoriaLog.objects.get(entidad='Cliente', entidad_id=str(response.data['id']))
        self.assertEqual(evento.resultado, 'exito')
        self.assertEqual(evento.usuario_id, self.finanzas.pk)
        self.assertEqual(evento.ip_address, '192.0.2.20')
        self.assertEqual(evento.user_agent, 'FYAG audit test')
        self.assertEqual(evento.valores_nuevos['razon_social'], 'Cliente auditado SpA')

    def test_eventos_de_auditoria_no_se_pueden_editar_ni_eliminar(self):
        evento = AuditoriaLog.objects.create(
            usuario=self.gerencia,
            modulo='Pruebas',
            accion='evento_prueba',
            resultado='exito',
            detalle='Evento inmutable',
        )

        with self.assertRaises(ValueError):
            evento.save(update_fields=['detalle'])
        with self.assertRaises(ValueError):
            AuditoriaLog.objects.filter(pk=evento.pk).update(detalle='Alterado')
        with self.assertRaises(ValueError):
            evento.delete()

    def test_borrado_logico_masivo_es_atomico_si_un_registro_no_se_puede_borrar(self):
        eliminable = self.crear_cliente('CLI-BULK-001', '76123456-1')
        protegido = self.crear_cliente('CLI-BULK-002', '76123456-2')
        self.crear_presupuesto(cliente=protegido, numero='PRE-BULK-001')

        with self.assertRaises(DjangoValidationError):
            Cliente.objects.filter(pk__in=[eliminable.pk, protegido.pk]).order_by('pk').delete()

        eliminable.refresh_from_db()
        protegido.refresh_from_db()
        self.assertIsNone(eliminable.deleted_at)
        self.assertIsNone(protegido.deleted_at)


class AuthenticationSecurityTests(FyagAPITestCase):
    def test_login_exige_csrf_y_emite_cookie_httponly_de_15_minutos(self):
        self.api = APIClient(enforce_csrf_checks=True)
        credenciales = {'email': self.finanzas.email, 'password': 'Test-Password-2026!'}

        sin_csrf = self.api.post('/api/auth/login/', credenciales, format='json')
        self.assertEqual(sin_csrf.status_code, status.HTTP_403_FORBIDDEN)

        csrf = self.api.get('/api/auth/csrf/')
        login = self.api.post(
            '/api/auth/login/',
            credenciales,
            format='json',
            HTTP_X_CSRFTOKEN=csrf.data['csrfToken'],
        )

        self.assertEqual(login.status_code, status.HTTP_200_OK)
        access_cookie = login.cookies['fyag_access']
        self.assertTrue(access_cookie['httponly'])
        self.assertEqual(access_cookie['max-age'], '900')
        self.assertEqual(login.data['user']['role'], 'FINANZAS')
