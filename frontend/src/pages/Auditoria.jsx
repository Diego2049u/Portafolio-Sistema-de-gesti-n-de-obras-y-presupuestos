import { useMemo, useState } from 'react';
import MainLayout from '../components/layout';

const EVENTOS = [
  { id: 'evt-000', modulo: 'Acceso al sistema', tipo: 'exito', evento: 'Inicio de sesión correcto', detalle: 'El usuario ingresó correctamente al sistema.', usuario: 'Gerencia', fecha: 'Hoy, 12:04:16' },
  { id: 'evt-001', modulo: 'Obras y Proyectos', tipo: 'exito', evento: 'Proyecto actualizado', detalle: 'Se registró el avance y se guardaron los cambios del proyecto.', usuario: 'Supervisor de obras', fecha: 'Hoy, 11:42:08' },
  { id: 'evt-002', modulo: 'Presupuestos y Costos', tipo: 'incompleto', evento: 'Presupuesto no guardado', detalle: 'Falta completar la descripción de una partida antes de guardar.', usuario: 'Finanzas', fecha: 'Hoy, 11:28:31' },
  { id: 'evt-003', modulo: 'Facturación y Cobranza', tipo: 'error', evento: 'Error al emitir documento', detalle: 'No se pudo completar la emisión. Revise los datos del documento e inténtelo nuevamente.', usuario: 'Finanzas', fecha: 'Hoy, 10:56:14' },
  { id: 'evt-004', modulo: 'Costos de Materiales', tipo: 'exito', evento: 'Material registrado', detalle: 'Se creó un registro de material y quedó disponible para su consulta.', usuario: 'Bodega', fecha: 'Hoy, 10:21:47' },
  { id: 'evt-005', modulo: 'Clientes y Contratos', tipo: 'incompleto', evento: 'Contrato pendiente de datos', detalle: 'No se guardó el contrato: falta ingresar la fecha de término.', usuario: 'Administración', fecha: 'Hoy, 09:48:03' },
  { id: 'evt-006', modulo: 'Técnicos', tipo: 'exito', evento: 'Técnico asignado', detalle: 'La asignación del técnico se completó correctamente.', usuario: 'Supervisor de obras', fecha: 'Hoy, 09:16:25' },
  { id: 'evt-007', modulo: 'Obras y Proyectos', tipo: 'error', evento: 'No se pudo crear la ficha de obra', detalle: 'Ocurrió un error al guardar la ficha. El registro no fue creado.', usuario: 'Supervisor de obras', fecha: 'Ayer, 16:37:52' },
  { id: 'evt-008', modulo: 'Presupuestos y Costos', tipo: 'exito', evento: 'Presupuesto enviado', detalle: 'La cotización se emitió y quedó registrada en el sistema.', usuario: 'Finanzas', fecha: 'Ayer, 15:02:19' },
  { id: 'evt-009', modulo: 'Facturación y Cobranza', tipo: 'incompleto', evento: 'Estado de pago incompleto', detalle: 'Falta asociar el respaldo requerido para continuar el proceso.', usuario: 'Finanzas', fecha: 'Ayer, 14:44:06' },
  { id: 'evt-010', modulo: 'Clientes y Contratos', tipo: 'exito', evento: 'Cliente creado', detalle: 'El registro del cliente se guardó correctamente.', usuario: 'Administración', fecha: 'Ayer, 12:10:40' },
  { id: 'evt-011', modulo: 'Panel principal', tipo: 'exito', evento: 'Indicadores consultados', detalle: 'Se cargaron los indicadores y resúmenes del panel principal.', usuario: 'Gerencia', fecha: 'Ayer, 08:32:17' },
];

const TIPOS = [
  { id: 'todos', etiqueta: 'Todos los eventos', icono: 'list_alt' },
  { id: 'error', etiqueta: 'Errores', icono: 'error' },
  { id: 'incompleto', etiqueta: 'Datos incompletos', icono: 'assignment_late' },
  { id: 'exito', etiqueta: 'Procesos exitosos', icono: 'check_circle' },
];

