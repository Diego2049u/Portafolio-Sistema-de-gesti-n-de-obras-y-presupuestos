# Planificación y disponibilidad

Las obras reservan al técnico entre `inicio_programado` y `fin_estimado`,
intersectando ese intervalo con la jornada de lunes a viernes, 08:00–13:00 y
14:00–18:00, en `America/Santiago`. No se excluyen feriados en esta versión.
`fecha_termino` conserva su significado de término real de la obra.

Solo `en-proceso` reserva. Suspender, finalizar o cancelar libera la reserva;
reanudar o reabrir vuelve a comprobar la disponibilidad. Las fechas no se repiten
semanalmente: una obra de noviembre–diciembre no reserva enero–febrero.

Crear, reasignar o reprogramar una obra activa con un cruce devuelve HTTP 400.
No hay confirmación de sobrecarga. Se permite que una reserva comience justo
cuando termina otra. La escritura toma un bloqueo de fila sobre el usuario
técnico en PostgreSQL para serializar asignaciones concurrentes.

## API

- `GET /api/obras/tecnicos-disponibles/?inicio=...&fin=...`: disponibilidad para
  fechas ISO con hora. Sin zona explícita se interpretan como hora de Chile.
  Si se omiten ambos parámetros consulta la jornada de la semana actual.
  `excluir=<obra_id>` permite consultar una reprogramación sin contar la propia
  obra; el servidor vuelve a validar al guardar usando el ID real de la obra.
- `GET /api/obras/agenda-tecnico/?tecnico_id=...&desde=YYYY-MM-DD&hasta=YYYY-MM-DD`:
  bloques fechados, con ambos días incluidos. El técnico autenticado solo recibe
  su propia agenda, independientemente del ID solicitado. No expone importes.
- `POST /api/obras/` y `PATCH /api/obras/<id>/`: fechas de planificación y
  `tecnico_responsable`. La validación del servidor es obligatoria aun si no se
  realizó la consulta previa de disponibilidad.

Las tarjetas distinguen `disponible`, `parcial` y `ocupado` según las horas
reservadas en el período consultado. Una obra activa antigua sin planificación
produce `sin_determinar`; no se inventan fechas ni se confirman horas libres.
Para completar datos existentes se usa **Planificar** en Obras y Proyectos.
Si hay varias obras antiguas del mismo técnico sin fechas, se pueden suspender
temporalmente mientras se completa su planificación y reanudarlas después de
comprobar que sus períodos no se cruzan.

## Validación

Pruebas rápidas, sin tocar la base de desarrollo:

```powershell
backend/.venv/Scripts/python.exe backend/manage.py test api --settings=central.test_settings --noinput
```

La prueba de concurrencia usa dos solicitudes independientes y requiere
PostgreSQL. Se omite en SQLite:

```powershell
backend/.venv/Scripts/python.exe backend/manage.py test api.test_disponibilidad --noinput --keepdb
```
