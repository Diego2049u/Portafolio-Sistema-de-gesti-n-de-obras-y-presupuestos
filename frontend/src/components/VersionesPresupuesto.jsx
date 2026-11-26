import { useEffect, useRef, useState } from 'react';
import { api } from '../api/client';

const fechaVersion = new Intl.DateTimeFormat('es-CL', {
  dateStyle: 'medium', timeStyle: 'short', timeZone: 'America/Santiago',
});

export default function VersionesPresupuesto({ presupuesto, format, onClose }) {
  const dialog = useRef(null);
  const [versiones, setVersiones] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    dialog.current.showModal();
    api.request(`/presupuestos/${presupuesto.id}/historial-versiones/`, { signal: controller.signal })
      .then((data) => { if (!controller.signal.aborted) setVersiones(data); })
      .catch((err) => { if (!controller.signal.aborted) setError(err.message); });
    return () => controller.abort();
  }, [presupuesto.id]);

  return (
    <dialog ref={dialog} onClose={onClose} aria-labelledby="titulo-versiones-presupuesto"
      className="historial-obra m-auto max-h-[85vh] w-[calc(100%-2rem)] max-w-xl overflow-y-auto rounded-xl bg-surface-container-lowest p-5 text-on-surface shadow-xl">
      <header className="flex items-start justify-between gap-4">
        <div>
          <h2 id="titulo-versiones-presupuesto" className="text-xl font-bold">Versiones del presupuesto</h2>
          <p className="text-sm text-secondary">{presupuesto.numero_presupuesto}</p>
        </div>
        <form method="dialog"><button className="rounded-lg bg-surface-container px-3 py-2">Cerrar</button></form>
      </header>
      {error && <p role="alert" className="mt-4 text-error">{error}</p>}
      {!versiones && !error && <p role="status" className="mt-4">Cargando versiones…</p>}
      {versiones?.length === 0 && <p className="mt-4">Sin versiones registradas.</p>}
      {versiones?.length > 0 && (
        <ol className="mt-5 space-y-4 border-l-2 border-surface-container pl-5">
          {versiones.map((version) => (
            <li key={version.id} className="relative before:absolute before:-left-[27px] before:top-1.5 before:h-3 before:w-3 before:rounded-full before:bg-primary">
              <div className="flex flex-wrap items-baseline justify-between gap-x-3">
                <p className="font-semibold">Versión {version.numero_version}</p>
                {version.snapshot?.monto_total != null && <p className="text-sm">Total guardado · {format(version.snapshot.monto_total)}</p>}
              </div>
              <time className="text-sm text-secondary" dateTime={version.fecha}>
                {fechaVersion.format(new Date(version.fecha))}
              </time>
              {version.usuario_nombre && <p className="text-sm text-secondary">{version.usuario_nombre}</p>}
            </li>
          ))}
        </ol>
      )}
    </dialog>
  );
}
