import { useEffect, useState } from 'react';
import { api } from '../api/client';
import TablePagination from './TablePagination';
import { useTablePagination } from './useTablePagination';

const empty = { fecha: '', descripcion: '', monto: '' };
const field = 'block w-full rounded-lg bg-surface-container-low px-3 py-2';

export default function GastosGenerales({ editable, format }) {
  const [rows, setRows] = useState([]);
  const [form, setForm] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const table = useTablePagination(rows);

  useEffect(() => {
    let active = true;
    api.listAll('/gastos-generales/').then((gastos) => {
      if (active) setRows(gastos);
    }).catch((err) => { if (active) setError(err.message); });
    return () => { active = false; };
  }, []);

  async function guardar(event) {
    event.preventDefault();
    setBusy(true);
    setError('');
    const { id, ...body } = form;
    try {
      const gasto = await api.request(id ? `/gastos-generales/${id}/` : '/gastos-generales/', {
        method: id ? 'PATCH' : 'POST', body,
      });
      setRows((current) => [...current.filter((row) => row.id !== gasto.id), gasto]
        .sort((a, b) => b.fecha.localeCompare(a.fecha) || b.id - a.id));
      setForm(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="space-y-4 rounded-xl bg-surface-container-lowest p-4 shadow-sm">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div><h2 className="text-xl font-bold">Gastos generales</h2><p className="text-sm text-secondary">Gastos de la empresa sin imputación a una obra.</p></div>
        {editable && <button type="button" disabled={busy} className="rounded-lg bg-primary-container px-4 py-2 text-on-primary" onClick={() => setForm(empty)}>Registrar gasto general</button>}
      </header>
      {error && <p role="alert" className="text-error">{error}</p>}
      {form && <form onSubmit={guardar} className="space-y-3">
        <div className="grid gap-3 md:grid-cols-3">
          <label>Fecha<input required type="date" className={field} value={form.fecha} onChange={(e) => setForm({ ...form, fecha: e.target.value })} /></label>
          <label>Descripción<input required maxLength={255} className={field} value={form.descripcion} onChange={(e) => setForm({ ...form, descripcion: e.target.value })} /></label>
          <label>Monto (CLP)<input required type="number" min="1" max="999999999999" className={field} value={form.monto} onChange={(e) => setForm({ ...form, monto: e.target.value })} /></label>
        </div>
        <div className="flex gap-3">
          <button disabled={busy} className="rounded bg-primary-container px-4 py-2 text-on-primary">Guardar gasto</button>
          <button disabled={busy} type="button" className="px-4 py-2" onClick={() => setForm(null)}>Cancelar</button>
        </div>
      </form>}
      {rows.length ? <ul className="divide-y divide-surface-container">{table.rows.map((gasto) => (
        <li key={gasto.id} className="flex flex-wrap items-center justify-between gap-3 py-2">
          <span>{gasto.fecha} · {gasto.descripcion}</span>
          <div className="flex gap-3"><strong>{format(gasto.monto)}</strong>
            {editable && <button disabled={busy} type="button" className="link-action" onClick={() => setForm(gasto)}>Editar</button>}
          </div>
        </li>
      ))}</ul> : <p>Sin gastos generales registrados.</p>}
      <TablePagination table={table} label="Paginación de gastos generales" />
    </section>
  );
}
