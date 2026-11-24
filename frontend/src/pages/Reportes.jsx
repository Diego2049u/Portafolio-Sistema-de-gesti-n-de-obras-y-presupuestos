import { useEffect, useState } from 'react';
import { api, withQuery } from '../api/client';

const moneda = new Intl.NumberFormat('es-CL');
const campo = 'mt-1 block w-full rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-2';
const secundario = 'rounded-lg border border-outline-variant px-4 py-2 font-semibold disabled:opacity-50';
const inicial = { tipo: '', desde: '', hasta: '', cliente_id: '', tecnico_id: '', estado: '' };

function textoCelda(valor) {
  if (typeof valor === 'number') return moneda.format(valor);
  if (/^\d{4}-\d{2}-\d{2}$/.test(valor ?? '')) return valor.split('-').reverse().join('-');
  return valor ?? '';
}

export default function Reportes() {
  const [catalogos, setCatalogos] = useState(null);
  const [filtros, setFiltros] = useState(inicial);
  const [consulta, setConsulta] = useState(null);
  const [resultado, setResultado] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [exportando, setExportando] = useState(false);
  const [error, setError] = useState('');
  const tipo = catalogos?.tipos.find((opcion) => opcion.id === filtros.tipo);

  useEffect(() => {
    const controller = new AbortController();
    api.request('/reportes/filtros/', { signal: controller.signal }).then((datos) => {
      const filtrosIniciales = { ...inicial, tipo: datos.tipos[0].id, desde: datos.desde, hasta: datos.hasta };
      setCatalogos(datos);
      setFiltros(filtrosIniciales);
      setConsulta({ filtros: filtrosIniciales, pagina: 1 });
    }).catch((err) => {
      if (!controller.signal.aborted) {
        setError(err.message);
        setCargando(false);
      }
    });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!consulta) return;
    const controller = new AbortController();
    const ruta = withQuery('/reportes/', { ...consulta.filtros, page: consulta.pagina });
    api.request(ruta, { signal: controller.signal }).then(setResultado).catch((err) => {
      if (!controller.signal.aborted) setError(err.message);
    }).finally(() => {
      if (!controller.signal.aborted) setCargando(false);
    });
    return () => controller.abort();
  }, [consulta]);

  function consultar(pagina, valores) {
    setError('');
    setCargando(true);
    setResultado(null);
    setConsulta({ filtros: valores, pagina });
  }

  async function descargar(salida) {
    setError('');
    setExportando(true);
    try {
      const blob = await api.download(withQuery('/reportes/', { ...consulta.filtros, salida }));
      const url = URL.createObjectURL(blob);
      const enlace = document.createElement('a');
      enlace.href = url;
      enlace.download = `reporte-${consulta.filtros.tipo}.${salida}`;
      enlace.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (err) {
      setError(err.message);
    } finally {
      setExportando(false);
    }
  }

  function cambiar(campo, valor) {
    setFiltros((actuales) => ({
      ...actuales, [campo]: valor, ...(campo === 'tipo' ? { estado: '' } : {}),
    }));
  }

  return (
    <div className="mx-auto max-w-[1600px] space-y-6 p-4 sm:p-6">
      <header>
        <h1 className="text-3xl font-bold text-on-surface">Reportes</h1>
      </header>
      {error && <p role="alert" className="rounded-lg bg-error-container p-3 text-on-error-container">{error}</p>}
      {catalogos && (
        <form className="rounded-xl bg-surface-container-lowest p-4 shadow-sm space-y-4" onSubmit={(e) => {
          e.preventDefault();
          consultar(1, filtros);
        }}>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            <label>Tipo de reporte
              <select className={campo} value={filtros.tipo} onChange={(e) => cambiar('tipo', e.target.value)}>
                {catalogos.tipos.map((opcion) => <option key={opcion.id} value={opcion.id}>{opcion.nombre}</option>)}
              </select>
            </label>
            <label>{tipo?.fecha} desde
              <input className={campo} type="date" required max={filtros.hasta} value={filtros.desde}
                onChange={(e) => cambiar('desde', e.target.value)} />
            </label>
            <label>{tipo?.fecha} hasta
              <input className={campo} type="date" required min={filtros.desde} value={filtros.hasta}
                onChange={(e) => cambiar('hasta', e.target.value)} />
            </label>
            {[
              ['cliente_id', 'Cliente', catalogos.clientes],
              ['tecnico_id', 'Técnico', catalogos.tecnicos],
              ['estado', 'Estado', tipo?.estados.map(([id, nombre]) => ({ id, nombre })) ?? []],
            ].map(([id, nombre, opciones]) => (
              <label key={id}>{nombre}
                <select className={campo} value={filtros[id]} onChange={(e) => cambiar(id, e.target.value)}>
                  <option value="">Todos</option>
                  {opciones.map((opcion) => <option key={opcion.id} value={opcion.id}>{opcion.nombre}</option>)}
                </select>
              </label>
            ))}
          </div>
          <button disabled={cargando || exportando} className="rounded-lg bg-primary-container px-4 py-2 font-semibold text-on-primary disabled:opacity-50">
            Aplicar filtros
          </button>
        </form>
      )}
      {cargando && <p role="status" className="text-secondary">Cargando reporte…</p>}
      {resultado && (
        <section className="space-y-4 rounded-xl bg-surface-container-lowest p-4 shadow-sm" aria-label="Resultados del reporte">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-xl font-semibold">{catalogos.tipos.find((opcion) => opcion.id === consulta.filtros.tipo)?.nombre}</h2>
              <p className="text-secondary">{moneda.format(resultado.count)} registros con los filtros aplicados</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <button className={secundario} disabled={exportando} onClick={() => descargar('xlsx')}>Descargar Excel</button>
              <button className={secundario} disabled={exportando} onClick={() => descargar('pdf')}>Descargar PDF</button>
            </div>
          </div>
          {exportando && <p role="status" className="text-secondary">Preparando archivo…</p>}
          {resultado.count > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-surface-container-low">
                  <tr>{resultado.results.columnas.map((columna) => <th key={columna} scope="col" className="p-3">{columna}</th>)}</tr>
                </thead>
                <tbody>
                  {resultado.results.filas.map((fila) => (
                    <tr key={fila[0]} className="border-b border-surface-container">
                      {fila.map((valor, i) => <td key={resultado.results.columnas[i]} className="p-3">{textoCelda(valor)}</td>)}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : <p className="py-6 text-center text-secondary">No hay registros para los filtros aplicados.</p>}
          {(resultado.previous || resultado.next) && (
            <nav className="flex flex-wrap items-center gap-2" aria-label="Páginas del reporte">
              <button className={secundario} disabled={!resultado.previous || exportando} onClick={() => consultar(consulta.pagina - 1, consulta.filtros)}>Anterior</button>
              <span className="px-2">Página {consulta.pagina}</span>
              <button className={secundario} disabled={!resultado.next || exportando} onClick={() => consultar(consulta.pagina + 1, consulta.filtros)}>Siguiente</button>
            </nav>
          )}
        </section>
      )}
    </div>
  );
}
