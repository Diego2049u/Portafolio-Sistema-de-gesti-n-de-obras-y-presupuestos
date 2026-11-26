import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';

const moneda = new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP' });
const fecha = (valor) => valor?.split('-').reverse().join('/');
const dias = (valor) => `${valor} ${valor === 1 ? 'día' : 'días'}`;

export default function AlertasFinancieras() {
  const dialog = useRef(null);
  const consultar = useRef(null);
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    let enCurso = false;
    async function actualizar() {
      if (enCurso || document.hidden) return;
      enCurso = true;
      try {
        const pendientes = await api.request('/facturas/pendientes/', { signal: controller.signal });
        if (!controller.signal.aborted) {
          setDatos(pendientes);
          setError('');
        }
      } catch (err) {
        if (!controller.signal.aborted) setError(err.message);
      } finally {
        enCurso = false;
      }
    }
    consultar.current = actualizar;
    actualizar();
    const intervalo = window.setInterval(actualizar, 60_000);
    document.addEventListener('visibilitychange', actualizar);
    return () => {
      controller.abort();
      window.clearInterval(intervalo);
      document.removeEventListener('visibilitychange', actualizar);
    };
  }, []);

  const total = datos ? datos.facturacion.length + datos.cobranza.length : 0;

  return (
    <>
      <button type="button" className="rounded-lg bg-surface-container-low px-2 py-1 text-sm text-primary"
        aria-haspopup="dialog" aria-label={`Pendientes de facturación y cobranza. ${total} avisos`}
        onClick={() => { dialog.current.showModal(); consultar.current?.(); }}>
        <span className="material-symbols-outlined align-middle text-base" aria-hidden="true">notifications</span>
        {total > 0 && <span className="ml-1 font-semibold">{total}</span>}
      </button>
      <dialog ref={dialog} aria-labelledby="titulo-alertas-financieras"
        className="historial-obra m-auto max-h-[85vh] w-[calc(100%-2rem)] max-w-2xl overflow-y-auto rounded-xl bg-surface-container-lowest p-5 text-on-surface shadow-xl">
        <header className="flex items-start justify-between gap-3">
          <h2 id="titulo-alertas-financieras" className="text-xl font-bold">Pendientes de facturación y cobranza</h2>
          <form method="dialog"><button className="rounded-lg bg-surface-container px-3 py-2">Cerrar</button></form>
        </header>
        {error && <p role="alert" className="mt-3 text-error">No se pudieron actualizar los avisos. {error}</p>}
        {!datos && !error && <p role="status" className="mt-3">Consultando pendientes…</p>}
        {datos && <div className="mt-4 space-y-5">
          <section>
            <h3 className="font-semibold">Obras pendientes de facturar</h3>
            {datos.facturacion.length === 0 && <p className="text-sm text-secondary">Sin obras pendientes.</p>}
            <ul className="divide-y divide-surface-container">{datos.facturacion.map((obra) => (
              <li key={obra.id} className="flex flex-wrap justify-between gap-x-4 py-2 text-sm">
                <div><strong>{obra.codigo} · {obra.nombre}</strong><p>{obra.cliente}</p></div>
                <div>
                  <p>{obra.tiene_factura ? 'Facturación incompleta' : 'Sin factura'} · {moneda.format(obra.saldo)}</p>
                  <p className="text-secondary">{obra.dias === null
                    ? 'Sin fecha de finalización' : `Finalizada el ${fecha(obra.fecha_termino)} · ${dias(obra.dias)}`}</p>
                </div>
              </li>
            ))}</ul>
          </section>
          <section>
            <h3 className="font-semibold">Facturas vencidas o por vencer en 7 días</h3>
            {datos.cobranza.length === 0 && <p className="text-sm text-secondary">Sin facturas por revisar.</p>}
            <ul className="divide-y divide-surface-container">{datos.cobranza.map((factura) => (
              <li key={factura.id} className="flex flex-wrap justify-between gap-x-4 py-2 text-sm">
                <div><strong>{factura.numero}</strong><p>{factura.cliente}</p></div>
                <div>
                  <p>{moneda.format(factura.saldo)} por cobrar · {fecha(factura.vencimiento)}</p>
                  <p className={factura.dias < 0 ? 'text-error' : 'text-secondary'}>
                    {factura.dias < 0 ? `Vencida hace ${dias(-factura.dias)}`
                      : factura.dias === 0 ? 'Vence hoy' : `Vence en ${dias(factura.dias)}`}
                  </p>
                </div>
              </li>
            ))}</ul>
          </section>
          <Link to="/facturacion" className="link-action" onClick={() => dialog.current.close()}>Ir a Facturación y Cobranza</Link>
        </div>}
      </dialog>
    </>
  );
}
