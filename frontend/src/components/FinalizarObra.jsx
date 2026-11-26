import { useEffect, useRef, useState } from 'react';
import { api } from '../api/client';

export default function FinalizarObra({ obra, onClose, onFinalizada }) {
  const dialog = useRef(null);
  const [confirmado, setConfirmado] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => { dialog.current.showModal(); }, []);

  async function finalizar(event) {
    event.preventDefault();
    if (!confirmado || busy) return;
    setBusy(true);
    setError('');
    try {
      await api.request(`/obras/${obra.id}/transicionar/`, {
        method: 'POST',
        body: { estado_operativo: 'finalizada', costos_confirmados: true },
      });
      onFinalizada();
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <dialog ref={dialog} onClose={onClose} onCancel={(event) => { if (busy) event.preventDefault(); }}
      aria-labelledby="titulo-finalizar-obra"
      className="historial-obra m-auto w-[calc(100%-2rem)] max-w-lg rounded-xl bg-surface-container-lowest p-5 text-on-surface shadow-xl">
      <form className="space-y-4" onSubmit={finalizar}>
        <header>
          <h2 id="titulo-finalizar-obra" className="text-xl font-bold">Finalizar obra</h2>
          <p className="text-sm text-secondary">{obra.codigo_obra} · {obra.nombre_obra}</p>
        </header>
        <p>Revisa que las horas profesionales, los despachos y los demás costos aplicables estén registrados en Costos y Materiales.</p>
        <label className="flex items-start gap-2">
          <input type="checkbox" required disabled={busy} checked={confirmado} onChange={(event) => setConfirmado(event.target.checked)} />
          Confirmo que los costos de ejecución están completos.
        </label>
        {error && <p role="alert" className="rounded-lg bg-error-container p-3 text-on-error-container">{error}</p>}
        <div className="flex flex-wrap gap-3">
          <button disabled={!confirmado || busy} className="rounded-lg bg-primary-container px-4 py-2 text-on-primary disabled:opacity-50">
            {busy ? 'Finalizando…' : 'Confirmar finalización'}
          </button>
          <button type="button" disabled={busy} className="rounded-lg bg-surface-container px-4 py-2" onClick={() => dialog.current.close()}>Volver</button>
        </div>
      </form>
    </dialog>
  );
}
