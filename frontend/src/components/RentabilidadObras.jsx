import { useState } from 'react';
import { useTablePagination } from './useTablePagination';
import TablePagination from './TablePagination';
import DetalleOtrosCostos from './DetalleOtrosCostos';

function estado(resultado) {
  if (resultado > 0) return 'Ganancia';
  if (resultado < 0) return 'Pérdida';
  return 'Punto de equilibrio';
}

export default function RentabilidadObras({ rentabilidad, format }) {
  const table = useTablePagination(rentabilidad?.obras ?? []);
  const [obraDetalle, setObraDetalle] = useState(null);
  if (!rentabilidad) return null;
  const { periodo, empresa } = rentabilidad;

  return (
    <section className="space-y-4 rounded-xl bg-surface-container-lowest p-5 shadow-sm">
      <div>
        <h2 className="text-xl font-bold">Rentabilidad de obras</h2>
        <p className="text-sm text-secondary">Resultado directo según facturación sin IVA, notas de crédito y costos registrados.</p>
      </div>
      <dl className="grid gap-3 sm:grid-cols-3">
        <div><dt>Facturación ajustada del período</dt><dd className="font-semibold">{format(periodo.ingresos)}</dd></div>
        <div><dt>Costos directos del período</dt><dd className="font-semibold">{format(periodo.costos_directos)}</dd></div>
        <div>
          <dt>Resultado directo del período</dt>
          <dd className="font-semibold">{periodo.tiene_movimientos
            ? `${estado(periodo.resultado)} · ${format(periodo.resultado)}`
            : 'Sin movimientos registrados'}</dd>
          {periodo.obras_provisionales > 0 && <dd className="text-sm text-secondary">
            Provisional · {periodo.obras_provisionales} {periodo.obras_provisionales === 1 ? 'obra con pendientes' : 'obras con pendientes'}
          </dd>}
        </div>
      </dl>
      {empresa && <div className="rounded-lg bg-surface-container-low p-3">
        <h3 className="font-semibold">Resultado operativo registrado de la empresa</h3>
        <p>Gastos generales del período · {format(empresa.gastos_generales)}</p>
        <p className="font-semibold">{periodo.tiene_movimientos || empresa.gastos_registrados
          ? `${estado(empresa.resultado)} · ${format(empresa.resultado)}`
          : 'Sin movimientos registrados'}</p>
        {!empresa.gastos_registrados && <p className="text-sm text-secondary">Provisional · Sin gastos generales registrados en el período.</p>}
        {periodo.obras_provisionales > 0 && <p className="text-sm text-secondary">Provisional · Hay obras con datos pendientes.</p>}
      </div>}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <caption className="py-2 text-left font-semibold">Resultado acumulado por obra</caption>
          <thead><tr className="border-b">
            {['Obra', 'Presupuesto aprobado', 'Ejecución de costos', 'Facturación ajustada', 'Horas profesionales', 'Materiales', 'Otros costos', 'Resultado directo'].map(
              (label) => <th key={label} scope="col" className="p-2">{label}</th>,
            )}
          </tr></thead>
          <tbody>{table.rows.map((obra) => (
            <tr key={obra.id} className="border-b align-top">
              <th scope="row" className="p-2">{obra.codigo_obra}<div>{obra.nombre_obra}</div></th>
              <td className="p-2">{format(obra.presupuesto_neto)} <span className="text-secondary">neto</span></td>
              <td className="p-2">
                <strong>{format(obra.costos_directos)} reales</strong>
                {obra.costo_previsto == null ? <div className="text-secondary">Sin desglose previsto</div> : <>
                  <div>{format(obra.costo_previsto)} previstos</div>
                  <div className="text-secondary">Desviación · {format(obra.desviacion_costos)}</div>
                </>}
              </td>
              <td className="p-2">{format(obra.ingresos)}</td>
              <td className="p-2">{format(obra.mano_de_obra)}</td>
              <td className="p-2">{format(obra.materiales)}</td>
              <td className="p-2">
                <div>{format(obra.otros_costos)}</div>
                <button type="button" aria-haspopup="dialog" aria-label={`Ver otros costos de ${obra.nombre_obra}`}
                  className="link-action" onClick={() => setObraDetalle(obra)}>Ver detalle</button>
              </td>
              <td className="p-2">
                <strong>{estado(obra.resultado)} · {format(obra.resultado)}</strong>
                {obra.pendientes.length > 0 && <div className="text-secondary">
                  Provisional · {obra.pendientes.join(' · ')}
                </div>}
              </td>
            </tr>
          ))}</tbody>
        </table>
      </div>
      {!rentabilidad.obras.length && <p>No hay obras para los filtros seleccionados.</p>}
      <TablePagination table={table} label="Paginación de rentabilidad por obra" />
      {obraDetalle && <DetalleOtrosCostos obra={obraDetalle} format={format} onClose={() => setObraDetalle(null)} />}
    </section>
  );
}
