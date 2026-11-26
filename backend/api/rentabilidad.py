from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Exists, OuterRef, Q, Sum

from .models import CostoMaterial, Factura, GastoGeneral, MermaMaterial, MovimientoMaterial, NotaCredito


CATEGORIAS_DIRECTAS_DESGLOSADAS = {'MANO_DE_OBRA': 'mano_de_obra', 'MATERIALES': 'materiales'}
COSTO_SIN_DESGLOSE = Q(categoria__in=CATEGORIAS_DIRECTAS_DESGLOSADAS) & (
    Q(cantidad_real__isnull=True) | Q(costo_unitario_real__isnull=True) | Q(unidad_real='')
)


def despachos_pendientes(obras):
    costo = CostoMaterial.objects.filter(despacho_id=OuterRef('pk'))
    return MovimientoMaterial.objects.filter(
        tipo=MovimientoMaterial.Tipo.ENTRADA, asignacion__obra_id__in=obras,
    ).filter(~Exists(costo))


def pendientes_costos_finalizacion(obra):
    costos = obra.costos.all()
    pendientes = []
    if not costos.filter(categoria='MANO_DE_OBRA').exists():
        pendientes.append('Registre las horas profesionales y su costo por hora.')
    if costos.filter(COSTO_SIN_DESGLOSE).exists():
        pendientes.append('Complete el desglose de los costos de mano de obra y materiales.')
    cantidad_pendiente = despachos_pendientes([obra.pk]).count()
    if cantidad_pendiente:
        pendientes.append(f'Valorice los despachos de materiales pendientes ({cantidad_pendiente}).')
    entradas = MovimientoMaterial.objects.filter(tipo=MovimientoMaterial.Tipo.ENTRADA)
    if MermaMaterial.objects.filter(asignacion__obra=obra).exclude(
        asignacion_id__in=entradas.values('asignacion_id'),
    ).exists():
        pendientes.append('Registre la entrada inicial de los materiales con mermas previas.')
    if entradas.filter(asignacion__obra=obra).exists() and costos.filter(
        categoria='MATERIALES', despacho__isnull=True,
    ).exists():
        pendientes.append('Concilie los costos de materiales sin despacho vinculado para evitar duplicados.')
    return pendientes


def detallar_otros_costos(obra):
    costos = CostoMaterial.objects.filter(obra=obra).exclude(
        categoria__in=CATEGORIAS_DIRECTAS_DESGLOSADAS,
    ).order_by('-fecha', '-pk')
    registros = [
        {
            'id': costo.pk,
            'fecha': costo.fecha,
            'categoria': costo.get_categoria_display(),
            'descripcion': costo.descripcion,
            'monto': int(costo.monto),
        }
        for costo in costos
    ]
    return {'registros': registros, 'total': sum(registro['monto'] for registro in registros)}


