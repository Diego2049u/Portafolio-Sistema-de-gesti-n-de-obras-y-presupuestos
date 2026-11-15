from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncMonth
from datetime import timedelta
from django.utils import timezone

from .models import CostoMaterial, Factura, NotaCredito, Obra, Pago, Presupuesto, ReversaPago


ESTADOS_PENDIENTES_PRESUPUESTO = ('pendiente_gerencia', 'enviado')


def construir_resumen_dashboard(*, desde, hasta, cliente_id=None, tecnico_id=None, estado_obra=None):
    """Calcula indicadores del MVP desde datos activos, aplicando filtros de obra."""
    obras_sin_estado = Obra.objects.select_related('clasificacion_servicio', 'presupuesto__cliente')
    if cliente_id:
        obras_sin_estado = obras_sin_estado.filter(presupuesto__cliente_id=cliente_id)
    if tecnico_id:
        obras_sin_estado = obras_sin_estado.filter(tecnico_responsable_id=tecnico_id)
    obras = obras_sin_estado
    if estado_obra:
        obras = obras.filter(estado_operativo=estado_obra)

    presupuestos = Presupuesto.objects.all()
    if cliente_id:
        presupuestos = presupuestos.filter(cliente_id=cliente_id)
    if tecnico_id or estado_obra:
        presupuestos = presupuestos.filter(pk__in=obras.values('presupuesto_id'))

    facturas = Factura.objects.filter(
        fecha_emision__range=(desde, hasta),
        obra_id__in=obras.values('pk'),
    )
    ventas = facturas.aggregate(total=Sum('monto_total'), cantidad=Count('pk'))
    notas_credito_periodo = NotaCredito.objects.filter(
        fecha__date__range=(desde, hasta),
        factura__obra_id__in=obras.values('pk'),
    ).aggregate(total=Sum('monto'), cantidad=Count('pk'))
    recaudacion_pagos = Pago.objects.filter(
        fecha_pago__range=(desde, hasta), factura__obra_id__in=obras.values('pk'),
    ).aggregate(total=Sum('monto'), cantidad=Count('pk'))
    reversas_periodo = ReversaPago.objects.filter(
        fecha__date__range=(desde, hasta), pago__factura__obra_id__in=obras.values('pk'),
    ).aggregate(total=Sum('monto'), cantidad=Count('pk'))
    costos = CostoMaterial.objects.filter(
        fecha__range=(desde, hasta),
        obra_id__in=obras.values('pk'),
    )
    costos_periodo = costos.aggregate(total=Sum('monto'), cantidad=Count('pk'))
    costos_por_categoria = list(
        costos.values('categoria')
        .annotate(monto=Sum('monto'), cantidad=Count('pk'))
        .order_by('-monto', 'categoria')
    )
    costos_por_mes = list(
        costos.annotate(mes=TruncMonth('fecha'))
        .values('mes')
        .annotate(monto=Sum('monto'), cantidad=Count('pk'))
        .order_by('mes')
    )

    aprobados = presupuestos.filter(
        estado='aprobado',
        fecha_decision_cliente__date__range=(desde, hasta),
    ).aggregate(total=Sum('monto_total'), cantidad=Count('pk'))
    pendientes = presupuestos.filter(
        estado__in=ESTADOS_PENDIENTES_PRESUPUESTO,
        fecha_emision__range=(desde, hasta),
    ).aggregate(total=Sum('monto_total'), cantidad=Count('pk'))

    hoy = timezone.localdate()
    cartera = Factura.objects.filter(obra_id__in=obras.values('pk'), saldo_pendiente__gt=0)
    facturas_vencidas = cartera.filter(fecha_vencimiento__lt=hoy).aggregate(total=Sum('saldo_pendiente'), cantidad=Count('pk'))
    antiguedad = {
        '1_30_dias': cartera.filter(fecha_vencimiento__gte=hoy - timedelta(days=30), fecha_vencimiento__lt=hoy).aggregate(total=Sum('saldo_pendiente'), cantidad=Count('pk')),
        '31_60_dias': cartera.filter(fecha_vencimiento__gte=hoy - timedelta(days=60), fecha_vencimiento__lt=hoy - timedelta(days=30)).aggregate(total=Sum('saldo_pendiente'), cantidad=Count('pk')),
        '61_90_dias': cartera.filter(fecha_vencimiento__gte=hoy - timedelta(days=90), fecha_vencimiento__lt=hoy - timedelta(days=60)).aggregate(total=Sum('saldo_pendiente'), cantidad=Count('pk')),
        'mas_90_dias': cartera.filter(fecha_vencimiento__lt=hoy - timedelta(days=90)).aggregate(total=Sum('saldo_pendiente'), cantidad=Count('pk')),
    }
    presupuesto_decidido = presupuestos.filter(fecha_decision_cliente__date__range=(desde, hasta), estado__in=('aprobado', 'rechazado'))
    conversion = presupuesto_decidido.aggregate(
        aprobados=Count('pk', filter=Q(estado='aprobado')),
        rechazados=Count('pk', filter=Q(estado='rechazado')),
    )
    por_vencer = presupuestos.filter(estado='enviado', fecha_vencimiento__range=(hoy, hoy + timedelta(days=7))).aggregate(total=Sum('monto_total'), cantidad=Count('pk'))
    presupuestos_proyectados = presupuestos.filter(estado='aprobado', fecha_decision_cliente__date__range=(desde, hasta))
    monto_aprobado_proyectado = presupuestos_proyectados.aggregate(total=Sum('monto_total'))['total'] or 0
    facturas_proyectadas = Factura.objects.filter(obra__presupuesto__in=presupuestos_proyectados)
    monto_facturado_proyectado = facturas_proyectadas.aggregate(total=Sum('monto_total'))['total'] or 0
    notas_proyectadas = NotaCredito.objects.filter(factura__in=facturas_proyectadas).aggregate(total=Sum('monto'))['total'] or 0
    proyeccion_ingresos = max(0, monto_aprobado_proyectado - monto_facturado_proyectado + notas_proyectadas)

    obras_por_estado = list(
        obras.values('estado_operativo')
        .annotate(cantidad=Count('pk'))
        .order_by('estado_operativo')
    )
    servicios_realizados = obras.filter(
        estado_operativo='finalizada',
        fecha_termino__range=(desde, hasta),
    ).count()
    servicios_por_categoria = list(
        obras.filter(
            estado_operativo='finalizada',
            fecha_termino__range=(desde, hasta),
        )
        .values('clasificacion_servicio_id', 'clasificacion_servicio__nombre')
        .annotate(cantidad=Count('pk'))
        .order_by('-cantidad', 'clasificacion_servicio__nombre')
    )
    facturacion_mensual = list(
        facturas.annotate(mes=TruncMonth('fecha_emision'))
        .values('mes')
        .annotate(monto=Sum('monto_total'), cantidad=Count('pk'))
        .order_by('mes')
    )
    obras_activas_por_tecnico = list(
        obras.filter(estado_operativo__in=('en-proceso', 'suspendida'), tecnico_responsable__isnull=False)
        .values('tecnico_responsable_id', 'tecnico_responsable__first_name', 'tecnico_responsable__last_name')
        .annotate(cantidad=Count('pk'))
        .order_by('-cantidad', 'tecnico_responsable__last_name')
    )
    ventas_por_cliente = list(
        facturas.values('obra__presupuesto__cliente_id', 'obra__presupuesto__cliente__razon_social')
        .annotate(monto=Sum('monto_total'), cantidad=Count('pk'))
        .order_by('-monto')[:10]
    )
    creditos_por_cliente = {
        fila['factura__obra__presupuesto__cliente_id']: fila['monto']
        for fila in NotaCredito.objects.filter(fecha__date__range=(desde, hasta), factura__obra_id__in=obras.values('pk'))
        .values('factura__obra__presupuesto__cliente_id')
        .annotate(monto=Sum('monto'))
    }
    top_clientes_ventas = [{
        'cliente_id': fila['obra__presupuesto__cliente_id'],
        'cliente': fila['obra__presupuesto__cliente__razon_social'],
        'monto_facturado_bruto': int(fila['monto'] or 0),
        'monto_notas_credito': int(creditos_por_cliente.get(fila['obra__presupuesto__cliente_id'], 0)),
        'monto_neto': int(fila['monto'] or 0) - int(creditos_por_cliente.get(fila['obra__presupuesto__cliente_id'], 0)),
        'cantidad_facturas': fila['cantidad'],
    } for fila in ventas_por_cliente]
    top_clientes_deuda = list(
        cartera.values('obra__presupuesto__cliente_id', 'obra__presupuesto__cliente__razon_social')
        .annotate(saldo=Sum('saldo_pendiente'), cantidad=Count('pk'))
        .order_by('-saldo')[:10]
    )
    costos_por_obra = list(
        obras.annotate(costo_total=Sum(
            'costos__monto',
            filter=Q(costos__deleted_at__isnull=True),
        ))
        .filter(costo_total__gt=0)
        .values(
            'id', 'codigo_obra', 'nombre_obra',
            'presupuesto__monto_neto', 'costo_total', 'estado_operativo',
            'estado_comercial', 'avance_porcentaje',
            'presupuesto__cliente__razon_social',
            'tecnico_responsable__first_name', 'tecnico_responsable__last_name',
            'clasificacion_servicio__nombre',
        )
        .order_by('-costo_total')[:10]
    )

    return {
        'moneda': 'CLP',
        'periodo': {'desde': desde.isoformat(), 'hasta': hasta.isoformat()},
        'filtros': {
            'cliente_id': cliente_id,
            'tecnico_id': tecnico_id,
            'estado_obra': estado_obra,
        },
        'metricas': {
            'ventas_facturadas': {
                'monto_total_bruto': int(ventas['total'] or 0),
                'monto_notas_credito': int(notas_credito_periodo['total'] or 0),
                'monto_total': int((ventas['total'] or 0) - (notas_credito_periodo['total'] or 0)),
                'cantidad_facturas': ventas['cantidad'],
                'cantidad_notas_credito': notas_credito_periodo['cantidad'],
            },
            'presupuestos_aprobados': {
                'cantidad': aprobados['cantidad'],
                'monto_total': int(aprobados['total'] or 0),
            },
            'presupuestos_pendientes': {
                'cantidad': pendientes['cantidad'],
                'monto_total': int(pendientes['total'] or 0),
            },
            'costos_directos_periodo': {
                'monto_total': int(costos_periodo['total'] or 0),
                'cantidad_registros': costos_periodo['cantidad'],
            },
            'cuentas_por_cobrar': {
                'saldo_total': int(cartera.aggregate(total=Sum('saldo_pendiente'))['total'] or 0),
                'facturas_pendientes': cartera.count(),
                'saldo_vencido': int(facturas_vencidas['total'] or 0),
                'facturas_vencidas': facturas_vencidas['cantidad'],
                'antiguedad': {
                    clave: {'saldo': int(fila['total'] or 0), 'cantidad_facturas': fila['cantidad']}
                    for clave, fila in antiguedad.items()
                },
            },
            'recaudacion_periodo': {
                'pagos_brutos': int(recaudacion_pagos['total'] or 0),
                'reversiones': int(reversas_periodo['total'] or 0),
                'monto_neto': int((recaudacion_pagos['total'] or 0) - (reversas_periodo['total'] or 0)),
                'cantidad_pagos': recaudacion_pagos['cantidad'],
                'cantidad_reversiones': reversas_periodo['cantidad'],
            },
            'proyeccion_ingresos_aprobados': int(proyeccion_ingresos),
            'presupuestos_por_vencer_7_dias': {
                'cantidad': por_vencer['cantidad'], 'monto_total': int(por_vencer['total'] or 0),
            },
            'conversion_presupuestos': {
                'aprobados': conversion['aprobados'],
                'rechazados': conversion['rechazados'],
                'decididos': conversion['aprobados'] + conversion['rechazados'],
                'porcentaje_aprobacion': round(conversion['aprobados'] * 100 / (conversion['aprobados'] + conversion['rechazados']), 1) if conversion['aprobados'] + conversion['rechazados'] else 0,
            },
            'obras_en_proceso': obras_sin_estado.filter(estado_operativo='en-proceso').count(),
            'servicios_realizados': servicios_realizados,
        },
        'distribuciones': {
            'obras_por_estado': obras_por_estado,
            'obras_activas_por_tecnico': [{
                'tecnico_id': fila['tecnico_responsable_id'],
                'tecnico': ' '.join(filter(None, [fila['tecnico_responsable__first_name'], fila['tecnico_responsable__last_name']])),
                'cantidad_obras': fila['cantidad'],
            } for fila in obras_activas_por_tecnico],
            'top_clientes_por_ventas': top_clientes_ventas,
            'top_clientes_por_deuda': [{
                'cliente_id': fila['obra__presupuesto__cliente_id'],
                'cliente': fila['obra__presupuesto__cliente__razon_social'],
                'saldo_pendiente': int(fila['saldo'] or 0),
                'facturas_pendientes': fila['cantidad'],
            } for fila in top_clientes_deuda],
            'servicios_por_categoria': servicios_por_categoria,
            'facturacion_mensual': [
                {
                    'mes': fila['mes'].isoformat(),
                    'monto_total': int(fila['monto'] or 0),
                    'cantidad_facturas': fila['cantidad'],
                }
                for fila in facturacion_mensual
            ],
            'costos_por_categoria': [
                {
                    'categoria': fila['categoria'],
                    'monto_total': int(fila['monto'] or 0),
                    'cantidad_registros': fila['cantidad'],
                }
                for fila in costos_por_categoria
            ],
            'costos_mensuales': [
                {
                    'mes': fila['mes'].isoformat(),
                    'monto_total': int(fila['monto'] or 0),
                    'cantidad_registros': fila['cantidad'],
                }
                for fila in costos_por_mes
            ],
            'costos_por_obra_acumulados': [
                {
                    'obra_id': fila['id'],
                    'codigo_obra': fila['codigo_obra'],
                    'nombre_obra': fila['nombre_obra'],
                    'cliente_nombre': fila['presupuesto__cliente__razon_social'],
                    'tecnico_nombre': ' '.join(filter(None, [
                        fila['tecnico_responsable__first_name'],
                        fila['tecnico_responsable__last_name'],
                    ])),
                    'categoria_servicio': fila['clasificacion_servicio__nombre'],
                    'estado_operativo': fila['estado_operativo'],
                    'estado_comercial': fila['estado_comercial'],
                    'avance_porcentaje': fila['avance_porcentaje'],
                    'presupuesto_neto': int(fila['presupuesto__monto_neto'] or 0),
                    'costo_acumulado': int(fila['costo_total'] or 0),
                    'porcentaje_ejecutado': round(
                        int(fila['costo_total'] or 0) * 100 / int(fila['presupuesto__monto_neto'])
                    ) if fila['presupuesto__monto_neto'] else None,
                }
                for fila in costos_por_obra
            ],
        },
    }
