import { useEffect, useState } from 'react';
import { api } from '../api/client';

const field = 'rounded bg-surface-container-low px-3 py-2';
const numberFormat = new Intl.NumberFormat('es-CL', { maximumFractionDigits: 3 });
const tiposMovimiento = { entrada: 'Entrada', consumo: 'Consumo', merma: 'Merma' };

export function SelectorMateriales({ servicio, seleccion, onChange }) {
  const [catalogo, setCatalogo] = useState(null);
  const [error, setError] = useState('');
  const [todos, setTodos] = useState(false);
  const [busqueda, setBusqueda] = useState('');

  useEffect(() => {
    let active = true;
    api.listAll('/materiales/?activo=1').then((rows) => {
      if (active) setCatalogo(rows);
    }).catch((err) => { if (active) setError(err.message); });
    return () => { active = false; };
  }, []);

  const filtro = busqueda.trim().toLocaleLowerCase('es-CL');
  const opciones = (catalogo ?? []).filter((material) =>
    (todos || !servicio || !material.servicios.length || material.servicios.includes(servicio))
    && material.nombre.toLocaleLowerCase('es-CL').includes(filtro)
    && !seleccion.some((item) => item.material === material.id),
  );

  const agregar = (event) => {
    const material = Number(event.target.value);
    if (material && seleccion.length < 10) {
      onChange([...seleccion, { material, cantidad_planificada: '' }]);
      setBusqueda('');
    }
  };

  return (
    <fieldset className="space-y-3 rounded-lg border border-outline-variant p-3">
      <legend className="px-1 font-semibold">Materiales ({seleccion.length}/10)</legend>
      {error && <p role="alert" className="text-error">{error}</p>}
      <label className="block">
        Buscar material
        <input type="search" className={field + ' mt-1 w-full'} value={busqueda} disabled={!catalogo || seleccion.length >= 10}
          onChange={(event) => setBusqueda(event.target.value)} />
      </label>
      <label className="block">
        Agregar material (opcional)
        <select className={field + ' mt-1 w-full'} value="" onChange={agregar}
          disabled={!catalogo || !opciones.length || seleccion.length >= 10}>
          <option value="">{!catalogo && !error ? 'Cargando catálogo…' : opciones.length ? 'Seleccionar material' : 'Sin materiales disponibles'}</option>
          {opciones.map((item) => <option key={item.id} value={item.id}>{item.nombre} ({item.unidad})</option>)}
        </select>
      </label>
      {servicio && <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" checked={todos} onChange={(event) => setTodos(event.target.checked)} />
        Mostrar materiales de todos los servicios
      </label>}
      {seleccion.map((item) => {
        const material = catalogo?.find((row) => row.id === item.material);
        return <div key={item.material} className="flex flex-wrap items-end gap-3">
          <label className="min-w-48 flex-1 text-sm">
            {material?.nombre} · Cantidad planificada ({material?.unidad})
            <input className={field + ' mt-1 block w-full'} type="number" required min="0.001" max="999999999.999"
              step="0.001" value={item.cantidad_planificada}
              onChange={(event) => onChange(seleccion.map((row) => row.material === item.material
                ? { ...row, cantidad_planificada: event.target.value } : row))} />
          </label>
          <button type="button" className="link-action link-action-danger" aria-label={`Quitar ${material?.nombre}`}
            onClick={() => onChange(seleccion.filter((row) => row.material !== item.material))}>Quitar</button>
        </div>;
      })}
    </fieldset>
  );
}