def calcular_rentabilidad(obras, desde, hasta, *, incluir_empresa):
    acumulado = defaultdict(lambda: {'ingresos': 0, 'mano_de_obra': 0, 'materiales': 0, 'otros_costos': 0})
    periodo = dict(acumulado[None])
    facturas_registradas = set()
    categorias_desglosadas = defaultdict(set)
    obras_del_periodo = set()
    ids = obras.values('pk')

    for obra_id, fecha, neto in Factura.objects.filter(obra_id__in=ids).values_list('obra_id', 'fecha_emision', 'monto_neto'):
        acumulado[obra_id]['ingresos'] += int(neto)
        facturas_registradas.add(obra_id)
        if desde <= fecha <= hasta:
            periodo['ingresos'] += int(neto)
            obras_del_periodo.add(obra_id)

    notas = NotaCredito.objects.filter(factura__obra_id__in=ids, factura__deleted_at__isnull=True)
    creditos_acumulados = defaultdict(lambda: Decimal('0'))
    ajustes_acumulados = defaultdict(int)
    for factura_id, obra_id, fecha, monto, neto, total in notas.order_by('fecha', 'pk').values_list(
        'factura_id', 'factura__obra_id', 'fecha__date', 'monto', 'factura__monto_neto', 'factura__monto_total',
    ):
        creditos_acumulados[factura_id] += monto
        ajuste_acumulado = int(
            (creditos_acumulados[factura_id] * neto / total).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        ) if total else 0
        ajuste = ajuste_acumulado - ajustes_acumulados[factura_id]
        ajustes_acumulados[factura_id] = ajuste_acumulado
        acumulado[obra_id]['ingresos'] -= ajuste
        if desde <= fecha <= hasta:
            periodo['ingresos'] -= ajuste
            obras_del_periodo.add(obra_id)

    costos = CostoMaterial.objects.filter(obra_id__in=ids)
    obras_con_despachos_pendientes = set(despachos_pendientes(ids).values_list('asignacion__obra_id', flat=True))
    obras_sin_desglose = set(costos.filter(COSTO_SIN_DESGLOSE).values_list('obra_id', flat=True))
    obras_con_despachos = MovimientoMaterial.objects.filter(tipo=MovimientoMaterial.Tipo.ENTRADA).values('asignacion__obra_id')
    obras_sin_conciliar = set(costos.filter(
        categoria='MATERIALES', despacho__isnull=True, obra_id__in=obras_con_despachos,
    ).values_list('obra_id', flat=True))
    for costo in costos.values('obra_id', 'categoria', 'fecha', 'cantidad_real').annotate(total=Sum('monto')).order_by():
        obra_id = costo['obra_id']
        campo = CATEGORIAS_DIRECTAS_DESGLOSADAS.get(costo['categoria'], 'otros_costos')
        monto = int(costo['total'])
        acumulado[obra_id][campo] += monto
        if costo['cantidad_real'] is not None:
            categorias_desglosadas[obra_id].add(campo)
        if desde <= costo['fecha'] <= hasta:
            periodo[campo] += monto
            obras_del_periodo.add(obra_id)

    def resultado(datos):
        costos_directos = datos['mano_de_obra'] + datos['materiales'] + datos['otros_costos']
        return {**datos, 'costos_directos': costos_directos, 'resultado': datos['ingresos'] - costos_directos}

    filas = []
    for obra in obras.values(
        'id', 'codigo_obra', 'nombre_obra', 'estado_comercial', 'presupuesto__monto_neto',
        'presupuesto__costo_base', 'presupuesto__reserva_imprevistos',
    ).order_by('codigo_obra'):
        obra_id = obra['id']
        presupuesto_neto = int(obra.pop('presupuesto__monto_neto'))
        costo_base = obra.pop('presupuesto__costo_base')
        reserva = obra.pop('presupuesto__reserva_imprevistos')
        costo_previsto = int(costo_base + (reserva or 0)) if costo_base is not None else None
        pendientes = []
        if obra['estado_comercial'] != 'cerrada':
            pendientes.append('Cierre comercial pendiente')
        if obra_id not in facturas_registradas:
            pendientes.append('Sin facturación registrada')
        if 'mano_de_obra' not in categorias_desglosadas[obra_id]:
            pendientes.append('Sin horas profesionales valorizadas')
        if obra_id in obras_con_despachos_pendientes:
            pendientes.append('Despachos de materiales sin valorizar')
        if obra_id in obras_sin_desglose:
            pendientes.append('Costos sin desglose')
        if obra_id in obras_sin_conciliar:
            pendientes.append('Costos de materiales sin conciliar con despachos')
        totales = resultado(acumulado[obra_id])
        filas.append({
            **obra, **totales, 'pendientes': pendientes, 'presupuesto_neto': presupuesto_neto,
            'costo_previsto': costo_previsto,
            'desviacion_costos': totales['costos_directos'] - costo_previsto if costo_previsto is not None else None,
        })

    resumen = resultado(periodo)
    resumen['obras_provisionales'] = sum(
        bool(fila['pendientes']) for fila in filas if fila['id'] in obras_del_periodo
    )
    resumen['tiene_movimientos'] = bool(obras_del_periodo)
    empresa = None
    if incluir_empresa:
        gastos = GastoGeneral.objects.filter(fecha__range=(desde, hasta)).aggregate(total=Sum('monto'))['total']
        empresa = {
            'gastos_generales': int(gastos or 0),
            'resultado': resumen['resultado'] - int(gastos or 0),
            'gastos_registrados': gastos is not None,
        }
    return {'periodo': resumen, 'obras': filas, 'empresa': empresa}
