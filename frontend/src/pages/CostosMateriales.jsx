import { useMemo, useState } from 'react';
import MainLayout from '../components/layout';

const OBRAS = [
  { id: 'OBR-2026-104', nombre: 'CMPC Celulosa Planta Pacífico' },
  { id: 'OBR-2026-103', nombre: 'Minera Los Pelambres' },
  { id: 'OBR-2026-101', nombre: 'Hospital Clínico' },
  { id: 'OBR-2026-088', nombre: 'Planta Solar Quillota' },
];
const CATEGORIAS = ['MATERIALES', 'MANO_DE_OBRA', 'SUBCONTRATO', 'EQUIPAMIENTO', 'VARIOS'];
const CLP = new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 0 });
const INITIAL_COSTS = [
  { id: 1, obraId: OBRAS[0].id, categoria: 'MATERIALES', monto: 150000, descripcion: 'Cableado Tablero Fuerza', comprobante: 'https://fyag.cl/comprobantes/imp-089.pdf', fecha: '18/10/2026' },
  { id: 2, obraId: OBRAS[1].id, categoria: 'SUBCONTRATO', monto: 840000, descripcion: 'Instalación de ductos eléctricos', comprobante: 'https://fyag.cl/comprobantes/imp-087.pdf', fecha: '17/10/2026' },
];
const FIELD = 'w-full rounded-lg border border-surface-container bg-surface-container-low px-3 py-2 text-on-surface focus:outline-none focus:ring-2 focus:ring-primary';

