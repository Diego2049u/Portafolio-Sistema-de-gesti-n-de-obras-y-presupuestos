import { useEffect, useRef, useState } from 'react';
import { api } from '../api/client';

const fechaHistorial = new Intl.DateTimeFormat('es-CL', {
  dateStyle: 'medium', timeStyle: 'short', timeZone: 'America/Santiago',
});

export default function HistorialObra({ obra, estados, onClose }) {
  const dialog = useRef(null);
  const [eventos, setEventos] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    dialog.current.showModal();
    api.request(`/obras/${obra.id}/historial-estados/`, { signal: controller.signal })
      .then((data) => { if (!controller.signal.aborted) setEventos(data); })
      .catch((err) => { if (!controller.signal.aborted) setError(err.message); });
    return () => controller.abort();
  }, [obra.id]);

  function estado(valor) {
    return estados[valor] ?? valor;
  }

  return (
    <dialog ref={dialog} onClose={onClose} aria-labelledby="titulo-historial-obra"
      className="historial-obra m-auto max-h-[85vh] w-[calc(100%-2rem)] max-w-xl overflow-y-auto rounded-xl bg-surface-container-lowest p-5 text-on-surface shadow-xl">
      <header className="flex items-start justify-between gap-4">
        <div>
          <h2 id="titulo-historial-obra" className="text-xl font-bold">Historial de estados</h2>
          <p className="text-sm text-secondary">{obra.codigo_obra} · {obra.nombre_obra}</p>
        </div>
        <form method="dialog">
          <button className="rounded-lg bg-surface-container px-3 py-2">Cerrar</button>
        </form>
      </header>
      {error && <p role="alert" className="mt-4 text-error">{error}</p>}
      {!eventos && !error && <p role="status" className="mt-4">Cargando historial…</p>}
      {eventos?.length === 0 && <p className="mt-4">Sin transiciones registradas.</p>}
      {eventos?.length > 0 && (
        <ol className="mt-5 space-y-4 border-l-2 border-surface-container pl-5">
          {eventos.map((evento) => (
            <li key={evento.id} className="relative before:absolute before:-left-[27px] before:top-1.5 before:h-3 before:w-3 before:rounded-full before:bg-primary">
              <time className="text-sm text-secondary" dateTime={evento.fecha}>
                {fechaHistorial.format(new Date(evento.fecha))}
              </time>
              <p className="font-semibold">{evento.estado_anterior ? estado(evento.estado_anterior) : 'Creada'} → {estado(evento.estado_nuevo)}</p>
              {evento.estado_nuevo === 'finalizada' && <p className="text-sm text-secondary">
                Finalizó: {evento.usuario_nombre || 'Usuario no identificado'}
                {' · '}{evento.usuario_rol_finalizacion_nombre
                  || (evento.usuario_rol_actual_nombre && `Rol actual: ${evento.usuario_rol_actual_nombre}`)
                  || 'Rol al finalizar no registrado'}
              </p>}
              {evento.observacion && <p className="whitespace-pre-wrap break-words text-sm">{evento.observacion}</p>}
            </li>
          ))}
        </ol>
      )}
    </dialog>
  );
}