const ESTILOS_TIPO = {
  exito: { etiqueta: 'Correcto', icono: 'check_circle', clase: 'bg-primary-fixed text-primary' },
  error: { etiqueta: 'Error', icono: 'error', clase: 'bg-error-container text-on-error-container' },
  incompleto: { etiqueta: 'Dato faltante', icono: 'warning', clase: 'bg-tertiary-fixed text-tertiary' },
};

const MODULOS = ['Acceso al sistema', 'Panel principal', 'Obras y Proyectos', 'Clientes y Contratos', 'Presupuestos y Costos', 'Costos de Materiales', 'Facturación y Cobranza', 'Técnicos'];

export default function Auditoria() {
  const [tipoActivo, setTipoActivo] = useState('todos');
  const [moduloActivo, setModuloActivo] = useState('todos');
  const [busqueda, setBusqueda] = useState('');

  const eventosFiltrados = useMemo(() => {
    const consulta = busqueda.trim().toLocaleLowerCase('es');
    return EVENTOS.filter((evento) => {
      const coincideTipo = tipoActivo === 'todos' || evento.tipo === tipoActivo;
      const coincideModulo = moduloActivo === 'todos' || evento.modulo === moduloActivo;
      const texto = `${evento.evento} ${evento.detalle} ${evento.usuario} ${evento.modulo}`.toLocaleLowerCase('es');
      return coincideTipo && coincideModulo && texto.includes(consulta);
    });
  }, [tipoActivo, moduloActivo, busqueda]);

  const totalErrores = EVENTOS.filter((evento) => evento.tipo === 'error').length;
  const totalIncompletos = EVENTOS.filter((evento) => evento.tipo === 'incompleto').length;
  const totalExitosos = EVENTOS.filter((evento) => evento.tipo === 'exito').length;

  return (
    <MainLayout breadcrumb="Auditoría del sistema" period="Q4-2026">
      <div className="w-full bg-surface">
        <div className="px-margin-desktop py-space-xl flex flex-col gap-space-xl max-w-[1600px] mx-auto">
          <section className="flex flex-col lg:flex-row lg:items-center justify-between gap-space-lg bg-surface-container-lowest p-space-lg rounded-xl shadow-sm">
            <div className="flex flex-col gap-space-xs">
              <span className="inline-flex w-fit items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-secondary-container text-on-secondary-container font-label-sm text-label-sm"><span className="w-1.5 h-1.5 rounded-full bg-primary-container" />REGISTRO DE ACTIVIDAD</span>
              <h1 className="font-headline-lg text-headline-lg text-on-surface tracking-tight">Auditoría del sistema</h1>
              <p className="font-body-md text-body-md text-on-surface-variant">Consulta los procesos realizados, los errores y los datos que faltan en los distintos módulos.</p>
            </div>
            <div className="inline-flex items-center gap-space-xs px-space-md py-2 rounded-xl bg-surface-container text-on-surface-variant font-label-md text-label-md"><span className="material-symbols-outlined text-[18px] text-primary">history</span>Actividad reciente</div>
          </section>

          <section className="grid grid-cols-1 sm:grid-cols-3 gap-gutter-desktop" aria-label="Resumen de eventos">
            {[
              { tipo: 'error', titulo: 'Errores', valor: totalErrores, icono: 'error', color: 'text-error' },
              { tipo: 'incompleto', titulo: 'Datos incompletos', valor: totalIncompletos, icono: 'assignment_late', color: 'text-tertiary' },
              { tipo: 'exito', titulo: 'Procesos exitosos', valor: totalExitosos, icono: 'task_alt', color: 'text-primary' },
            ].map((resumen) => <article key={resumen.tipo} className="bg-surface-container-lowest p-space-lg rounded-xl shadow-sm flex items-center justify-between"><div><span className="font-label-sm text-label-sm text-secondary uppercase tracking-wider font-semibold">{resumen.titulo}</span><div className="font-metric-lg text-metric-lg text-on-surface font-bold mt-1">{resumen.valor}</div></div><span className={`material-symbols-outlined text-[28px] ${resumen.color}`}>{resumen.icono}</span></article>)}
          </section>

          <section className="bg-surface-container-lowest p-space-md rounded-xl shadow-sm flex flex-col gap-space-md">
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-space-md">
              <div className="flex items-center gap-1 p-1 bg-surface-container-low rounded-lg overflow-x-auto max-w-full">
                {TIPOS.map((tipo) => <button key={tipo.id} onClick={() => setTipoActivo(tipo.id)} className={`inline-flex items-center gap-1.5 px-space-md py-2 rounded-lg whitespace-nowrap font-label-md text-label-md font-semibold transition-all ${tipoActivo === tipo.id ? 'bg-surface-container-lowest text-primary shadow-sm' : 'text-on-surface-variant hover:text-on-surface'}`} type="button"><span className="material-symbols-outlined text-[18px]">{tipo.icono}</span>{tipo.etiqueta}</button>)}
              </div>
              <div className="flex flex-col sm:flex-row gap-space-sm">
                <label className="flex items-center gap-space-xs bg-surface-container-low px-space-md py-2 rounded-lg text-on-surface font-label-md text-label-md"><span className="text-secondary">Módulo:</span><select aria-label="Filtrar por módulo" value={moduloActivo} onChange={(event) => setModuloActivo(event.target.value)} className="bg-transparent font-semibold text-on-surface focus:outline-none cursor-pointer"><option value="todos">Todos los módulos</option>{MODULOS.map((modulo) => <option key={modulo} value={modulo}>{modulo}</option>)}</select></label>
                <label className="relative flex items-center"><span className="material-symbols-outlined absolute left-3 text-secondary text-[18px]">search</span><input aria-label="Buscar eventos" value={busqueda} onChange={(event) => setBusqueda(event.target.value)} className="w-full sm:w-64 h-10 pl-10 pr-space-md bg-surface-container-low rounded-lg font-body-sm text-body-sm text-on-surface placeholder:text-outline focus:outline-none focus:bg-surface-container-lowest" placeholder="Buscar en los eventos..." type="search" /></label>
              </div>
            </div>

            <div className="flex items-center justify-between border-b border-surface-container-low pb-space-sm"><h2 className="font-headline-sm text-headline-sm font-semibold text-on-surface">Registro de eventos</h2><span className="font-label-sm text-label-sm text-secondary">{eventosFiltrados.length} {eventosFiltrados.length === 1 ? 'evento' : 'eventos'}</span></div>

            <div className="flex flex-col gap-space-sm">
              {eventosFiltrados.map((evento) => {
                const estilo = ESTILOS_TIPO[evento.tipo];
                return <article key={evento.id} className="flex flex-col lg:flex-row lg:items-center justify-between gap-space-md p-space-md bg-surface-container-low rounded-xl">
                  <div className="flex items-start gap-space-md min-w-0"><span className={`inline-flex items-center justify-center w-10 h-10 rounded-xl shrink-0 ${estilo.clase}`}><span className="material-symbols-outlined text-[21px]">{estilo.icono}</span></span><div className="min-w-0"><div className="flex flex-wrap items-center gap-space-xs"><h3 className="font-headline-sm text-headline-sm font-semibold text-on-surface">{evento.evento}</h3><span className={`px-2 py-0.5 rounded-full font-label-sm text-label-sm font-semibold ${estilo.clase}`}>{estilo.etiqueta}</span></div><p className="font-body-sm text-body-sm text-on-surface-variant mt-0.5">{evento.detalle}</p><div className="flex flex-wrap gap-x-space-md gap-y-1 mt-1 font-label-sm text-label-sm text-secondary"><span>{evento.modulo}</span><span>Usuario: {evento.usuario}</span></div></div></div>
                  <time className="font-label-md text-label-md text-secondary shrink-0 lg:text-right">{evento.fecha}</time>
                </article>;
              })}
              {eventosFiltrados.length === 0 && <div className="p-space-xl text-center text-on-surface-variant"><span className="material-symbols-outlined text-[28px]">search_off</span><p className="font-body-md text-body-md mt-1">No hay eventos que coincidan con estos filtros.</p></div>}
            </div>
          </section>
        </div>
      </div>
    </MainLayout>
  );
}