export default function CostosMateriales({ userRole = 'GERENCIA' }) {
  const canImputeCost = userRole === 'FINANZAS' || userRole === 'SUPERVISOR';
  const [costos, setCostos] = useState(INITIAL_COSTS);
  const [modalAbierto, setModalAbierto] = useState(false);
  const [obraId, setObraId] = useState(OBRAS[0].id);
  const [categoria, setCategoria] = useState(CATEGORIAS[0]);
  const [monto, setMonto] = useState('');
  const [descripcion, setDescripcion] = useState('');
  const [comprobante, setComprobante] = useState('');
  const [mensaje, setMensaje] = useState('');
  const total = useMemo(() => costos.reduce((suma, costo) => suma + costo.monto, 0), [costos]);

  const guardarCosto = (event) => {
    event.preventDefault();
    const obra = OBRAS.find((item) => item.id === obraId);
    setCostos((actuales) => [{ id: Date.now(), obraId, obraNombre: obra?.nombre, categoria, monto: Number(monto), descripcion, comprobante, fecha: new Date().toLocaleDateString('es-CL') }, ...actuales]);
    setMonto(''); setDescripcion(''); setComprobante(''); setModalAbierto(false);
    setMensaje('Costo directo imputado a la obra.');
    window.setTimeout(() => setMensaje(''), 3000);
  };

  return (
    <MainLayout breadcrumb="Costos y Materiales de Obra" period="Q4-2026">
      <div className="mx-auto flex w-full max-w-[1600px] flex-col gap-6">
        <header className="flex flex-wrap items-end justify-between gap-4">
          <div><span className="text-label-sm font-semibold uppercase tracking-wider text-primary">Costos ejecutados por obra</span><h1 className="mt-1 text-headline-lg font-bold text-on-surface">Costos y Materiales</h1><p className="mt-1 text-body-md text-on-surface-variant">Registro de gastos directos vinculados a cada obra.</p></div>
          {canImputeCost && <button onClick={() => setModalAbierto(true)} type="button" className="rounded-lg bg-primary-container px-4 py-2.5 font-semibold text-on-primary shadow-sm hover:bg-primary">+ Imputar Costo a Obra</button>}
        </header>

        <section className="grid gap-4 sm:grid-cols-2"><article className="rounded-xl bg-surface-container-lowest p-5 shadow-sm"><span className="text-label-sm uppercase text-secondary">Gasto registrado</span><div className="mt-2 text-headline-lg font-bold text-on-surface">{CLP.format(total)}</div></article><article className="rounded-xl bg-surface-container-lowest p-5 shadow-sm"><span className="text-label-sm uppercase text-secondary">Imputaciones</span><div className="mt-2 text-headline-lg font-bold text-on-surface">{costos.length}</div></article></section>

        <section className="overflow-hidden rounded-xl bg-surface-container-lowest shadow-sm">
          <div className="border-b border-surface-container p-5"><h2 className="font-semibold text-on-surface">Gastos ejecutados por categoría</h2><p className="mt-1 text-body-sm text-secondary">Cada registro queda asociado a la ficha de su obra.</p></div>
          <div className="overflow-x-auto"><table className="w-full text-left text-body-sm"><thead className="bg-surface-container-low text-label-sm uppercase text-secondary"><tr><th className="p-4">Fecha</th><th className="p-4">Obra</th><th className="p-4">Categoría</th><th className="p-4">Descripción</th><th className="p-4 text-right">Monto (CLP)</th><th className="p-4">Comprobante</th></tr></thead><tbody className="divide-y divide-surface-container">{costos.map((costo) => { const obra = OBRAS.find((item) => item.id === costo.obraId); return <tr key={costo.id}><td className="p-4">{costo.fecha}</td><td className="p-4"><strong>{costo.obraId}</strong><div className="text-secondary">{costo.obraNombre || obra?.nombre}</div></td><td className="p-4">{costo.categoria}</td><td className="p-4">{costo.descripcion}</td><td className="p-4 text-right font-semibold">{CLP.format(costo.monto)}</td><td className="p-4">{costo.comprobante ? <a className="text-primary underline" href={costo.comprobante} target="_blank" rel="noreferrer">Ver comprobante</a> : '—'}</td></tr>; })}</tbody></table></div>
        </section>
      </div>

      {modalAbierto && canImputeCost && <div className="fixed inset-0 z-50 flex items-center justify-center bg-inverse-surface/50 p-4" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setModalAbierto(false); }}><form onSubmit={guardarCosto} className="w-full max-w-xl space-y-5 rounded-xl bg-surface-container-lowest p-6 shadow-2xl" role="dialog" aria-modal="true" aria-labelledby="cost-modal-title"><header className="flex items-start justify-between"><div><h2 id="cost-modal-title" className="text-headline-md font-bold text-on-surface">Imputar Costo Directo a Obra</h2><p className="mt-1 text-body-sm text-secondary">El gasto se registra en la ficha de la obra seleccionada.</p></div><button type="button" onClick={() => setModalAbierto(false)} aria-label="Cerrar" className="text-secondary">✕</button></header>
        <label className="block text-label-md font-semibold">Obra ID / Nombre<select className={`${FIELD} mt-1`} value={obraId} onChange={(event) => setObraId(event.target.value)} required>{OBRAS.map((obra) => <option key={obra.id} value={obra.id}>{obra.id} — {obra.nombre}</option>)}</select></label>
        <label className="block text-label-md font-semibold">Categoría de Gasto<select className={`${FIELD} mt-1`} value={categoria} onChange={(event) => setCategoria(event.target.value)}>{CATEGORIAS.map((item) => <option key={item}>{item}</option>)}</select></label>
        <label className="block text-label-md font-semibold">Monto (CLP)<input className={`${FIELD} mt-1`} type="number" min="1" step="1" value={monto} onChange={(event) => setMonto(event.target.value)} required /></label>
        <label className="block text-label-md font-semibold">Descripción del Gasto<textarea className={`${FIELD} mt-1`} rows="3" value={descripcion} onChange={(event) => setDescripcion(event.target.value)} required /></label>
        <label className="block text-label-md font-semibold">URL / Archivo de Comprobante<input className={`${FIELD} mt-1`} type="url" placeholder="https://…" value={comprobante} onChange={(event) => setComprobante(event.target.value)} /></label>
        <div className="flex justify-end gap-3"><button type="button" onClick={() => setModalAbierto(false)} className="rounded-lg bg-surface-container px-4 py-2 text-on-surface">Cancelar</button><button type="submit" className="rounded-lg bg-primary-container px-4 py-2 font-semibold text-on-primary">Guardar imputación</button></div>
      </form></div>}
      {mensaje && <div className="fixed bottom-6 right-6 rounded-lg bg-inverse-surface px-4 py-3 text-inverse-on-surface shadow-xl" role="status">{mensaje}</div>}
    </MainLayout>
  );
}