export function MaterialesObra({ obra, onClose, canRegisterWaste }) {
  const [rows, setRows] = useState(null);
  const [error, setError] = useState('');
  const [asignacion, setAsignacion] = useState(null);
  const [tipo, setTipo] = useState('entrada');
  const [busy, setBusy] = useState(false);
  const path = `/obras/${obra.id}/materiales/`;
  const editable = canRegisterWaste && obra.estado_operativo === 'en-proceso' && obra.estado_comercial !== 'cerrada';

  useEffect(() => {
    let active = true;
    api.request(path).then((data) => { if (active) setRows(data); })
      .catch((err) => { if (active) setError(err.message); });
    return () => { active = false; };
  }, [path]);

  async function guardarMovimiento(event) {
    event.preventDefault();
    const { cantidad, motivo, referencia } = Object.fromEntries(new FormData(event.currentTarget));
    setBusy(true);
    setError('');
    try {
      const esMerma = tipo === 'merma';
      const resultado = await api.request(`${path}${asignacion.id}/${esMerma ? 'mermas' : 'movimientos'}/`, {
        method: 'POST', body: esMerma ? { cantidad, motivo } : { cantidad, motivo, tipo, referencia },
      });
      setRows((current) => current.map((row) => {
        if (row.id !== asignacion.id) return row;
        return esMerma ? { ...row, saldo: resultado.saldo, mermas: [resultado, ...row.mermas] } : resultado;
      }));
      setAsignacion(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  function abrirMovimiento(row, nuevoTipo) {
    setAsignacion(row);
    setTipo(nuevoTipo);
    setError('');
  }

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/40 p-4">
      <section role="dialog" aria-modal="true" aria-labelledby="titulo-materiales-obra"
        className="max-h-[90vh] w-full max-w-2xl space-y-4 overflow-y-auto rounded-xl bg-surface-container-lowest p-6">
        <header className="flex items-start justify-between gap-4">
          <div><h2 id="titulo-materiales-obra" className="text-xl font-bold">Materiales de la obra</h2><p>{obra.nombre_obra}</p></div>
          <button type="button" className={field} onClick={onClose} disabled={busy}>Cerrar</button>
        </header>
        {error && <p role="alert" className="text-error">{error}</p>}
        {!rows && !error && <p role="status">Cargando materiales…</p>}
        {rows?.length === 0 && <p>Esta obra no tiene materiales asignados.</p>}
        {rows?.map((row) => <article key={row.id} className="rounded-lg border border-outline-variant p-3">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <h3 className="font-semibold">{row.material.nombre}</h3>
              <p>Planificado · {numberFormat.format(row.cantidad_planificada)} {row.material.unidad}</p>
            </div>
            {editable && <div className="flex flex-wrap gap-3 text-sm">
              <button type="button" className="link-action" disabled={busy} onClick={() => abrirMovimiento(row, 'entrada')}>Registrar entrada</button>
              {Number(row.saldo) > 0 && <button type="button" className="link-action" disabled={busy} onClick={() => abrirMovimiento(row, 'consumo')}>Registrar consumo</button>}
              {(row.saldo === null || Number(row.saldo) > 0) && <button type="button" className="link-action" disabled={busy} onClick={() => abrirMovimiento(row, 'merma')}>Registrar merma</button>}
            </div>}
          </div>
          <p className="mt-2 font-semibold">Saldo registrado · {row.saldo === null
            ? 'Sin entradas registradas' : `${numberFormat.format(row.saldo)} ${row.material.unidad}`}</p>
          <p className="mt-2 font-medium">Merma registrada · {numberFormat.format(row.mermas.reduce((total, entry) => total + Number(entry.cantidad), 0))} {row.material.unidad}</p>
          {row.mermas.length > 0 && <ul className="mt-1 space-y-1 text-sm">
            {row.mermas.map((entry) => <li key={entry.id}>{entry.fecha} · {numberFormat.format(entry.cantidad)} {row.material.unidad} · {entry.motivo}</li>)}
          </ul>}
          {row.movimientos.length > 0 && <ul className="mt-2 space-y-1 text-sm" aria-label="Entradas y consumos">
            {row.movimientos.map((entry) => <li key={entry.id}>
              {tiposMovimiento[entry.tipo]} · {new Date(entry.fecha).toLocaleString('es-CL')} · {numberFormat.format(entry.cantidad)} {row.material.unidad} · {entry.motivo}
              {entry.referencia && <> · Ref. {entry.referencia}</>}
            </li>)}
          </ul>}
          {editable && asignacion?.id === row.id && <form key={tipo} className="mt-3 space-y-2" onSubmit={guardarMovimiento}>
            <h4 className="font-semibold">{tiposMovimiento[tipo]}</h4>
            {tipo === 'entrada' && row.saldo === null && <p className="text-sm">Para iniciar el saldo, ingresa la cantidad disponible hoy más las mermas ya registradas.</p>}
            <label className="block">Cantidad ({row.material.unidad})<input className={field + ' block w-full'} name="cantidad" type="number" min="0.001" max="999999999.999" step="0.001" required /></label>
            <label className="block">Motivo<input className={field + ' block w-full'} name="motivo" maxLength={255} required /></label>
            {tipo === 'entrada' && <label className="block">Referencia del despacho<input className={field + ' block w-full'}
              name="referencia" maxLength={100} required placeholder="Guía, folio o referencia interna" /></label>}
            <button className="rounded bg-primary-container px-3 py-2 text-on-primary" disabled={busy}>{busy ? 'Guardando…' : 'Guardar movimiento'}</button>
            <button type="button" className="px-3 py-2" disabled={busy} onClick={() => setAsignacion(null)}>Cancelar</button>
          </form>}
        </article>)}
      </section>
    </div>
  );
}
