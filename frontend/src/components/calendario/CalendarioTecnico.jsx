import { useEffect, useRef, useState } from 'react';
import { claveFecha, diasVisibles, fechaChile, formatearFecha, sumarDias } from './fechas';
import './calendario.css';

const HORAS = Array.from({ length: 24 }, (_, hora) => hora);
const horaTexto = (hora) => { const minutos = Math.round(hora * 60); return `${String(Math.floor(minutos / 60)).padStart(2, '0')}:${String(minutos % 60).padStart(2, '0')}`; };

// obtenerBloques(fecha) recibe una fecha civil y devuelve franjas con inicio/fin
// en horas, título y estado. La vista no depende del origen de las asignaciones.
export default function CalendarioTecnico({ nombre, obtenerBloques, onPeriodoChange, loading = false, error = '', reintentar, sinPlanificar = false }) {
  const [fecha, setFecha] = useState(fechaChile);
  const [vista, setVista] = useState('semana');
  const scroll = useRef(null);
  const hoy = claveFecha(fechaChile());
  const dias = diasVisibles(fecha, vista);
  const desde = claveFecha(dias[0]), hasta = claveFecha(dias[dias.length - 1]);
  useEffect(() => { onPeriodoChange?.(desde, hasta); }, [desde, hasta, onPeriodoChange]);
  const titulo = formatearFecha(fecha, vista === 'dia'
    ? { day: 'numeric', month: 'long', year: 'numeric' }
    : { month: 'long', year: 'numeric' });

  useEffect(() => {
    // Abre en la jornada laboral; se puede desplazar para ver las 24 horas.
    scroll.current.scrollTop = 7 * 56;
  }, []);

  function navegar(direccion) {
    setFecha((actual) => sumarDias(actual, direccion * (vista === 'dia' ? 1 : 7)));
  }

  return <section className="calendario" aria-label={`Calendario de disponibilidad de ${nombre}`}>
    <div className="calendario-toolbar">
      <div className="calendario-controles">
        <button type="button" onClick={() => navegar(-1)} aria-label={vista === 'dia' ? 'Día anterior' : 'Semana anterior'}><span aria-hidden="true" className="material-symbols-outlined">chevron_left</span></button>
        <button type="button" onClick={() => navegar(1)} aria-label={vista === 'dia' ? 'Día siguiente' : 'Semana siguiente'}><span aria-hidden="true" className="material-symbols-outlined">chevron_right</span></button>
        <button type="button" onClick={() => setFecha(fechaChile())}>Hoy</button>
      </div>
      <label className="text-body-sm text-secondary">Ir a fecha <input aria-label="Ir a fecha" type="date" className="rounded border border-surface-container px-2 py-1" value={claveFecha(fecha)} onChange={(event) => { if (event.target.value) setFecha(new Date(`${event.target.value}T12:00:00Z`)); }} /></label>
      <div className="calendario-periodo" aria-live="polite">
        <h2 className="font-semibold capitalize">{titulo}</h2>
        {vista === 'semana' && <p>{formatearFecha(dias[0], { day: 'numeric', month: 'short' })} – {formatearFecha(dias[6], { day: 'numeric', month: 'short', year: 'numeric' })}</p>}
      </div>
      <select aria-label="Vista del calendario" value={vista} onChange={(event) => setVista(event.target.value)}>
        <option value="semana">Semana</option>
        <option value="dia">Día</option>
      </select>
    </div>

    {loading && <p role="status" className="px-6 py-2 text-secondary">Consultando agenda…</p>}
    {error && <p role="alert" className="px-6 py-2 text-error">{error} <button type="button" onClick={reintentar} className="underline">Reintentar</button></p>}
    {sinPlanificar && <p role="status" className="px-6 py-2 text-tertiary">Existen obras sin planificación. Las horas libres aún no pueden confirmarse como disponibles.</p>}
    <div className="calendario-horizontal" tabIndex={0} role="region" aria-label="Cuadrícula de disponibilidad" aria-busy={loading}>
      <div className={`calendario-contenido ${vista === 'dia' ? 'calendario-dia' : ''}`} style={{ '--dias': dias.length }}>
        <div className="calendario-cabecera">
          <span />
          {dias.map((dia) => <button type="button" key={claveFecha(dia)} className={claveFecha(dia) === hoy ? 'calendario-hoy' : ''} onClick={() => { setFecha(dia); setVista('dia'); }} aria-label={`Ver ${formatearFecha(dia, { dateStyle: 'full' })}`}>
            {formatearFecha(dia, { weekday: 'short' }).replace('.', '')} · {dia.getUTCDate()}
          </button>)}
        </div>
        <div className="calendario-resumen">
          <span>Jornada</span>
          {dias.map((dia) => <div key={claveFecha(dia)} className={claveFecha(dia) === hoy ? 'calendario-resumen-hoy' : ''}>
            <span className={`calendario-etiqueta ${dia.getUTCDay() === 0 || dia.getUTCDay() === 6 ? 'calendario-etiqueta-descanso' : ''}`}>
              {dia.getUTCDay() === 0 || dia.getUTCDay() === 6 ? 'Sin jornada' : '08:00 – 18:00'}
            </span>
          </div>)}
        </div>
        <div ref={scroll} className="calendario-scroll" tabIndex={0} role="region" aria-label="Horas del día, de 00:00 a 24:00">
          <div className="calendario-horas">
            <div className="calendario-eje">{HORAS.map((hora) => <div key={hora}>{horaTexto(hora)}</div>)}</div>
            {dias.map((dia) => <div key={claveFecha(dia)} className={`calendario-columna ${claveFecha(dia) === hoy ? 'calendario-columna-hoy' : ''}`} aria-label={formatearFecha(dia, { dateStyle: 'full' })}>
              {(!loading && !error ? obtenerBloques(dia) : []).map((bloque, index) => <article key={bloque.id || index} className={`calendario-bloque calendario-bloque-${bloque.estado}`} style={{ top: `${bloque.inicio * 56 + 3}px`, height: `${(bloque.fin - bloque.inicio) * 56 - 6}px` }}>
                <p className="calendario-bloque-titulo">{bloque.titulo}</p>
                <p>{horaTexto(bloque.inicio)} – {horaTexto(bloque.fin)}</p>
                {bloque.detalle && <p className="calendario-bloque-detalle">{bloque.detalle}</p>}
              </article>)}
            </div>)}
          </div>
        </div>
      </div>
    </div>
    <footer className="calendario-leyenda">
      <span><i className="calendario-punto calendario-punto-disponible" />Disponible</span>
      <span><i className="calendario-punto calendario-punto-ocupado" />En obra</span>
      <span><i className="calendario-punto calendario-punto-descanso" />Colación</span>
      <p>Hora de Chile · Lunes a viernes, sin exclusión de feriados.</p>
    </footer>
  </section>;
}
