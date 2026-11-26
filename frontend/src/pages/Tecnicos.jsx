import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, withQuery } from '../api/client';
import { ESTADOS_DISPONIBILIDAD, rangoLaboralActual } from '../components/calendario/agenda';

const COLORES = { disponible: 'bg-emerald-50 text-emerald-800', parcial: 'bg-tertiary-fixed text-tertiary', ocupado: 'bg-primary/10 text-primary', sin_determinar: 'bg-surface-container text-secondary' };

export default function Tecnicos() {
  const [rango, setRango] = useState(rangoLaboralActual);
  const [estado, setEstado] = useState({ rows: [], loading: true, error: '' });
  const [version, setVersion] = useState(0);
  useEffect(() => {
    let vigente = true;
    async function cargar() {
      setEstado({ rows: [], loading: true, error: '' });
      try {
        if (!rango.inicio || !rango.fin || rango.inicio >= rango.fin) throw new Error('Indica un inicio anterior al término.');
        const rows = await api.request(withQuery('/obras/tecnicos-disponibles/', rango));
        if (vigente) setEstado({ rows, loading: false, error: '' });
      } catch (error) { if (vigente) setEstado({ rows: [], loading: false, error: error.message }); }
    }
    cargar();
    return () => { vigente = false; };
  }, [rango, version]);

  return <div className="space-y-6">
    <header><p className="text-label-sm uppercase text-primary">Gestión de dotación</p><h1 className="mt-1 text-headline-lg font-bold">Disponibilidad de Técnicos</h1><p className="mt-1 text-secondary">Disponibilidad calculada para el período seleccionado, de lunes a viernes.</p></header>
    <section className="flex flex-wrap items-end gap-4 rounded-xl bg-surface-container-lowest p-5 shadow-sm">
      <label>Inicio<input type="datetime-local" className="mt-1 block rounded-lg bg-surface-container-low p-2" value={rango.inicio} onChange={(e) => setRango({ ...rango, inicio: e.target.value })} /></label>
      <label>Término<input type="datetime-local" className="mt-1 block rounded-lg bg-surface-container-low p-2" value={rango.fin} onChange={(e) => setRango({ ...rango, fin: e.target.value })} /></label>
      <button type="button" onClick={() => setVersion((v) => v + 1)} className="rounded-lg bg-primary-container px-4 py-2 text-on-primary">Actualizar</button>
    </section>
    {estado.error && <p role="alert" className="rounded bg-error-container p-4 text-error">{estado.error}</p>}
    {estado.loading ? <p role="status">Consultando disponibilidad…</p> : !estado.error && <>
      <section className="grid gap-4 sm:grid-cols-3">{['disponible', 'parcial', 'ocupado'].map((tipo) => <article key={tipo} className="rounded-xl bg-surface-container-lowest p-5 shadow-sm"><p className="text-label-sm text-secondary">{ESTADOS_DISPONIBILIDAD[tipo]}</p><p className="mt-1 text-3xl font-bold">{estado.rows.filter((t) => t.estado === tipo).length}</p></article>)}</section>
      <section className="rounded-xl bg-surface-container-lowest p-5 shadow-sm"><h2 className="mb-4 font-semibold">Equipo técnico · {estado.rows.length}</h2><div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {estado.rows.map((tecnico) => <article key={tecnico.id} className="rounded-xl border border-surface-container p-4">
          <h3 className="font-semibold">{tecnico.nombre}</h3><p className="text-body-sm text-secondary">{tecnico.especialidad}</p>
          <span className={`mt-4 inline-flex rounded-full px-3 py-1 text-label-sm ${COLORES[tecnico.estado]}`}>{ESTADOS_DISPONIBILIDAD[tecnico.estado]}</span>
          <p className="mt-3 text-body-sm text-secondary">{tecnico.horas_ocupadas} de {tecnico.horas_laborales} horas laborales reservadas</p>
          <p className="mt-2 text-body-sm text-secondary">{tecnico.obras.length ? tecnico.obras.map((o) => o.nombre).join(', ') : 'Sin obras asignadas en este período'}</p>
          {!!tecnico.sin_planificar.length && <p className="mt-2 text-body-sm text-tertiary">Complete las fechas de las obras sin planificación.</p>}
          <Link to={`/tecnicos/${tecnico.id}`} className="link-action mt-4">Ver perfil <span aria-hidden="true" className="material-symbols-outlined text-base">arrow_forward</span></Link>
        </article>)}
      </div>{!estado.rows.length && <p className="text-secondary">No hay técnicos activos registrados.</p>}</section>
    </>}
  </div>;
}