import { useState } from 'react';

const axisDate = new Intl.DateTimeFormat('es-CL', { day: 'numeric', month: 'short', timeZone: 'UTC' });
const fullDate = new Intl.DateTimeFormat('es-CL', { dateStyle: 'long', timeZone: 'UTC' });
const compactNumber = new Intl.NumberFormat('es-CL', { notation: 'compact', maximumFractionDigits: 1 });
const percentage = new Intl.NumberFormat('es-CL', { style: 'percent', maximumFractionDigits: 1 });
const dayMilliseconds = 86400000;

function ChartPanel({ title, description, children }) {
  return (
    <article className="min-w-0 rounded-2xl border border-surface-container-high bg-surface-container-lowest p-5 shadow-sm sm:p-6">
      <h2 className="text-lg font-semibold text-on-surface">{title}</h2>
      {description && <p className="mt-1 text-sm text-on-surface-variant">{description}</p>}
      {children}
    </article>
  );
}

export function SalesTrend({ period, series, total, format, loading }) {
  const [selectedDate, setSelectedDate] = useState(null);
  if (!period || !series) {
    return (
      <ChartPanel title="Evolución de ventas netas">
        <p className="mt-6 text-secondary">{loading ? 'Consultando ventas…' : 'Serie de ventas no disponible.'}</p>
      </ChartPanel>
    );
  }

  const start = Date.parse(period.desde);
  const end = Date.parse(period.hasta);
  const byDay = new Map(series.map(({ fecha, monto_total }) => [fecha, monto_total]));
  const days = Array.from({ length: (end - start) / dayMilliseconds + 1 }, (_, index) => {
    const date = new Date(start + index * dayMilliseconds);
    const key = date.toISOString().slice(0, 10);
    return { date, key, value: byDay.get(key) ?? 0 };
  });
  const values = days.map(({ value }) => value);
  const min = Math.min(0, ...values);
  const max = Math.max(1, ...values);
  const y = (value) => (max - value) / (max - min) * 100;
  const x = (index) => days.length === 1 ? 50 : index / (days.length - 1) * 100;
  const points = days.map(({ value }, index) => [x(index), y(value)]);
  const line = [
    ...points.map(([left, top]) => left + '% ' + (top - 0.55) + '%'),
    ...[...points].reverse().map(([left, top]) => left + '% ' + (top + 0.55) + '%'),
  ].join(', ');
  const area = ['0% ' + y(0) + '%', ...points.map(([left, top]) => left + '% ' + top + '%'), '100% ' + y(0) + '%'].join(', ');
  const ticks = [max, (max + min) / 2, min];
  const dateTicks = [...new Set([0, Math.floor((days.length - 1) / 2), days.length - 1])];
  const selectedIndex = days.findIndex(({ key }) => key === selectedDate);
  const selected = days[selectedIndex];

  return (
    <ChartPanel title="Evolución de ventas netas" description="Facturación diaria menos notas de crédito, en CLP.">
      <div className="mt-4 flex min-h-12 flex-wrap items-baseline gap-x-3">
        <strong className="text-2xl text-on-surface">{format(selected?.value ?? total)}</strong>
        <span className="text-sm text-secondary">{selected ? fullDate.format(selected.date) : 'Total del período'}</span>
      </div>
      {series.length === 0 ? (
        <p className="grid min-h-52 place-items-center text-sm text-secondary">Sin movimientos de venta en el período.</p>
      ) : (
        <>
          <div className="grid grid-cols-[3.75rem_minmax(0,1fr)] gap-x-2 pb-2 pt-3" aria-hidden="true">
            <div className="relative h-44 text-right text-xs text-secondary sm:h-52">
              {ticks.map((tick, index) => (
                <span key={index} className="absolute right-0 -translate-y-1/2 whitespace-nowrap" style={{ top: y(tick) + '%' }}>
                  {compactNumber.format(tick)}
                </span>
              ))}
            </div>
            <div className="relative h-44 sm:h-52" onPointerLeave={() => setSelectedDate(null)}>
              {ticks.map((tick, index) => (
                <div key={index} className="absolute inset-x-0 border-t border-dashed border-outline-variant" style={{ top: y(tick) + '%' }} />
              ))}
              <div className="absolute inset-x-0 border-t border-outline-variant" style={{ top: y(0) + '%' }} />
              {points.length > 1 && (
                <>
                  <div className="absolute inset-0 bg-primary/15" style={{ clipPath: 'polygon(' + area + ')' }} />
                  <div className="absolute inset-0 bg-primary" style={{ clipPath: 'polygon(' + line + ')' }} />
                </>
              )}
              {(selected || points.length === 1) && (
                <div className="pointer-events-none absolute z-10 -translate-x-1/2 -translate-y-1/2 rounded-[50%] border-2 border-white bg-primary p-1.5 shadow"
                  style={{ left: x(Math.max(0, selectedIndex)) + '%', top: y(selected?.value ?? days[0].value) + '%' }} />
              )}
              <div
                className="absolute inset-0 cursor-crosshair"
                onPointerMove={(event) => {
                  const { left, width } = event.currentTarget.getBoundingClientRect();
                  const position = Math.min(1, Math.max(0, (event.clientX - left) / width));
                  setSelectedDate(days[Math.round(position * (days.length - 1))].key);
                }}
              />
            </div>
            <div className={'col-start-2 mt-3 flex text-xs text-secondary ' + (days.length === 1 ? 'justify-center' : 'justify-between')}>
              {dateTicks.map((index) => <span key={days[index].key}>{axisDate.format(days[index].date)}</span>)}
            </div>
          </div>
          <details className="mt-3 border-t border-surface-container pt-3 text-sm">
            <summary className="cursor-pointer font-medium text-primary">Ver ventas por día</summary>
            <div className="mt-2 max-h-56 overflow-auto">
              <table className="w-full text-left">
                <thead><tr><th scope="col">Fecha</th><th scope="col" className="text-right">Ventas netas</th></tr></thead>
                <tbody>
                  {days.map(({ key, date, value }) => (
                    <tr key={key} className="border-t border-surface-container">
                      <td className="py-1">{fullDate.format(date)}</td><td className="text-right tabular-nums">{format(value)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
        </>
      )}
    </ChartPanel>
  );
}

export function BudgetBreakdown({ rows, ready }) {
  const total = rows.reduce((sum, row) => sum + row.value, 0);
  const approvedShare = total ? rows[0].value / total : 0;

  return (
    <ChartPanel title="Estado de presupuestos" description="Cantidad y monto por estado en el período.">
      <div className="relative mx-auto my-6 grid aspect-square w-40 place-items-center rounded-[50%] bg-surface-container sm:w-44">
        {ready && total > 0 && (
          <div aria-hidden="true" className="absolute inset-0 rounded-[50%]" style={{
            background: 'conic-gradient(#004ac6 0 ' + approvedShare * 100 + '%, #996100 0 100%)',
          }} />
        )}
        <div className="z-10 grid h-[72%] w-[72%] content-center rounded-[50%] bg-surface-container-lowest text-center">
          <strong className="text-3xl text-on-surface">{ready ? total : '—'}</strong>
          <span className="text-xs text-secondary">presupuestos</span>
        </div>
      </div>
      {ready && (
        <ul className="divide-y divide-surface-container text-sm">
          {rows.map(({ label, value, detail, color }) => (
            <li key={label} className="flex items-center justify-between gap-2 py-2">
              <span><span aria-hidden="true" className={'mr-2 inline-block h-2 w-2 rounded-[50%] ' + color} />{label}</span>
              <span className="text-right"><strong>{value}</strong>{total > 0 && <span className="ml-1 text-secondary">({percentage.format(value / total)})</span>}
                <span className="block text-xs text-secondary">{detail}</span>
              </span>
            </li>
          ))}
        </ul>
      )}
    </ChartPanel>
  );
}

export function CountBreakdown({ title, description, rows, ready, empty, color }) {
  const max = Math.max(1, ...rows.map(({ value }) => value));

  return (
    <ChartPanel title={title} description={description}>
      {!ready && <p className="mt-5 text-secondary">Sin datos consultados.</p>}
      {ready && !rows.length && <p className="mt-5 text-secondary">{empty}</p>}
      {ready && rows.length > 0 && (
        <ul className="mt-5 space-y-3">
          {rows.map(({ id, label, value }) => (
            <li key={id ?? label}>
              <div className="mb-1 flex justify-between gap-3 text-sm">
                <span>{label}</span><strong className="tabular-nums">{value}</strong>
              </div>
              <div aria-hidden="true" className="h-2 overflow-hidden rounded-[1rem] bg-surface-container">
                <div className={'h-full rounded-[1rem] ' + color} style={{ width: (value / max) * 100 + '%' }} />
              </div>
            </li>
          ))}
        </ul>
      )}
    </ChartPanel>
  );
}
