from decimal import Decimal
import json

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .audit_context import get_current_request
from .models import AuditoriaLog, CategoriaServicio, Cliente, Contrato, CostoMaterial, Factura, NotaCredito, Obra, ObraEstadoHistorial, Pago, Presupuesto, ReversaPago, VersionPresupuesto


TRANSICIONES_OBRA = {
    'en-proceso': {'finalizada', 'suspendida', 'cancelada'},
    'suspendida': {'en-proceso', 'cancelada'},
    'finalizada': set(),
    'cancelada': set(),
}


def registrar_evento(*, usuario, modulo, accion, resultado, detalle, entidad='', entidad_id='', metadata=None, valores_anteriores=None, valores_nuevos=None, request=None):
    """Registra un evento sin incluir el cuerpo completo de la solicitud."""
    request = request or get_current_request()
    ip_address = request.META.get('REMOTE_ADDR') if request else None
    if request and getattr(settings, 'FYAG_TRUST_PROXY_HEADERS', False):
        forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
        if forwarded_for:
            ip_address = forwarded_for.split(',')[0].strip()
    user_agent = request.META.get('HTTP_USER_AGENT', '')[:512] if request else ''
    metadata_json = json.loads(json.dumps(metadata or {}, cls=DjangoJSONEncoder))
    anterior_json = json.loads(json.dumps(valores_anteriores or {}, cls=DjangoJSONEncoder))
    nuevos_json = json.loads(json.dumps(valores_nuevos or {}, cls=DjangoJSONEncoder))
    return AuditoriaLog.objects.create(
        usuario=usuario if getattr(usuario, 'is_authenticated', False) else None,
        modulo=modulo,
        accion=accion,
        resultado=resultado,
        detalle=str(detalle)[:4000],
        entidad=entidad,
        entidad_id=str(entidad_id or ''),
        metadata=metadata_json,
        ip_address=ip_address,
        user_agent=user_agent,
        valores_anteriores=anterior_json,
        valores_nuevos=nuevos_json,
    )


def guardar_con_actor(instance, usuario, campos):
    instance.updated_by = usuario
    instance.save(update_fields=[*campos, 'updated_by', 'updated_at'])


def actualizar_totales_presupuesto(presupuesto):
    partidas = presupuesto.items.filter(deleted_at__isnull=True)
    neto = sum((item.subtotal for item in partidas), Decimal('0'))
    iva = (neto * Decimal('0.19')).quantize(Decimal('1'))
    presupuesto.monto_neto = neto
    presupuesto.iva = iva
    presupuesto.monto_total = neto + iva
    presupuesto.save(update_fields=['monto_neto', 'iva', 'monto_total', 'updated_at'])


def snapshot_presupuesto(presupuesto):
    return {
        'numero_presupuesto': presupuesto.numero_presupuesto,
        'cliente_id': presupuesto.cliente_id,
        'contrato_id': presupuesto.contrato_id,
        'categoria_servicio_id': presupuesto.categoria_servicio_id,
        'contacto': presupuesto.contacto,
        'fecha_vencimiento': presupuesto.fecha_vencimiento.isoformat() if presupuesto.fecha_vencimiento else None,
        'monto_neto': str(presupuesto.monto_neto),
        'iva': str(presupuesto.iva),
        'monto_total': str(presupuesto.monto_total),
        'items': [
            {'descripcion': item.descripcion, 'cantidad': item.cantidad, 'unidad': item.unidad, 'precio_unitario': str(item.precio_unitario)}
            for item in presupuesto.items.filter(deleted_at__isnull=True).order_by('id')
        ],
    }


def guardar_version_presupuesto(presupuesto, usuario):
    ultima = presupuesto.historial_versiones.order_by('-numero_version').values_list('numero_version', flat=True).first() or 0
    return VersionPresupuesto.objects.create(
        presupuesto=presupuesto,
        numero_version=ultima + 1,
        snapshot=snapshot_presupuesto(presupuesto),
        usuario=usuario,
    )


@transaction.atomic
def decidir_aprobacion_gerencia(presupuesto, decision, usuario):
    if not presupuesto.requiere_aprobacion_gerencia or presupuesto.aprobacion_gerencia != 'pendiente':
        raise ValidationError({'error': 'TRANSICION_NO_PERMITIDA', 'detalle': 'Este presupuesto no está pendiente de aprobación de Gerencia.'})
    if decision not in {'aprobada', 'rechazada'}:
        raise ValidationError({'decision': 'Use aprobada o rechazada.'})
    presupuesto.aprobacion_gerencia = decision
    presupuesto.estado = 'enviado' if decision == 'aprobada' else 'borrador'
    guardar_con_actor(presupuesto, usuario, ['aprobacion_gerencia', 'estado'])
    registrar_evento(usuario=usuario, modulo='Presupuestos', accion=f'aprobacion_gerencia_{decision}', resultado='exito', detalle=f"Aprobación interna {decision} para {presupuesto.numero_presupuesto}.", entidad='Presupuesto', entidad_id=presupuesto.pk)
    return presupuesto


