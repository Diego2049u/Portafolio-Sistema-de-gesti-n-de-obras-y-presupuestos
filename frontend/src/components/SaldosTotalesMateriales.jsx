import { useEffect, useRef, useState } from 'react';
import { api } from '../api/client';
import TablePagination from './TablePagination';
import { useTablePagination } from './useTablePagination';

const cantidad = new Intl.NumberFormat('es-CL', { maximumFractionDigits: 3 });

function mostrarSaldo(saldo, unidad) {
  return saldo === null ? 'Sin entradas registradas' : `${cantidad.format(saldo)} ${unidad}`;
}

export default function SaldosTotalesMateriales({ onClose }) {
  const dialog = useRef(null);
  const [materiales, setMateriales] = useState(null);
  const [busqueda, setBusqueda] = useState('');
  const [error, setError] = useState('');
  const filtro = busqueda.trim().toLocaleLowerCase('es-CL');
  const visibles = (materiales ?? []).filter((material) => material.nombre.toLocaleLowerCase('es-CL').includes(filtro));
  const tabla = useTablePagination(visibles, { filterKey: filtro });

  useEffect(() => {
    const controller = new AbortController();
    dialog.current.showModal();
    api.request('/materiales/saldos-totales/', { signal: controller.signal })
      .then((data) => { if (!controller.signal.aborted) setMateriales(data); })
      .catch((err) => { if (!controller.signal.aborted) setError(err.message); });
    return () => controller.abort();
  }, []);

  return (
    <dialog ref={dialog} onClose={onClose} aria-labelledby="titulo-saldos-totales"
      className="historial-obra m-auto max-h-[85vh] w-[calc(100%-2rem)] max-w-3xl overflow-y-auto rounded-xl bg-surface-container-lowest p-5 text-on-surface shadow-xl">
      <header className="flex items-start justify-between gap-4">
        <div>
          <h2 id="titulo-saldos-totales" className="text-xl font-bold">Saldos totales por material</h2>
          <p className="text-sm text-secondary">Suma de los saldos registrados en las obras, descontando consumos y mermas.</p>
        </div>
        <form method="dialog"><button className="rounded-lg bg-surface-container px-3 py-2">Cerrar</button></form>
      </header>
      {error && <p role="alert" className="mt-4 text-error">{error}</p>}
      {!materiales && !error && <p role="status" className="mt-4">Cargando saldos…</p>}
      {materiales && <>
        <label className="mt-4 block max-w-sm">Buscar material
          <input type="search" value={busqueda} onChange={(event) => setBusqueda(event.target.value)}
            className="mt-1 block w-full rounded-lg bg-surface-container-low px-3 py-2" />
        </label>
        {visibles.length === 0 && <p className="mt-4">No hay materiales para mostrar.</p>}
        <ul className="mt-4 divide-y divide-surface-container">
          {tabla.rows.map((material) => (
            <li key={material.id} className="py-3">
              <div className="flex flex-wrap justify-between gap-x-4">
                <h3 className="font-semibold">{material.nombre}</h3>
                <p>{material.obras.length ? mostrarSaldo(material.saldo, material.unidad) : 'Sin asignaciones'}</p>
              </div>
              {material.sin_entradas > 0 && <p className="text-sm text-secondary">
                {material.saldo !== null && 'Total parcial · '}{material.sin_entradas} {material.sin_entradas === 1 ? 'obra' : 'obras'} sin entradas registradas
              </p>}
              {material.obras.length > 0 && <details className="mt-1 text-sm">
                <summary className="cursor-pointer text-primary">Ver desglose por obra</summary>
                <ul className="mt-1 space-y-1 pl-4">
                  {material.obras.map((obra) => (
                    <li key={obra.codigo} className="flex flex-wrap justify-between gap-x-4">
                      <span>{obra.codigo} · {obra.nombre}</span>
                      <span>{mostrarSaldo(obra.saldo, material.unidad)}</span>
                    </li>
                  ))}
                </ul>
              </details>}
            </li>
          ))}
        </ul>
        <TablePagination label="Paginación de saldos de materiales" table={tabla} />
      </>}
    </dialog>
  );
}
