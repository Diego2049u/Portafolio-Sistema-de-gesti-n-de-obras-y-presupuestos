const TECNICOS = [
  { id: 'carlos', nombre: 'Carlos Araya', rut: '16.892.441-K', especialidad: 'Climatización', iniciales: 'CA', estado: 'OCUPADO (1 Obra)', color: 'bg-primary-container text-on-primary', obras: [{ nombre: 'CMPC Celulosa - Planta Pacífico', avance: 68, termino: '30/11/2026' }] },
  { id: 'eduardo', nombre: 'Eduardo Vera', rut: '15.234.890-2', especialidad: 'Mantenimiento', iniciales: 'EV', estado: 'LIBERADO', color: 'bg-secondary-container text-on-secondary-fixed', obras: [] },
  { id: 'felipe', nombre: 'Felipe Rivas', rut: '18.123.456-7', especialidad: 'Redes Eléctricas', iniciales: 'FR', estado: 'OCUPADO (1 Obra)', color: 'bg-tertiary-fixed text-tertiary', obras: [{ nombre: 'Viña Concha y Toro S.A.', avance: 42, termino: '15/12/2026' }] },
  { id: 'patricio', nombre: 'Patricio Silva', rut: '14.567.890-1', especialidad: 'Climatización', iniciales: 'PS', estado: 'LIBERADO', color: 'bg-surface-container-high text-primary', obras: [] },
  { id: 'camilo', nombre: 'Camilo Morales', rut: '17.456.123-8', especialidad: 'Mantenimiento', iniciales: 'CM', estado: 'SOBRECARGADO', color: 'bg-error-container text-on-error-container', obras: [{ nombre: 'Hospital Clínico del Sur', avance: 55, termino: '22/11/2026' }, { nombre: 'Mantención Planta Norte', avance: 30, termino: '08/12/2026' }] },
];

export const TECNICOS_REGISTRADOS = TECNICOS;
export const buscarTecnico = (nombre) => TECNICOS.find((tecnico) => tecnico.nombre.toLowerCase() === nombre?.toLowerCase()) || TECNICOS[0];

export default function TecnicoFichaModal({ tecnico, onClose }) {
  if (!tecnico) return null;
  return <div className="fixed inset-0 z-50 flex items-center justify-center bg-inverse-surface/50 p-4" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <section className="w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl bg-surface-container-lowest p-6 shadow-2xl" role="dialog" aria-modal="true" aria-labelledby="tecnico-ficha-title">
      <header className="flex items-start justify-between gap-4"><div className="flex items-center gap-4"><div className="flex h-20 w-20 shrink-0 items-center justify-center rounded-full bg-primary-container text-2xl font-bold text-on-primary">{tecnico.iniciales}</div><div><p className="text-label-sm font-semibold uppercase tracking-wide text-primary">Ficha técnica de disponibilidad</p><h2 id="tecnico-ficha-title" className="mt-1 text-headline-md font-bold text-on-surface">{tecnico.nombre}</h2><p className="text-body-sm text-secondary">RUT {tecnico.rut} · {tecnico.especialidad}</p></div></div><button type="button" onClick={onClose} aria-label="Cerrar ficha" className="rounded-lg p-2 text-secondary hover:bg-surface-container"><span className="material-symbols-outlined">close</span></button></header>
      <div className="mt-5"><span className={`inline-flex rounded-full px-3 py-1 text-label-sm font-semibold ${tecnico.color}`}>{tecnico.estado}</span></div>
      <div className="mt-6"><h3 className="font-headline-sm font-bold text-on-surface">Obras actualmente asignadas</h3>{tecnico.obras.length ? <ul className="mt-3 space-y-3">{tecnico.obras.map((obra) => <li key={obra.nombre} className="rounded-xl bg-surface-container-low p-4"><div className="flex items-start justify-between gap-3"><span className="font-semibold text-on-surface">{obra.nombre}</span><span className="font-mono text-sm font-bold text-primary">{obra.avance}%</span></div><div className="mt-2 h-2 overflow-hidden rounded-full bg-surface-container"><div className="h-full rounded-full bg-primary-container" style={{ width: `${obra.avance}%` }} /></div><p className="mt-2 text-label-sm text-secondary">Término estimado: {obra.termino}</p></li>)}</ul> : <p className="mt-3 rounded-xl bg-surface-container-low p-4 text-body-sm text-secondary">Sin obras asignadas actualmente.</p>}</div>
    </section>
  </div>;
}
