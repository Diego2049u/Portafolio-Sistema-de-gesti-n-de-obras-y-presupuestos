# api/pdf_generator.py
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors

def generar_pdf_presupuesto(presupuesto):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    
    # Encabezado Institucional FYAG SpA
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, 750, "FYAG SpA - FRÍO Y AGROINDUSTRIA")
    p.setFont("Helvetica", 10)
    p.drawString(50, 735, "Cotización Comercial e Ingeniería de Proyectos")
    
    p.setFont("Helvetica-Bold", 12)
    p.drawString(400, 750, f"Folio: {presupuesto.numero_presupuesto}")
    p.drawString(400, 735, f"Fecha: {presupuesto.fecha_emision}")
    
    p.setStrokeColor(colors.gray)
    p.line(50, 720, 550, 720)
    
    # Datos del Cliente
    p.setFont("Helvetica-Bold", 11)
    p.drawString(50, 695, "INFORMACIÓN DEL CLIENTE MANDANTE:")
    p.setFont("Helvetica", 10)
    p.drawString(50, 680, f"Razón Social: {presupuesto.cliente.razon_social}")
    p.drawString(50, 665, f"RUT: {presupuesto.cliente.rut_cliente}")
    p.drawString(50, 650, f"Contacto: {presupuesto.contacto}")
    p.drawString(50, 635, f"Servicio: {presupuesto.categoria_servicio}")
    
    # Resumen Financiero
    p.line(50, 615, 550, 615)
    p.setFont("Helvetica-Bold", 11)
    p.drawString(50, 595, "RESUMEN MONETARIO (CLP):")
    p.setFont("Helvetica", 10)
    p.drawString(50, 575, f"Monto Neto: ${presupuesto.monto_neto:,.0f} CLP")
    p.drawString(50, 560, f"IVA (19%): ${presupuesto.iva:,.0f} CLP")
    
    p.setFont("Helvetica-Bold", 12)
    p.setFillColor(colors.HexColor("#003366"))
    p.drawString(50, 535, f"TOTAL COTIZADO: ${presupuesto.monto_total:,.0f} CLP")
    
    # Pie de página
    p.setFillColor(colors.black)
    p.setFont("Helvetica-Oblique", 8)
    p.drawString(50, 50, "Documento generado por el ERP FYAG SpA. Válido por 30 días.")
    
    p.showPage()
    p.save()
    
    buffer.seek(0)
    return buffer