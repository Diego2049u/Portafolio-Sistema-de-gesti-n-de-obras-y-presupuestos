from rest_framework.exceptions import ValidationError
from .models import Obra, Factura
from .models import Material, MovimientoBodega

def registrar_egreso_bodega(material_id, cantidad, obra_id, usuario):
    material = Material.objects.get(id=material_id)
    
    if material.stock_actual < cantidad:
        raise ValidationError({
            "error": "STOCK_INSUFICIENTE",
            "detalle": f"Stock insuficiente para {material.nombre}. Disponible: {material.stock_actual}, Solicitado: {cantidad}."
        })
    
    # Descontar stock y registrar movimiento
    material.stock_actual -= cantidad
    material.save()
    
    movimiento = MovimientoBodega.objects.create(
        material=material,
        obra_id=obra_id,
        tipo='EGRESO',
        cantidad=cantidad,
        responsable=usuario
    )
    
    # Alerta preventiva en consola o logs si queda en stock crítico
    alerta_critica = material.stock_actual <= material.stock_critico
    return movimiento, alerta_critica

def validar_cierre_obra(obra: Obra):
    """
    Regla RF-07: Comprueba que la obra no tenga facturas pendientes de cobro 
    o saldo pendiente antes de autorizar el estado 'finalizada'.
    """
    facturas_pendientes = Factura.objects.filter(
        obra=obra
    ).exclude(estado_pago='PAGADO')

    if facturas_pendientes.exists():
        total_saldo = sum(f.saldo_pendiente for f in facturas_pendientes)
        raise ValidationError({
            "error": "REGLA_RF07_VIOLADA",
            "detalle": f"No se puede finalizar la obra {obra.codigo_obra}. Existen facturas pendientes con un saldo exigible de ${total_saldo:,.0f} CLP."
        })
    return True