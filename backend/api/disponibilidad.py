"""Reservas laborales: lunes a viernes, 08–13 y 14–18, America/Santiago.

Los intervalos son semiabiertos: una reserva puede empezar cuando otra termina.
No se infieren fechas para obras antiguas ni se consideran feriados en este MVP.
"""
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.db.models import Q
from rest_framework.exceptions import ValidationError

from .models import Obra, Usuario

CHILE = ZoneInfo('America/Santiago')
TURNOS = ((time(8), time(13)), (time(14), time(18)))
MAX_DIAS_PLANIFICACION = 367


def franjas(inicio, fin):
    inicio, fin = inicio.astimezone(CHILE), fin.astimezone(CHILE)
    dia = inicio.date()
    while dia <= fin.date():
        if dia.weekday() < 5:
            for desde, hasta in TURNOS:
                a = max(inicio, datetime.combine(dia, desde, CHILE))
                b = min(fin, datetime.combine(dia, hasta, CHILE))
                if a < b:
                    yield a, b
        if dia == fin.date():
            break
        dia += timedelta(days=1)


def validar_rango(inicio, fin):
    if not inicio or not fin:
        raise ValidationError({'planificacion': 'Indique inicio y término estimado con fecha y hora.'})
    if inicio >= fin:
        raise ValidationError({'planificacion': 'El término estimado debe ser posterior al inicio.'})
    if (fin - inicio) > timedelta(days=MAX_DIAS_PLANIFICACION):
        raise ValidationError({'planificacion': 'La planificación admite un máximo de 367 días.'})
    try:
        primera_franja = next(franjas(inicio, fin), None)
    except OverflowError as exc:
        raise ValidationError({'planificacion': 'Las fechas están fuera del calendario admitido.'}) from exc
    if not primera_franja:
        raise ValidationError({'planificacion': 'El período debe incluir horas laborales de lunes a viernes, de 08:00 a 13:00 o de 14:00 a 18:00.'})


def obras_reservadas(tecnico_id, inicio, fin, excluir=None):
    return Obra.objects.filter(tecnico_responsable_id=tecnico_id, estado_operativo='en-proceso').exclude(pk=excluir).filter(
        Q(inicio_programado__isnull=True) | Q(fin_estimado__isnull=True)
        | Q(inicio_programado__lt=fin, fin_estimado__gt=inicio)
    ).select_related('presupuesto__cliente')


def evaluar(tecnico_id, inicio, fin, excluir=None):
    validar_rango(inicio, fin)
    solicitadas = list(franjas(inicio, fin))
    conflictos, sin_planificar, ocupadas = [], [], []
    obras = list(obras_reservadas(tecnico_id, inicio, fin, excluir))
    for obra in obras:
        if not obra.inicio_programado or not obra.fin_estimado:
            sin_planificar.append({'id': obra.pk, 'nombre': obra.nombre_obra})
            continue
        for a, b in franjas(max(inicio, obra.inicio_programado), min(fin, obra.fin_estimado)):
            ocupadas.append((a, b))
            conflictos.append({'obra_id': obra.pk, 'obra': obra.nombre_obra, 'inicio': a.isoformat(), 'fin': b.isoformat()})
    # Unión de intervalos: las inconsistencias históricas no duplican horas ocupadas.
    unidas = []
    for a, b in sorted(ocupadas):
        if unidas and a <= unidas[-1][1]:
            unidas[-1] = (unidas[-1][0], max(unidas[-1][1], b))
        else:
            unidas.append((a, b))
    total = sum((b - a).total_seconds() for a, b in solicitadas)
    ocupado = sum((b - a).total_seconds() for a, b in unidas)
    estado = 'sin_determinar' if sin_planificar else 'disponible' if not ocupado else 'ocupado' if ocupado >= total else 'parcial'
    return {
        'estado': estado, 'asignable': not conflictos and not sin_planificar,
        'horas_laborales': round(total / 3600, 2), 'horas_ocupadas': round(ocupado / 3600, 2),
        'conflictos': conflictos, 'sin_planificar': sin_planificar,
        'obras': [{'id': o.pk, 'nombre': o.nombre_obra} for o in obras],
    }


def validar_asignacion(tecnico_id, inicio, fin, excluir=None):
    validar_rango(inicio, fin)
    if not tecnico_id:
        return
    # Todos los caminos de escritura toman este mismo bloqueo dentro de una transacción.
    tecnico = Usuario.objects.select_for_update().get(pk=tecnico_id)
    if tecnico.rol != 'TECNICO' or tecnico.estado != 'activo' or not tecnico.is_active:
        raise ValidationError({'tecnico_responsable': 'Seleccione un técnico activo.'})
    resultado = evaluar(tecnico_id, inicio, fin, excluir)
    if not resultado['asignable']:
        raise ValidationError({
            'detalle': 'El técnico no está disponible para todo el período. Cambie el técnico o las fechas. Si existen obras sin planificación, complete primero sus fechas.',
            'conflictos': resultado['conflictos'], 'sin_planificar': resultado['sin_planificar'],
        })


def agenda(tecnico, inicio, fin):
    obras = list(obras_reservadas(tecnico.pk, inicio, fin))
    eventos = []
    for obra in obras:
        if not obra.inicio_programado or not obra.fin_estimado:
            continue
        for a, b in franjas(max(inicio, obra.inicio_programado), min(fin, obra.fin_estimado)):
            eventos.append({'id': f'{obra.pk}-{a.isoformat()}', 'fecha': a.date().isoformat(),
                            'inicio': a.hour + a.minute / 60, 'fin': b.hour + b.minute / 60,
                            'estado': 'ocupado', 'titulo': obra.nombre_obra,
                            'detalle': obra.presupuesto.cliente.razon_social})
    return {'tecnico': {'id': tecnico.pk, 'nombre': tecnico.get_full_name(), 'rut': tecnico.rut_usuario, 'especialidad': tecnico.cargo},
            'eventos': eventos,
            'sin_planificar': [{'id': o.pk, 'nombre': o.nombre_obra} for o in obras if not o.inicio_programado or not o.fin_estimado]}
