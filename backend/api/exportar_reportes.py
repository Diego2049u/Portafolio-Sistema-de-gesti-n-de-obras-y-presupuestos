from datetime import date
from io import BytesIO
from xml.sax.saxutils import escape

import xlsxwriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import LongTable, Paragraph, SimpleDocTemplate, Spacer, TableStyle


AZUL = '#173B57'
GRIS_CLARO = '#F1F5F7'


def exportar_excel(titulo, periodo, columnas, filas):
    archivo = BytesIO()
    with xlsxwriter.Workbook(archivo, {
        'in_memory': True, 'strings_to_formulas': False, 'strings_to_urls': False,
    }) as libro:
        hoja = libro.add_worksheet('Reporte')
        titulo_estilo = libro.add_format({'bold': True, 'font_size': 16, 'font_color': AZUL})
        cabecera = libro.add_format({'bold': True, 'bg_color': AZUL, 'font_color': 'white'})
        fecha = libro.add_format({'num_format': 'dd-mm-yyyy'})
        moneda = libro.add_format({'num_format': '#,##0'})
        hoja.write(0, 0, titulo, titulo_estilo)
        hoja.write(1, 0, periodo)
        hoja.write_row(3, 0, columnas, cabecera)
        anchos = [len(columna) for columna in columnas]
        ultima = 3
        for ultima, fila in enumerate(filas, start=4):
            for indice, valor in enumerate(fila):
                if isinstance(valor, date):
                    hoja.write_datetime(ultima, indice, valor, fecha)
                elif isinstance(valor, int):
                    hoja.write_number(ultima, indice, valor, moneda)
                elif valor is not None:
                    hoja.write_string(ultima, indice, valor)
                anchos[indice] = max(anchos[indice], len(str(valor or '')))
        for indice, ancho in enumerate(anchos):
            hoja.set_column(indice, indice, min(48, max(13, ancho + 3)))
        hoja.autofilter(3, 0, ultima, len(columnas) - 1)
        hoja.freeze_panes(4, 0)
    archivo.seek(0)
    return archivo


def valor_pdf(valor):
    if isinstance(valor, date):
        return valor.strftime('%d-%m-%Y')
    if isinstance(valor, int):
        return f'{valor:,}'.replace(',', '.')
    return valor or ''


def exportar_pdf(titulo, periodo, columnas, filas):
    archivo = BytesIO()
    documento = SimpleDocTemplate(
        archivo, pagesize=landscape(letter), leftMargin=28, rightMargin=28,
        topMargin=28, bottomMargin=30, title=titulo, author='Frío y Agroindustria SpA',
    )
    titulo_estilo = ParagraphStyle('titulo', fontSize=18, leading=22, textColor=AZUL)
    normal = ParagraphStyle('normal', fontSize=9, leading=12)
    cuerpo = ParagraphStyle('cuerpo', fontSize=8, leading=10)
    cabecera = ParagraphStyle('cabecera', parent=cuerpo, fontName='Helvetica-Bold', textColor='white')
    tabla = [[Paragraph(escape(columna), cabecera) for columna in columnas]]
    tabla.extend([Paragraph(escape(valor_pdf(valor)), cuerpo) for valor in fila] for fila in filas)
    contenido = [
        Paragraph(escape(titulo), titulo_estilo),
        Spacer(1, 5),
        Paragraph('Frío y Agroindustria SpA · ' + escape(periodo), normal),
        Spacer(1, 12),
    ]
    if len(tabla) == 1:
        contenido.append(Paragraph('Sin registros para los filtros seleccionados.', normal))
    else:
        pesos = {'Obra': 1.4, 'Cliente': 1.6, 'Servicio': 1.4, 'Factura': 1.3, 'Código': 1.3, 'Folio': 1.3}
        anchos = [pesos.get(columna, 1) for columna in columnas]
        contenido.append(LongTable(
            tabla, colWidths=[(documento.width - 12) * ancho / sum(anchos) for ancho in anchos],
            repeatRows=1, hAlign='LEFT', style=TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(AZUL)),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor(GRIS_CLARO)]),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]),
        ))
    documento.build(contenido)
    archivo.seek(0)
    return archivo
