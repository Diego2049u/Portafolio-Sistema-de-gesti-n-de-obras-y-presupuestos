import { Link, useParams } from 'react-router-dom';
import CalendarioTecnico from '../components/calendario/CalendarioTecnico';
import { bloquesDelDia, useAgendaTecnico } from '../components/calendario/agenda';

export default function TecnicoDisponibilidad({ user, userRole }) {
  const { tecnicoId } = useParams();
  const personal = userRole === 'TECNICO';
  const id = personal ? user.id : tecnicoId;
  const { data, loading, error, onPeriodoChange, reintentar } = useAgendaTecnico(id);
  const tecnico = data?.tecnico;
  const nombre = tecnico?.nombre || (personal ? user.name : 'Agenda del técnico');
  return <div className="space-y-6">
    <Link to={personal ? '/obras' : '/tecnicos'} className="link-action">
      <span aria-hidden="true" className="material-symbols-outlined text-base">arrow_back</span>
      {personal ? 'Volver a Obras y Proyectos' : 'Volver al equipo técnico'}
    </Link>
    <header className="rounded-xl bg-surface-container-lowest p-6 shadow-sm">
      <p className="text-label-sm font-semibold uppercase tracking-wider text-primary">Disponibilidad del técnico</p>
      <h1 className="mt-3 text-headline-lg font-bold">{nombre}</h1>
      {tecnico && <p className="mt-1 text-body-md text-secondary">{tecnico.especialidad}{tecnico.rut && ` · RUT ${tecnico.rut}`}</p>}
    </header>
    <CalendarioTecnico key={id} nombre={nombre} loading={loading} error={error} reintentar={reintentar} sinPlanificar={!!data?.sin_planificar?.length}
      onPeriodoChange={onPeriodoChange} obtenerBloques={(fecha) => bloquesDelDia(fecha, data?.eventos || []).filter((bloque) => !data?.sin_planificar?.length || bloque.estado !== 'disponible')} />
  </div>;
}