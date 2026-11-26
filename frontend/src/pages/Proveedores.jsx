import { useEffect, useState } from 'react';
import { api } from '../api/client';
import TablePagination from '../components/TablePagination';
import { useTablePagination } from '../components/useTablePagination';

const nuevo = { rut: '', razon_social: '', correo: '', telefono: '', activo: true };
const campo = 'mt-1 block w-full rounded-lg bg-surface-container-low px-3 py-2';

export default function Proveedores({ userRole }) {
  const [proveedores, setProveedores] = useState(null);
  const [busqueda, setBusqueda] = useState('');
  const [form, setForm] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const editable = ['ADMIN_GENERAL', 'FINANZAS'].includes(userRole);
  const filtro = busqueda.trim().toLocaleLowerCase('es-CL');
  const visibles = (proveedores ?? []).filter((fila) => [fila.rut, fila.razon_social]
    .some((valor) => valor.toLocaleLowerCase('es-CL').includes(filtro)));
  const tabla = useTablePagination(visibles, { filterKey: filtro });

  useEffect(() => {
    let activo = true;
    api.listAll('/proveedores/').then((data) => { if (activo) setProveedores(data); })
      .catch((err) => { if (activo) setError(err.message); });
    return () => { activo = false; };
  }, []);

  async function guardar(event) {
    event.preventDefault();
    setBusy(true);
    setError('');
    const { id, ...body } = form;
    try {
      const registro = await api.request(id ? `/proveedores/${id}/` : '/proveedores/', {
        method: id ? 'PATCH' : 'POST', body,
      });
      setProveedores((actuales) => [...actuales.filter((fila) => fila.id !== registro.id), registro]
        .sort((a, b) => a.razon_social.localeCompare(b.razon_social, 'es-CL') || a.id - b.id));
      setForm(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto w-full max-w-6xl space-y-5 p-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-3xl font-bold">Proveedores</h1>
        {editable && <button type="button" disabled={!proveedores || busy} className="rounded-lg bg-primary-container px-4 py-2 text-on-primary"
          onClick={() => { setForm(nuevo); setError(''); }}>Nuevo proveedor</button>}
      </header>
      {error && <p role="alert" className="rounded-lg bg-error-container p-3 text-on-error-container">{error}</p>}
      {form && <form onSubmit={guardar} className="space-y-4 rounded-xl bg-surface-container-lowest p-4 shadow-sm">
        <h2 className="text-xl font-semibold">{form.id ? 'Editar proveedor' : 'Nuevo proveedor'}</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          <label>RUT<input className={campo} required maxLength={15} value={form.rut}
            onChange={(e) => setForm({ ...form, rut: e.target.value })} /></label>
          <label>Razón social<input className={campo} required maxLength={150} value={form.razon_social}
            onChange={(e) => setForm({ ...form, razon_social: e.target.value })} /></label>
          <label>Correo<input className={campo} type="email" value={form.correo}
            onChange={(e) => setForm({ ...form, correo: e.target.value })} /></label>
          <label>Teléfono<input className={campo} type="tel" maxLength={30} value={form.telefono}
            onChange={(e) => setForm({ ...form, telefono: e.target.value })} /></label>
        </div>
        <label className="flex items-center gap-2"><input type="checkbox" checked={form.activo}
          onChange={(e) => setForm({ ...form, activo: e.target.checked })} />Activo</label>
        <div className="flex gap-3">
          <button disabled={busy} className="rounded-lg bg-primary-container px-4 py-2 text-on-primary">Guardar proveedor</button>
          <button type="button" disabled={busy} onClick={() => setForm(null)} className="rounded-lg bg-surface-container px-4 py-2">Cancelar</button>
        </div>
      </form>}
      <section className="rounded-xl bg-surface-container-lowest p-4 shadow-sm">
        <label className="mb-3 block max-w-sm">Buscar por RUT o razón social
          <input type="search" className={campo} value={busqueda} onChange={(e) => setBusqueda(e.target.value)} />
        </label>
        {!proveedores && !error && <p role="status">Cargando proveedores…</p>}
        {proveedores && !visibles.length && <p>No hay proveedores para mostrar.</p>}
        <ul className="divide-y divide-surface-container">
          {tabla.rows.map((fila) => <li key={fila.id} className="flex flex-wrap justify-between gap-3 py-3">
            <div><strong>{fila.razon_social}</strong><p className="text-sm text-secondary">{fila.rut}{fila.correo && ` · ${fila.correo}`}{fila.telefono && ` · ${fila.telefono}`}</p></div>
            <div className="flex items-center gap-3 text-sm">{fila.activo ? 'Activo' : 'Inactivo'}
              {editable && <button type="button" disabled={busy} className="link-action" onClick={() => { setForm(fila); setError(''); }}>Editar</button>}
            </div>
          </li>)}
        </ul>
        <TablePagination table={tabla} label="Paginación de proveedores" />
      </section>
    </div>
  );
}
