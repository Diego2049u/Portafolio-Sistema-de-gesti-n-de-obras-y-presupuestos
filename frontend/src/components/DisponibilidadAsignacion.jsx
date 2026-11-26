import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, withQuery } from '../api/client';
import { claveConsulta, ESTADOS_DISPONIBILIDAD } from './calendario/agenda';

const input = 'mt-1 block w-full rounded-lg bg-surface-container-low px-3 py-2';
const fechaHora = (valor) => new Date(valor).toLocaleString('es-CL', { timeZone: 'America/Santiago', dateStyle: 'medium', timeStyle: 'short' });

export default function DisponibilidadAsignacion({ form, setForm, onResultado }) {
  const [consulta, setConsulta] = useState({ rows: [], loading: true, error: '' });
  const inicio = form.inicio_programado, fin = form.fin_estimado, tecnicoId = form.tecnico_responsable, excluir = form.id;
  const clave = claveConsulta(form);
  useEffect(() => {
    let vigente = true;
    async function consultar() {
      const cargando = { rows: [], loading: true, error: '', clave };
      setConsulta(cargando); onResultado(cargando);
      try {
        if (!inicio || !fin || inicio >= fin) throw new Error('Indique un inicio y un término estimado posterior al inicio.');
        const rows = await api.request(withQuery('/obras/tecnicos-disponibles/', { inicio, fin, excluir }));
        if (!vigente) return;
        const seleccionado = rows.find((t) => String(t.id) === String(tecnicoId));
        const resultado = { rows, loading: false, error: '', clave, asignable: !tecnicoId || !!seleccionado?.asignable };
        setConsulta(resultado); onResultado(resultado);
      } catch (error) {
        if (vigente) { const resultado = { rows: [], loading: false, error: error.message, clave }; setConsulta(resultado); onResultado(resultado); }
      }
    }
    const timer = setTimeout(consultar, 250);
    return () => { vigente = false; clearTimeout(timer); };
  }, [inicio, fin, tecnicoId, excluir, clave, onResultado]);
  const seleccionado = consulta.rows.find((t) => String(t.id) === String(tecnicoId));
  return <div className="space-y-3">
    <div className="grid gap-3 sm:grid-cols-2">
      <label>Inicio programado<input required type="datetime-local" className={input} value={inicio || ''} onChange={(e) => setForm({ ...form, inicio_programado: e.target.value })} /></label>
      <label>Término estimado<input required type="datetime-local" className={input} value={fin || ''} onChange={(e) => setForm({ ...form, fin_estimado: e.target.value })} /></label>
    </div>
    <p className="text-body-sm text-secondary">Hora de Chile. Se reservan las horas de lunes a viernes, 08:00–13:00 y 14:00–18:00; no se excluyen feriados.</p>
    <label className="block">Técnico responsable<select className={input} value={tecnicoId || ''} onChange={(e) => setForm({ ...form, tecnico_responsable: e.target.value })}>
      <option value="">Sin asignar</option>
      {tecnicoId && !seleccionado && <option value={tecnicoId}>Técnico seleccionado</option>}
      {consulta.rows.map((t) => <option key={t.id} value={t.id}>{t.nombre} — {t.asignable ? 'Disponible para asignar' : t.estado === 'sin_determinar' ? ESTADOS_DISPONIBILIDAD[t.estado] : 'Tiene cruces de horario'}</option>)}
    </select></label>
    {consulta.loading && <p role="status" className="text-secondary">Consultando disponibilidad…</p>}
    {consulta.error && <p role="alert" className="text-error">{consulta.error}</p>}
    {seleccionado && <div className={`rounded-lg p-3 text-body-sm ${seleccionado.asignable ? 'bg-emerald-50 text-emerald-800' : 'bg-error-container text-on-error-container'}`}>
      <p className="font-semibold">{seleccionado.asignable ? `${seleccionado.nombre} está disponible para todo el período.` : `${seleccionado.nombre} no está disponible para todo el período. Cambia el técnico o ajusta las fechas.`}</p>
      {!!seleccionado.conflictos.length && <ul className="mt-2 max-h-40 space-y-1 overflow-y-auto">{seleccionado.conflictos.map((c, i) => <li key={i}>{c.obra}: {fechaHora(c.inicio)} – {fechaHora(c.fin)}</li>)}</ul>}
      {!!seleccionado.sin_planificar.length && <p className="mt-2">Completa primero la planificación de: {seleccionado.sin_planificar.map((o) => o.nombre).join(', ')}.</p>}
      <Link className="link-action mt-2" to={`/tecnicos/${seleccionado.id}`} target="_blank" rel="noreferrer">Ver calendario del técnico</Link>
    </div>}
  </div>;
}