@transaction.atomic
def exigir_aprobacion_gerencia(presupuesto, usuario):
    if presupuesto.estado != 'borrador':
        raise ValidationError({'error': 'TRANSICION_NO_PERMITIDA', 'detalle': 'Gerencia solo puede exigir aprobación mientras el presupuesto esté en borrador.'})
    presupuesto.requiere_aprobacion_gerencia = True
    guardar_con_actor(presupuesto, usuario, ['requiere_aprobacion_gerencia'])
    registrar_evento(usuario=usuario, modulo='Presupuestos', accion='exigir_aprobacion_gerencia', resultado='exito', detalle=f'Gerencia solicitó aprobar {presupuesto.numero_presupuesto} antes del envío al cliente.', entidad='Presupuesto', entidad_id=presupuesto.pk)
    return presupuesto


@transaction.atomic
def enviar_presupuesto(presupuesto, usuario):
    if presupuesto.estado != 'borrador':
        raise ValidationError({'error': 'TRANSICION_NO_PERMITIDA', 'detalle': 'Solo se pueden enviar presupuestos en borrador.'})
    if not presupuesto.items.filter(deleted_at__isnull=True).exists():
        raise ValidationError({'error': 'DATOS_INCOMPLETOS', 'detalle': 'Agregue al menos una partida antes de enviar el presupuesto.'})
    if presupuesto.requiere_aprobacion_gerencia:
        presupuesto.estado = 'pendiente_gerencia'
        presupuesto.aprobacion_gerencia = 'pendiente'
        guardar_con_actor(presupuesto, usuario, ['estado', 'aprobacion_gerencia'])
    else:
        presupuesto.estado = 'enviado'
        guardar_con_actor(presupuesto, usuario, ['estado'])
    registrar_evento(usuario=usuario, modulo='Presupuestos', accion='enviar_presupuesto', resultado='exito', detalle=f"Presupuesto {presupuesto.numero_presupuesto} enviado al flujo correspondiente.", entidad='Presupuesto', entidad_id=presupuesto.pk)
    return presupuesto


@transaction.atomic
def registrar_decision_cliente(presupuesto, decision, usuario):
    if presupuesto.estado != 'enviado':
        raise ValidationError({'error': 'TRANSICION_NO_PERMITIDA', 'detalle': 'Solo se puede registrar la respuesta del cliente para un presupuesto enviado.'})
    if decision not in {'aprobado', 'rechazado'}:
        raise ValidationError({'decision': 'Use aprobado o rechazado.'})
    presupuesto.estado = decision
    presupuesto.fecha_decision_cliente = timezone.now()
    guardar_con_actor(presupuesto, usuario, ['estado', 'fecha_decision_cliente'])
    registrar_evento(usuario=usuario, modulo='Presupuestos', accion=f'decision_cliente_{decision}', resultado='exito', detalle=f"El cliente {decision} el presupuesto {presupuesto.numero_presupuesto}.", entidad='Presupuesto', entidad_id=presupuesto.pk)
    return presupuesto


