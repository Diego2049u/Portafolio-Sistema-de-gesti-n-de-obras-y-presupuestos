from io import BytesIO
from xml.etree import ElementTree
from zipfile import ZipFile

from django.utils import timezone

from .tests import FyagAPITestCase


class ReportesTests(FyagAPITestCase):
    ruta = '/api/reportes/'

    def test_acceso_por_rol_incluso_al_descargar(self):
        for usuario, codigo in (
            (self.administrador, 200), (self.gerencia, 200),
            (self.supervisor, 403), (self.tecnico, 403),
        ):
            self.autenticar(usuario)
            with self.subTest(rol=usuario.rol):
                self.assertEqual(self.api.get(f'{self.ruta}filtros/').status_code, codigo)
                for salida in ('vista', 'xlsx', 'pdf'):
                    respuesta = self.api.get(self.ruta, {'salida': salida})
                    self.assertEqual(respuesta.status_code, codigo)
                    if respuesta.streaming:
                        self.assertTrue(b''.join(respuesta.streaming_content))

    def test_finanzas_solo_consulta_y_exporta_cobranza(self):
        obra = self.crear_obra(estado='finalizada')
        factura = self.crear_factura(obra)
        self.autenticar(self.finanzas)

        filtros = self.api.get(f'{self.ruta}filtros/')
        self.assertEqual(filtros.status_code, 200)
        self.assertEqual([tipo['id'] for tipo in filtros.data['tipos']], ['cobranza'])

        vista = self.api.get(self.ruta)
        self.assertEqual(vista.status_code, 200)
        self.assertEqual(vista.data['results']['filas'][0][0], factura.numero_factura)
        for salida in ('vista', 'xlsx', 'pdf'):
            for tipo in ('obras', 'presupuestos'):
                self.assertEqual(self.api.get(self.ruta, {'tipo': tipo, 'salida': salida}).status_code, 403)
        for salida, firma in (('xlsx', b'PK'), ('pdf', b'%PDF-')):
            archivo = self.api.get(self.ruta, {'tipo': 'cobranza', 'salida': salida})
            self.assertEqual(archivo.status_code, 200)
            self.assertIn(f'reporte-cobranza.{salida}', archivo['Content-Disposition'])
            self.assertTrue(b''.join(archivo.streaming_content).startswith(firma))

    def test_filtros_y_archivos_con_datos_limpios_y_tipados(self):
        self.cliente.razon_social = '=Climatizacio\u0301n\u200b & Hijos\tSpA'
        self.cliente.save(update_fields=['razon_social'])
        obra = self.crear_obra(tecnico=self.tecnico, estado='finalizada')
        obra.fecha_inicio = timezone.localdate()
        obra.save(update_fields=['fecha_inicio'])
        factura = self.crear_factura(obra, total=50000)
        self.autenticar(self.gerencia)
        filtros = {
            'tipo': 'cobranza', 'desde': factura.fecha_emision, 'hasta': factura.fecha_emision,
            'cliente_id': self.cliente.pk, 'tecnico_id': self.tecnico.pk, 'estado': 'PENDIENTE',
        }
        vista = self.api.get(self.ruta, filtros)
        self.assertEqual(vista.data['count'], 1)
        fila = vista.data['results']['filas'][0]
        self.assertEqual(fila[2], '=Climatización & Hijos SpA')
        self.assertEqual(fila[-1], 50000)
        for cambio in (
            {'cliente_id': self.cliente.pk + 1}, {'tecnico_id': self.otro_tecnico.pk}, {'estado': 'PAGADO'},
        ):
            self.assertEqual(self.api.get(self.ruta, {**filtros, **cambio}).data['count'], 0)
        self.assertEqual(self.api.get(self.ruta, {**filtros, 'estado': 'finalizada'}).status_code, 400)
        for tipo, estado in (('obras', 'finalizada'), ('presupuestos', 'aprobado')):
            vista = self.api.get(self.ruta, {**filtros, 'tipo': tipo, 'estado': estado})
            self.assertEqual(vista.data['count'], 1)

        excel = self.api.get(self.ruta, {**filtros, 'salida': 'xlsx'})
        self.assertIn('reporte-cobranza.xlsx', excel['Content-Disposition'])
        with ZipFile(BytesIO(b''.join(excel.streaming_content))) as archivo:
            textos = archivo.read('xl/sharedStrings.xml').decode('utf-8')
            self.assertIn('=Climatización &amp; Hijos SpA', textos)
            self.assertNotIn('\u200b', textos)
            ns = {'x': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
            tabla = ElementTree.fromstring(archivo.read('xl/worksheets/sheet1.xml'))
            self.assertIsNone(tabla.find('.//x:f', ns))
            self.assertEqual(tabla.find(".//x:c[@r='I5']/x:v", ns).text, '50000')
            self.assertEqual(tabla.find(".//x:c[@r='C5']", ns).attrib['t'], 's')
            self.assertIn('s', tabla.find(".//x:c[@r='E5']", ns).attrib)

        pdf = self.api.get(self.ruta, {**filtros, 'salida': 'pdf'})
        self.assertIn('reporte-cobranza.pdf', pdf['Content-Disposition'])
        self.assertTrue(b''.join(pdf.streaming_content).startswith(b'%PDF-'))
