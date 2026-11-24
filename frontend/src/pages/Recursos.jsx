import { useEffect, useState } from 'react';
import { api } from '../api/client';

const input = 'mt-1 block w-full rounded-lg bg-surface-container-low px-3 py-2';
const empty = { nombre: '', unidad: '', servicios: [], activo: true };

export default function Recursos({ userRole }) {
  const [rows, setRows] = useState(null);
  const [categorias, setCategorias] = useState([]);
  const [form, setForm] = useState(null);
  const [query, setQuery] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const manager = userRole === 'ADMIN_GENERAL';

  useEffect(() => {
    let active = true;
    api.listAll('/materiales/').then((data) => { if (active) setRows(data); })
      .catch((err) => { if (active) setError(err.message); });
    if (manager) {
      api.listAll('/categorias-servicio/').then((data) => { if (active) setCategorias(data); })
        .catch((err) => { if (active) setError(err.message); });
    }
    return () => { active = false; };
  }, [manager]);

  async function guardar(event) {
    event.preventDefault();
    setBusy(true);
    setError('');
    const { id, ...body } = form;
    try {
      const material = await api.request(id ? `/materiales/${id}/` : '/materiales/', {
        method: id ? 'PATCH' : 'POST', body,
      });
      setRows((current) => [...(current ?? []).filter((row) => row.id !== material.id), material]
        .sort((a, b) => a.nombre.localeCompare(b.nombre, 'es-CL')));
      setForm(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const filtro = query.trim().toLocaleLowerCase('es-CL');
  const visible = rows?.filter((row) => [row.nombre, row.unidad, ...row.servicios].some(
    (value) => value.toLocaleLowerCase('es-CL').includes(filtro),
  ));
  const opcionesServicio = [...new Set([...categorias.map((item) => item.nombre), ...(form?.servicios ?? [])])];

  return (
    <div className="mx-auto flex w-full max-w-[1600px] flex-col gap-6 p-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div><h1 className="text-3xl font-bold text-on-surface">Recursos</h1><p className="mt-1 text-on-surface-variant">Catálogo de materiales para asignar a obras.</p></div>
        {manager && <button type="button" className="rounded-lg bg-primary-container px-4 py-2 text-on-primary"
          disabled={busy || !rows} onClick={() => { setForm(empty); setError(''); }}>Nuevo material</button>}
      </header>
      {error && <p role="alert" className="rounded-lg bg-error-container p-3 text-on-error-container">{error}</p>}
      {form && <form onSubmit={guardar} className="space-y-4 rounded-xl bg-surface-container-lowest p-4 shadow-sm">
        <h2 className="text-xl font-bold">{form.id ? 'Editar material' : 'Nuevo material'}</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          <label>Nombre<input className={input} required maxLength={120} value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} /></label>
          <label>Unidad de medida<input className={input} required maxLength={20} value={form.unidad} onChange={(e) => setForm({ ...form, unidad: e.target.value })} /></label>
        </div>
        <fieldset>
          <legend>Servicios sugeridos</legend>
          <div className="mt-2 flex flex-wrap gap-x-4 gap-y-2">
            {opcionesServicio.map((nombre) => <label key={nombre} className="flex items-center gap-2">
              <input type="checkbox" checked={form.servicios.includes(nombre)} onChange={(e) => setForm({
                ...form, servicios: e.target.checked ? [...form.servicios, nombre] : form.servicios.filter((item) => item !== nombre),
              })} />{nombre}
            </label>)}
            {!opcionesServicio.length && <p className="text-sm text-secondary">Sin servicios disponibles.</p>}
          </div>
        </fieldset>
        <label className="flex items-center gap-2"><input type="checkbox" checked={form.activo} onChange={(e) => setForm({ ...form, activo: e.target.checked })} />Activo</label>
        <div className="flex gap-3">
          <button className="rounded-lg bg-primary-container px-4 py-2 text-on-primary" disabled={busy}>{busy ? 'Guardando…' : 'Guardar'}</button>
          <button type="button" className="rounded px-4 py-2" disabled={busy} onClick={() => setForm(null)}>Cancelar</button>
        </div>
      </form>}
      <section className="rounded-xl bg-surface-container-lowest p-4 shadow-sm">
        <label className="mb-4 block max-w-md">Buscar en el catálogo<input className={input} value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Material, unidad o servicio" /></label>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead><tr className="border-b text-xs uppercase text-secondary">
              <th className="p-3">Material</th><th className="p-3">Unidad</th><th className="p-3">Servicios sugeridos</th><th className="p-3">Estado</th>
              {manager && <th className="p-3">Acciones</th>}
            </tr></thead>
            <tbody>{visible?.map((row) => <tr key={row.id} className="border-b border-surface-container">
              <td className="p-3 font-medium">{row.nombre}</td><td className="p-3">{row.unidad}</td>
              <td className="p-3">{row.servicios.join(', ') || 'Todos los servicios'}</td>
              <td className="p-3">{row.activo ? 'Activo' : 'Inactivo'}</td>
              {manager && <td className="p-3"><button type="button" className="text-primary" disabled={busy}
                onClick={() => { setForm(row); setError(''); }}>Editar</button></td>}
            </tr>)}</tbody>
          </table>
          {!rows && !error && <p role="status" className="p-4">Cargando catálogo…</p>}
          {visible?.length === 0 && <p className="p-4">No hay materiales para mostrar.</p>}
        </div>
      </section>
    </div>
  );
}