@transaction.atomic
def transicionar_obra(obra, nuevo_estado, usuario, motivo=''):
    if nuevo_estado not in TRANSICIONES_OBRA.get(obra.estado_operativo, set()):
        raise ValidationError({'error': 'TRANSICION_NO_PERMITIDA', 'detalle': f"No se permite pasar de {obra.estado_operativo} a {nuevo_estado}."})
    if nuevo_estado == 'finalizada' and not obra.tecnico_responsable_id:
        raise ValidationError({'error': 'TECNICO_REQUERIDO', 'detalle': 'Asigne un técnico responsable antes de finalizar la obra.'})
    if nuevo_estado == 'cancelada' and Factura.objects.filter(obra=obra).exists():
        raise ValidationError({'error': 'FACTURAS_ASOCIADAS', 'detalle': 'No se puede cancelar una obra que ya tiene facturas emitidas, aunque todavía no estén pagadas.'})
    if nuevo_estado in {'suspendida', 'cancelada'} and not str(motivo).strip():
        raise ValidationError({'motivo': 'Indique el motivo de suspensión o cancelación.'})

    estado_anterior = obra.estado_operativo
    obra.estado_operativo = nuevo_estado
    fields = ['estado_operativo']
    if nuevo_estado == 'finalizada':
        obra.estado_comercial = 'pendiente_facturacion'
        obra.fecha_termino = timezone.localdate()
        fields.extend(['estado_comercial', 'fecha_termino'])
    guardar_con_actor(obra, usuario, fields)
    ObraEstadoHistorial.objects.create(obra=obra, estado_anterior=estado_anterior, estado_nuevo=nuevo_estado, usuario=usuario, observacion=str(motivo).strip())
    registrar_evento(usuario=usuario, modulo='Obras y Proyectos', accion='cambio_estado_obra', resultado='exito', detalle=f"La obra {obra.codigo_obra} cambió al estado {nuevo_estado}.", entidad='Obra', entidad_id=obra.pk, valores_anteriores={'estado_operativo': estado_anterior}, valores_nuevos={'estado_operativo': nuevo_estado, 'motivo': str(motivo).strip()})
    return obra


@transaction.atomic
def reabrir_obra(obra, usuario, motivo):
    if obra.estado_operativo not in {'finalizada', 'cancelada', 'suspendida'}:
        raise ValidationError({'error': 'TRANSICION_NO_PERMITIDA', 'detalle': 'Solo se pueden reabrir obras suspendidas o en estado terminal.'})
    if obra.estado_comercial == 'cerrada' or Factura.objects.filter(obra=obra).exists():
        raise ValidationError({'error': 'HISTORIAL_FINANCIERO', 'detalle': 'No se puede reabrir una obra con facturas emitidas o cierre comercial.'})
    if not str(motivo).strip():
        raise ValidationError({'motivo': 'Indique el motivo de reapertura.'})
    anterior = obra.estado_operativo
    obra.estado_operativo = 'en-proceso'
    obra.estado_comercial = 'en_curso'
    obra.fecha_termino = None
    obra.fecha_cierre_comercial = None
    guardar_con_actor(obra, usuario, ['estado_operativo', 'estado_comercial', 'fecha_termino', 'fecha_cierre_comercial'])
    ObraEstadoHistorial.objects.create(obra=obra, estado_anterior=anterior, estado_nuevo='en-proceso', usuario=usuario, observacion=f'Reapertura: {str(motivo).strip()}')
    registrar_evento(usuario=usuario, modulo='Obras y Proyectos', accion='reapertura_obra', resultado='exito', detalle=f'Se reabrió {obra.codigo_obra}: {str(motivo).strip()}', entidad='Obra', entidad_id=obra.pk, valores_anteriores={'estado_operativo': anterior}, valores_nuevos={'estado_operativo': 'en-proceso', 'motivo': str(motivo).strip()})
    return obra


@transaction.atomic
def cerrar_obra_comercial(obra, usuario):
    if obra.estado_operativo != 'finalizada':
        raise ValidationError({'error': 'OBRA_NO_FINALIZADA', 'detalle': 'La obra debe estar finalizada operativamente para cerrar su ciclo comercial.'})
    if obra.estado_comercial == 'cerrada':
        raise ValidationError({'error': 'OBRA_YA_CERRADA', 'detalle': 'La obra ya tiene su ciclo comercial cerrado.'})
    facturas = Factura.objects.filter(obra=obra)
    if not facturas.exists():
        raise ValidationError({'error': 'FACTURACION_PENDIENTE', 'detalle': 'Registre al menos una factura antes del cierre comercial.'})
    pendientes = facturas.filter(saldo_pendiente__gt=0)
    if pendientes.exists():
        saldo = sum((factura.saldo_pendiente for factura in facturas.filter(saldo_pendiente__gt=0)), Decimal('0'))
        raise ValidationError({'error': 'PAGOS_PENDIENTES', 'detalle': f'No se puede cerrar comercialmente la obra. Saldo pendiente: ${saldo:,.0f} CLP.'})
    obra.estado_comercial = 'cerrada'
    obra.fecha_cierre_comercial = timezone.now()
    guardar_con_actor(obra, usuario, ['estado_comercial', 'fecha_cierre_comercial'])
    registrar_evento(usuario=usuario, modulo='Obras y Proyectos', accion='cierre_comercial_obra', resultado='exito', detalle=f"Se cerró comercialmente la obra {obra.codigo_obra}.", entidad='Obra', entidad_id=obra.pk)
    return obra


