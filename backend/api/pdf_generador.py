from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


AZUL = colors.HexColor('#173B57')
GRIS = colors.HexColor('#5B6870')
FONDO = colors.HexColor('#F1F5F7')
LOGO_PATH = Path(__file__).resolve().parents[2] / 'frontend' / 'src' / 'assets' / 'flyag-logo-pag.png'


def _clp(value):
    return f"${int(value or 0):,}".replace(',', '.')


def generar_pdf_presupuesto(presupuesto):
    """Genera una cotización paginada con datos y partidas vigentes del presupuesto."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=34 * mm,
        bottomMargin=22 * mm,
        title=f'Presupuesto {presupuesto.numero_presupuesto}',
        author='Frío y Agroindustria SpA',
        subject='Cotización de servicios y obras',
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='FYAGTitle', parent=styles['Title'], textColor=AZUL, fontName='Helvetica-Bold', fontSize=17, leading=21, alignment=TA_LEFT, spaceAfter=3 * mm))
    styles.add(ParagraphStyle(name='FYAGSection', parent=styles['Heading2'], textColor=AZUL, fontName='Helvetica-Bold', fontSize=10, leading=13, spaceBefore=4 * mm, spaceAfter=2 * mm))
    styles.add(ParagraphStyle(name='FYAGBody', parent=styles['BodyText'], fontName='Helvetica', fontSize=9, leading=12, textColor=colors.HexColor('#263238')))
    styles.add(ParagraphStyle(name='FYAGSmall', parent=styles['BodyText'], fontName='Helvetica', fontSize=8, leading=10, textColor=GRIS))
    styles.add(ParagraphStyle(name='FYAGRight', parent=styles['BodyText'], fontName='Helvetica', fontSize=9, leading=12, alignment=TA_RIGHT))
    story = []
    story.append(Paragraph('Presupuesto / Cotización', styles['FYAGTitle']))
    story.append(Paragraph('Frío y Agroindustria SpA · Gestión de obras y servicios', styles['FYAGBody']))
    story.append(Spacer(1, 4 * mm))

    client = presupuesto.cliente
    details = [
        [Paragraph('<b>Folio</b>', styles['FYAGBody']), Paragraph(str(presupuesto.numero_presupuesto), styles['FYAGBody']), Paragraph('<b>Fecha de emisión</b>', styles['FYAGBody']), Paragraph(presupuesto.fecha_emision.strftime('%d-%m-%Y'), styles['FYAGBody'])],
        [Paragraph('<b>Cliente</b>', styles['FYAGBody']), Paragraph(client.razon_social, styles['FYAGBody']), Paragraph('<b>RUT</b>', styles['FYAGBody']), Paragraph(client.rut_cliente, styles['FYAGBody'])],
        [Paragraph('<b>Contacto</b>', styles['FYAGBody']), Paragraph(presupuesto.contacto, styles['FYAGBody']), Paragraph('<b>Servicio</b>', styles['FYAGBody']), Paragraph(presupuesto.categoria_servicio.nombre, styles['FYAGBody'])],
    ]
    if presupuesto.fecha_vencimiento:
        details.append([Paragraph('<b>Válido hasta</b>', styles['FYAGBody']), Paragraph(presupuesto.fecha_vencimiento.strftime('%d-%m-%Y'), styles['FYAGBody']), '', ''])
    if presupuesto.contrato_id:
        details.append([Paragraph('<b>Contrato</b>', styles['FYAGBody']), Paragraph(presupuesto.contrato.numero_contrato, styles['FYAGBody']), Paragraph('<b>Nombre</b>', styles['FYAGBody']), Paragraph(presupuesto.contrato.nombre, styles['FYAGBody'])])
    info = Table(details, colWidths=[27 * mm, 65 * mm, 32 * mm, 50 * mm])
    info.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), FONDO), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 7), ('RIGHTPADDING', (0, 0), (-1, -1), 7),
        ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('BOX', (0, 0), (-1, -1), .5, colors.HexColor('#D4DEE3')),
    ]))
    story.extend([info, Paragraph('Detalle de partidas', styles['FYAGSection'])])

    cell = styles['FYAGBody']
    right = styles['FYAGRight']
    data = [[Paragraph('<b>Descripción</b>', cell), Paragraph('<b>Cantidad</b>', right), Paragraph('<b>Unidad</b>', cell), Paragraph('<b>Precio unitario</b>', right), Paragraph('<b>Subtotal</b>', right)]]
    for item in presupuesto.items.filter(deleted_at__isnull=True).order_by('id'):
        data.append([
            Paragraph(item.descripcion.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br/>'), cell),
            Paragraph(str(item.cantidad), right),
            Paragraph(item.unidad, cell),
            Paragraph(_clp(item.precio_unitario), right),
            Paragraph(_clp(item.subtotal), right),
        ])
    if len(data) == 1:
        data.append([Paragraph('Sin partidas registradas', cell), '', '', '', ''])
    items = Table(data, colWidths=[76 * mm, 20 * mm, 18 * mm, 30 * mm, 30 * mm], repeatRows=1, hAlign='LEFT')
    items.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), AZUL), ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('GRID', (0, 0), (-1, -1), .35, colors.HexColor('#D4DEE3')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, FONDO]),
        ('LEFTPADDING', (0, 0), (-1, -1), 6), ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(items)

    totals = [
        [Paragraph('Monto neto', cell), Paragraph(_clp(presupuesto.monto_neto), right)],
        [Paragraph('IVA', cell), Paragraph(_clp(presupuesto.iva), right)],
        [Paragraph('<b>Total cotizado (CLP)</b>', cell), Paragraph(f'<b>{_clp(presupuesto.monto_total)}</b>', right)],
    ]
    summary = Table(totals, colWidths=[45 * mm, 38 * mm], hAlign='RIGHT')
    summary.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (-1, 0), .8, AZUL), ('BACKGROUND', (0, 2), (-1, 2), FONDO),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'), ('LEFTPADDING', (0, 0), (-1, -1), 7),
        ('RIGHTPADDING', (0, 0), (-1, -1), 7), ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.extend([Spacer(1, 3 * mm), summary])
    if client.direccion:
        story.extend([Paragraph('Dirección del cliente', styles['FYAGSection']), Paragraph(client.direccion, styles['FYAGBody'])])
    story.extend([Spacer(1, 8 * mm), Paragraph('Este documento presenta el alcance y los valores registrados en el sistema para este presupuesto.', styles['FYAGSmall'])])

    def draw_page(canvas, document):
        canvas.saveState()
        width, height = letter
        canvas.setFillColor(AZUL)
        canvas.rect(0, height - 9 * mm, width, 9 * mm, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.setFont('Helvetica-Bold', 9)
        canvas.drawString(18 * mm, height - 6 * mm, 'FYAG · FRÍO Y AGROINDUSTRIA SpA')
        if LOGO_PATH.is_file():
            canvas.drawImage(str(LOGO_PATH), 18 * mm, height - 32 * mm, width=38 * mm, height=24 * mm, preserveAspectRatio=True, anchor='sw', mask='auto')
        canvas.setStrokeColor(colors.HexColor('#D4DEE3'))
        canvas.line(18 * mm, 16 * mm, width - 18 * mm, 16 * mm)
        canvas.setFillColor(GRIS)
        canvas.setFont('Helvetica', 8)
        canvas.drawString(18 * mm, 11 * mm, str(presupuesto.numero_presupuesto))
        canvas.drawRightString(width - 18 * mm, 11 * mm, f'Página {document.page}')
        canvas.restoreState()

    doc.build(story, onFirstPage=draw_page, onLaterPages=draw_page)
    buffer.seek(0)
    return buffer
