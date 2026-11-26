import { useEffect, useRef, useState } from 'react';
import { api } from '../api/client';

export default function DetalleOtrosCostos({ obra, format, onClose }) {
  const dialog = useRef(null);
  const [detalle, setDetalle] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    dialog.current.showModal();
    api.request(`/dashboard/obras/${obra.id}/otros-costos/`, { signal: controller.signal })
      .then((data) => { if (!controller.signal.aborted) setDetalle(data); })
      .catch((err) => { if (!controller.signal.aborted) setError(err.message); });
    return () => controller.abort();
  }, [obra.id]);

  return (
    <dialog ref={dialog} onClose={onClose} aria-labelledby="titulo-otros-costos"
      className="m-auto max-h-[85vh] w-[calc(100%-2rem)] max-w-2xl overflow-y-auto rounded-xl bg-surface-container-lowest p-5 text-on-surface shadow-xl backdrop:bg-black/40">
      <header className="flex items-start justify-between gap-4">
        <div>
          <h2 id="titulo-otros-costos" className="text-xl font-bold">Otros costos de la obra</h2>
          <p className="text-sm text-secondary">{obra.codigo_obra} · {obra.nombre_obra}</p>
        </div>
        <form method="dialog"><button className="rounded-lg bg-surface-container px-3 py-2">Cerrar</button></form>
      </header>
      <p className="mt-3 text-sm">Incluye subcontratos, equipamiento y gastos varios imputados a la obra.</p>
      {error && <p role="alert" className="mt-3 text-error">{error}</p>}
      {!detalle && !error && <p role="status" className="mt-3">Cargando detalle…</p>}
      {detalle?.registros.length === 0 && <p className="mt-3">Esta obra no tiene otros costos registrados.</p>}
      {detalle?.registros.length > 0 && (
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead><tr className="border-b">
              <th scope="col" className="p-2">Fecha</th>
              <th scope="col" className="p-2">Categoría</th>
              <th scope="col" className="p-2">Descripción</th>
              <th scope="col" className="p-2 text-right">Monto</th>
            </tr></thead>
            <tbody>{detalle.registros.map((costo) => (
              <tr key={costo.id} className="border-b align-top">
                <td className="whitespace-nowrap p-2">{costo.fecha.split('-').reverse().join('/')}</td>
                <td className="p-2">{costo.categoria}</td>
                <td className="p-2">{costo.descripcion}</td>
                <td className="whitespace-nowrap p-2 text-right">{format(costo.monto)}</td>
              </tr>
            ))}</tbody>
            <tfoot><tr>
              <th scope="row" colSpan={3} className="p-2">Total acumulado</th>
              <td className="whitespace-nowrap p-2 text-right font-semibold">{format(detalle.total)}</td>
            </tr></tfoot>
          </table>
        </div>
      )}
    </dialog>
  );
}