@transaction.atomic
def registrar_pago(factura, datos, usuario):
    factura = Factura.objects.select_for_update().get(pk=factura.pk)
    monto = Decimal(str(datos['monto']))
    if monto <= 0:
        raise ValidationError({'monto': 'El monto debe ser mayor que cero.'})
    if monto > factura.saldo_pendiente:
        raise ValidationError({'monto': 'El pago supera el saldo pendiente de la factura.'})
    saldo_anterior = factura.saldo_pendiente
    estado_anterior = factura.estado_pago
    pago = Pago.objects.create(factura=factura, created_by=usuario, updated_by=usuario, **datos)
    factura.saldo_pendiente -= monto
    factura.estado_pago = 'PAGADO' if factura.saldo_pendiente == 0 else 'PARCIAL'
    guardar_con_actor(factura, usuario, ['saldo_pendiente', 'estado_pago'])

    obra = factura.obra
    facturas_activas = Factura.objects.filter(obra=obra)
    if facturas_activas.exists() and not facturas_activas.filter(saldo_pendiente__gt=0).exists():
        if obra.estado_operativo == 'finalizada' and obra.estado_comercial != 'cerrada':
            cerrar_obra_comercial(obra, usuario)
    elif obra.estado_operativo == 'finalizada':
        obra.estado_comercial = 'pendiente_cobro'
        guardar_con_actor(obra, usuario, ['estado_comercial'])

    registrar_evento(usuario=usuario, modulo='Facturación y Cobranza', accion='registrar_pago', resultado='exito', detalle=f"Pago registrado para factura {factura.numero_factura}.", entidad='Pago', entidad_id=pago.pk, valores_anteriores={'saldo_pendiente': saldo_anterior, 'estado_pago': estado_anterior}, valores_nuevos={'saldo_pendiente': factura.saldo_pendiente, 'estado_pago': factura.estado_pago, 'pago_id': pago.pk})
    return pago


@transaction.atomic
def registrar_nota_credito(factura, *, numero, monto, motivo, usuario):
    factura = Factura.objects.select_for_update().get(pk=factura.pk)
    monto = Decimal(str(monto))
    if monto <= 0 or monto > factura.saldo_pendiente:
        raise ValidationError({'monto': 'La nota de crédito debe ser positiva y no superar el saldo pendiente.'})
    saldo_anterior = factura.saldo_pendiente
    estado_anterior = factura.estado_pago
    nota = NotaCredito.objects.create(factura=factura, numero=numero, monto=monto, motivo=motivo, usuario=usuario)
    factura.saldo_pendiente -= monto
    factura.estado_pago = 'SALDADO' if factura.saldo_pendiente == 0 else 'PARCIAL'
    guardar_con_actor(factura, usuario, ['saldo_pendiente', 'estado_pago'])
    obra = factura.obra
    facturas_obra = Factura.objects.filter(obra=obra)
    if obra.estado_operativo == 'finalizada' and facturas_obra.exists() and not facturas_obra.filter(saldo_pendiente__gt=0).exists():
        if obra.estado_comercial != 'cerrada':
            cerrar_obra_comercial(obra, usuario)
    registrar_evento(usuario=usuario, modulo='Facturación y Cobranza', accion='emitir_nota_credito', resultado='exito', detalle=f'Nota de crédito {numero} registrada para {factura.numero_factura}.', entidad='NotaCredito', entidad_id=nota.pk, valores_anteriores={'saldo_pendiente': saldo_anterior, 'estado_pago': estado_anterior}, valores_nuevos={'saldo_pendiente': factura.saldo_pendiente, 'estado_pago': factura.estado_pago, 'nota_credito_id': nota.pk})
    return nota


@transaction.atomic
def revertir_pago(pago, *, monto, motivo, usuario):
    factura = Factura.objects.select_for_update().get(pk=pago.factura_id)
    monto = Decimal(str(monto))
    ya_revertido = pago.reversiones.aggregate(total=Sum('monto'))['total'] or Decimal('0')
    if monto <= 0 or ya_revertido + monto > pago.monto:
        raise ValidationError({'monto': 'La reversa debe ser positiva y no superar el monto aún vigente del pago.'})
    saldo_anterior = factura.saldo_pendiente
    estado_anterior = factura.estado_pago
    reversa = ReversaPago.objects.create(pago=pago, monto=monto, motivo=motivo, usuario=usuario)
    factura.saldo_pendiente += monto
    factura.estado_pago = 'PENDIENTE' if factura.saldo_pendiente == factura.monto_total else 'PARCIAL'
    guardar_con_actor(factura, usuario, ['saldo_pendiente', 'estado_pago'])
    obra = factura.obra
    if obra.estado_comercial == 'cerrada':
        obra.estado_comercial = 'pendiente_cobro'
        obra.fecha_cierre_comercial = None
        guardar_con_actor(obra, usuario, ['estado_comercial', 'fecha_cierre_comercial'])
    registrar_evento(usuario=usuario, modulo='Facturación y Cobranza', accion='reversa_pago', resultado='exito', detalle=f'Reversa de ${monto} registrada para el pago {pago.pk}.', entidad='ReversaPago', entidad_id=reversa.pk, valores_anteriores={'saldo_pendiente': saldo_anterior, 'estado_pago': estado_anterior}, valores_nuevos={'saldo_pendiente': factura.saldo_pendiente, 'estado_pago': factura.estado_pago, 'reversa_id': reversa.pk})
    return reversa


