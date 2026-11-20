import { useCallback, useEffect, useRef, useState } from 'react';
import { api, withQuery } from '../api/client';
import { BudgetBreakdown, CountBreakdown, SalesTrend } from '../components/DashboardCharts';

const currency = new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP' });
const clp = (value) => currency.format(value ?? 0);

const emptyFilters = { desde: null, hasta: null, cliente_id: '', tecnico_id: '', estado_obra: '' };
const workStates = {
  'en-proceso': 'En proceso',
  finalizada: 'Finalizada',
  suspendida: 'Suspendida',
  cancelada: 'Cancelada',
};

function MetricCard({ title, value, detail, accent }) {
  return (
    <article className="min-w-0 rounded-2xl border border-surface-container-high bg-surface-container-lowest p-5 shadow-sm">
      <p className="flex items-center gap-2 text-sm font-medium text-on-surface-variant">
        {accent && <span aria-hidden="true" className={'h-2 w-2 shrink-0 rounded-[50%] ' + accent} />}
        {title}
      </p>
      <strong className="mt-2 block break-words text-2xl tabular-nums text-on-surface">{value}</strong>
      {detail && <p className="mt-1 text-sm text-secondary">{detail}</p>}
    </article>
  );
}

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [clients, setClients] = useState([]);
  const [filters, setFilters] = useState(emptyFilters);
  const [appliedFilters, setAppliedFilters] = useState(emptyFilters);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const activeRequest = useRef(null);

  const load = useCallback((query, force = false) => {
    activeRequest.current?.abort();
    const controller = new AbortController();
    activeRequest.current = controller;

    const path = withQuery('/dashboard/resumen/', { ...query, actualizar: force ? 1 : undefined });
    api.request(path, { signal: controller.signal, cache: 'no-store' })
      .then((result) => {
        if (controller.signal.aborted) return;
        setData(result);
        setAppliedFilters(query);
      })
      .catch((requestError) => {
        if (!controller.signal.aborted) setError(requestError.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
  }, []);

  const reload = (query, force) => {
    setLoading(true);
    setError('');
    load(query, force);
  };

  useEffect(() => {
    load(emptyFilters);
    return () => activeRequest.current?.abort();
  }, [load]);

  useEffect(() => {
    let active = true;
    api.listAll('/clientes/').then((result) => {
      if (active) setClients(result);
    }).catch(() => {});
    return () => { active = false; };
  }, []);

  const m = data?.metricas ?? {};
  const d = data?.distribuciones ?? {};
  const techs = d.obras_activas_por_tecnico ?? [];
  const period = data?.periodo;
  const usesCurrentMonth = !appliedFilters.desde && !appliedFilters.hasta;
  const approved = m.presupuestos_aprobados?.cantidad ?? 0;
  const pending = m.presupuestos_pendientes?.cantidad ?? 0;
  const financialCards = [
    ['Recaudación neta', clp(m.recaudacion_periodo?.monto_neto)],
    ['Cuentas por cobrar', clp(m.cuentas_por_cobrar?.saldo_total)],
    ['Costos directos', clp(m.costos_directos_periodo?.monto_total)],
    ['Proyección aprobada', clp(m.proyeccion_ingresos_aprobados)],
  ];
  const changeFilter = (event) => {
    const { name, value } = event.target;
    setFilters((current) => ({ ...current, [name]: value }));
  };
  const fieldClass = 'mt-1 block w-full rounded bg-surface-container-low p-2';

  return (
    <div className="mx-auto flex w-full max-w-[1600px] flex-col gap-6 p-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-label-sm uppercase text-secondary">Panel gerencial</p>
          <h1 className="text-3xl font-bold text-on-surface">Dashboard</h1>
          {period && <p className="mt-1 text-on-surface-variant">Período consultado · {period.desde} a {period.hasta}</p>}
        </div>
        <button type="button" disabled={loading} onClick={() => reload(appliedFilters, true)} className="rounded-lg bg-primary-container px-4 py-2 text-on-primary disabled:opacity-60">
          {loading ? 'Actualizando…' : '↻ Actualizar datos'}
        </button>
      </header>
      {error && <p role="alert" className="rounded-lg bg-error-container p-3 text-on-error-container">{error}</p>}

      <form
        className="grid gap-3 rounded-xl bg-surface-container-lowest p-4 shadow-sm sm:grid-cols-2 lg:grid-cols-5"
        onSubmit={(event) => {
          event.preventDefault();
          reload(filters);
        }}
      >
        <label>Desde<input type="date" name="desde" className={fieldClass} value={filters.desde ?? period?.desde ?? ''} onChange={changeFilter} /></label>
        <label>Hasta<input type="date" name="hasta" className={fieldClass} value={filters.hasta ?? period?.hasta ?? ''} onChange={changeFilter} /></label>
        <label>Cliente<select name="cliente_id" className={fieldClass} value={filters.cliente_id} onChange={changeFilter}>
          <option value="">Todos</option>
          {clients.map((client) => <option key={client.id} value={client.id}>{client.razon_social}</option>)}
        </select></label>
        <label>Técnico<select name="tecnico_id" className={fieldClass} value={filters.tecnico_id} onChange={changeFilter}>
          <option value="">Todos</option>
          {techs.map((tech) => <option key={tech.tecnico_id} value={tech.tecnico_id}>{tech.tecnico}</option>)}
        </select></label>
        <label>Estado de obra<select name="estado_obra" className={fieldClass} value={filters.estado_obra} onChange={changeFilter}>
          <option value="">Todos</option>
          {['en-proceso', 'finalizada', 'suspendida', 'cancelada'].map((state) => <option key={state}>{state}</option>)}
        </select></label>
        <button type="submit" disabled={loading} className="self-end rounded bg-surface-container px-3 py-2 disabled:opacity-60">Aplicar filtros</button>
      </form>

      <section aria-label="Indicadores gerenciales" aria-busy={loading} className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard title={usesCurrentMonth ? 'Ventas netas del mes' : 'Ventas netas del período'} accent="bg-primary"
          value={data ? clp(m.ventas_facturadas?.monto_total) : '—'}
          detail={data && (m.ventas_facturadas?.cantidad_facturas ?? 0) + ' facturas emitidas'} />
        <MetricCard title="Presupuestos" accent="bg-tertiary-container" value={data ? approved + pending : '—'}
          detail={data && approved + ' aprobados · ' + pending + ' pendientes'} />
        <MetricCard title="Obras en proceso" accent="bg-indigo-600" value={data ? m.obras_en_proceso : '—'} />
        <MetricCard title="Servicios realizados" accent="bg-teal-700" value={data ? m.servicios_realizados : '—'} />
      </section>

      <section aria-label="Ventas y presupuestos" aria-busy={loading} className="grid gap-4 xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <SalesTrend period={period} series={d.ventas_netas_diarias} total={m.ventas_facturadas?.monto_total} format={clp} loading={loading} />
        <BudgetBreakdown ready={Boolean(data)}
          rows={[
            { label: 'Aprobados', value: approved, detail: clp(m.presupuestos_aprobados?.monto_total), color: 'bg-primary' },
            { label: 'Pendientes', value: pending, detail: clp(m.presupuestos_pendientes?.monto_total), color: 'bg-tertiary-container' },
          ]} />
      </section>

      <section aria-label="Obras y servicios" aria-busy={loading} className="grid gap-4 lg:grid-cols-2">
        <CountBreakdown title="Obras por estado" description="Estado operativo actual de las obras." color="bg-indigo-600"
          ready={Boolean(data)} empty="Sin obras para los filtros aplicados."
          rows={(d.obras_por_estado ?? []).map((row) => ({
            label: workStates[row.estado_operativo] ?? row.estado_operativo,
            value: row.cantidad,
          }))} />
        <CountBreakdown title="Servicios realizados por categoría" description="Obras finalizadas en el período." color="bg-teal-700"
          ready={Boolean(data)} empty="Sin servicios realizados en el período."
          rows={(d.servicios_por_categoria ?? []).map((row) => ({
            id: row.clasificacion_servicio_id ?? 'sin-categoria',
            label: row.clasificacion_servicio__nombre || 'Sin categoría',
            value: row.cantidad,
          }))} />
      </section>
      <section aria-label="Otros indicadores financieros" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {financialCards.map(([title, value]) => <MetricCard key={title} title={title} value={data ? value : '—'} />)}
      </section>
 <section className="grid gap-4 lg:grid-cols-2"><article className="rounded-xl bg-surface-container-lowest p-5 shadow-sm"><h2 className="mb-3 text-lg font-semibold">Cuentas por cobrar</h2><p>Facturas pendientes: {m.cuentas_por_cobrar?.facturas_pendientes||0}</p><p>Saldo vencido: {clp(m.cuentas_por_cobrar?.saldo_vencido)}</p><div className="mt-3 grid grid-cols-2 gap-2">{Object.entries(m.cuentas_por_cobrar?.antiguedad||{}).map(([k,v])=><p className="rounded bg-surface-container-low p-2" key={k}>{k.replaceAll('_',' ')}: {clp(v.saldo)}</p>)}</div><p className="mt-3">Presupuestos por vencer en 7 días: {m.presupuestos_por_vencer_7_dias?.cantidad||0} · {clp(m.presupuestos_por_vencer_7_dias?.monto_total)}</p><p>Conversión aprobada: {m.conversion_presupuestos?.porcentaje_aprobacion||0}% ({m.conversion_presupuestos?.aprobados||0}/{m.conversion_presupuestos?.decididos||0})</p></article>
      <article className="rounded-xl bg-surface-container-lowest p-5 shadow-sm"><h2 className="mb-3 text-lg font-semibold">Obras activas por técnico</h2>{techs.map(x=><p className="flex justify-between border-b border-surface-container py-2" key={x.tecnico_id}><span>{x.tecnico||'Sin nombre'}</span><strong>{x.cantidad_obras}</strong></p>)}{!techs.length&&<p className="text-secondary">Sin obras activas asignadas.</p>}</article>
      <article className="rounded-xl bg-surface-container-lowest p-5 shadow-sm"><h2 className="mb-3 text-lg font-semibold">Top clientes por ventas</h2>{(d.top_clientes_por_ventas||[]).map(x=><p className="flex justify-between border-b border-surface-container py-2" key={x.cliente_id}><span>{x.cliente}</span><strong>{clp(x.monto_neto)}</strong></p>)}</article>
      <article className="rounded-xl bg-surface-container-lowest p-5 shadow-sm"><h2 className="mb-3 text-lg font-semibold">Top clientes por deuda</h2>{(d.top_clientes_por_deuda||[]).map(x=><p className="flex justify-between border-b border-surface-container py-2" key={x.cliente_id}><span>{x.cliente}</span><strong>{clp(x.saldo_pendiente)}</strong></p>)}</article></section>
    </div>
  );
}