def soft_delete_instance(instance, usuario, valores_anteriores=None):
    if isinstance(instance, CostoMaterial) and (instance.obra.estado_operativo in {'finalizada', 'cancelada'} or instance.obra.estado_comercial == 'cerrada'):
        raise ValidationError({'error': 'OBRA_CERRADA', 'detalle': 'No se pueden modificar costos de una obra finalizada, cancelada o cerrada comercialmente.'})
    if isinstance(instance, Cliente) and (instance.contratos.exists() or instance.presupuestos.exists()):
        registrar_evento(usuario=usuario, modulo='Clientes y Contratos', accion='eliminacion_fallida', resultado='error', detalle=f'Cliente con historial asociado: {instance.razon_social}.', entidad='Cliente', entidad_id=instance.pk)
        raise ValidationError({'error': 'HISTORIAL_ASOCIADO', 'detalle': 'No se puede desactivar un cliente con contratos o presupuestos asociados.'})
    if isinstance(instance, Contrato) and instance.presupuestos.exists():
        registrar_evento(usuario=usuario, modulo='Clientes y Contratos', accion='eliminacion_fallida', resultado='error', detalle=f'Contrato asociado a presupuestos: {instance.numero_contrato}.', entidad='Contrato', entidad_id=instance.pk)
        raise ValidationError({'error': 'HISTORIAL_ASOCIADO', 'detalle': 'No se puede desactivar un contrato asociado a presupuestos.'})
    if isinstance(instance, CategoriaServicio) and (instance.presupuestos.exists() or instance.obras.exists()):
        registrar_evento(usuario=usuario, modulo='Categorías de servicio', accion='eliminacion_fallida', resultado='error', detalle=f'Categoría en uso: {instance.nombre}.', entidad='CategoriaServicio', entidad_id=instance.pk)
        raise ValidationError({'error': 'CATEGORIA_EN_USO', 'detalle': 'No se puede desactivar una categoría asociada a presupuestos u obras.'})
    if isinstance(instance, Factura) and (instance.pagos.exists() or instance.notas_credito.exists() or instance.saldo_pendiente > 0):
        raise ValidationError({'error': 'HISTORIAL_FINANCIERO', 'detalle': 'No se puede eliminar una factura con pagos o saldo pendiente.'})
    if isinstance(instance, Obra) and (instance.facturas.exists() or instance.costos.exists()):
        raise ValidationError({'error': 'HISTORIAL_FINANCIERO', 'detalle': 'No se puede eliminar una obra con facturas o gastos registrados.'})
    if isinstance(instance, Presupuesto) and hasattr(instance, 'obra'):
        raise ValidationError({'error': 'HISTORIAL_OPERATIVO', 'detalle': 'No se puede eliminar un presupuesto vinculado a una obra.'})
    if isinstance(instance, Pago):
        raise ValidationError({'error': 'PAGO_INMUTABLE', 'detalle': 'Los pagos registrados no se eliminan. Registre una corrección o reversa auditada.'})
    if isinstance(instance, Presupuesto):
        for item in instance.items.filter(deleted_at__isnull=True):
            item.updated_by = usuario
            item.soft_delete()
    if hasattr(instance, 'updated_by_id'):
        instance.updated_by = usuario
    instance.soft_delete()
    registrar_evento(usuario=usuario, modulo=instance._meta.verbose_name_plural, accion='eliminacion_logica', resultado='exito', detalle=f"Se marcó como eliminado el registro {instance}.", entidad=instance.__class__.__name__, entidad_id=instance.pk, valores_anteriores=valores_anteriores or {}, valores_nuevos={'deleted_at': instance.deleted_at.isoformat() if instance.deleted_at else None})
