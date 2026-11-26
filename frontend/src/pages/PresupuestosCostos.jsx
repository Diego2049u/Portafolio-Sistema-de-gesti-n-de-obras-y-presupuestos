import VersionesPresupuesto from '../components/VersionesPresupuesto';
import TablePagination, { SortableHeader } from '../components/TablePagination';
import { useTablePagination } from '../components/useTablePagination';
import { useCallback, useEffect, useState } from 'react';
import { api, withQuery } from '../api/client';

const partidaVacia = { descripcion: '', cantidad: 1, unidad: 'un', precio_unitario: '', costo_unitario: '' };
const blank = { cliente: '', categoria_servicio: '', contacto: '', fecha_vencimiento: '', margen_objetivo: '', contingencia_porcentaje: '', items: [partidaVacia] };
const porcentaje = value => new Intl.NumberFormat('es-CL', { maximumFractionDigits: 2 }).format(value) + '%';
const input='rounded-lg bg-surface-container-low px-3 py-2 text-on-surface';
const money = n => new Intl.NumberFormat('es-CL',{style:'currency',currency:'CLP',maximumFractionDigits:0}).format(Number(n||0));
export default function PresupuestosCostos({ userRole='ADMIN_GENERAL' }) {
  const isManager=userRole==='ADMIN_GENERAL', canCreate=['ADMIN_GENERAL','FINANZAS'].includes(userRole), canRegisterClientDecision=['ADMIN_GENERAL','FINANZAS'].includes(userRole);
  const [rows,setRows]=useState([]),[clients,setClients]=useState([]),[catalog,setCatalog]=useState([]),[contracts,setContracts]=useState([]);
  const [form,setForm]=useState(blank),[editing,setEditing]=useState(null),[modal,setModal]=useState(false),[error,setError]=useState(''),[busy,setBusy]=useState(false),[filter,setFilter]=useState(''),[search,setSearch]=useState(''),[clientFilter,setClientFilter]=useState(''),[categoryFilter,setCategoryFilter]=useState(''),[from,setFrom]=useState(''),[to,setTo]=useState('');
  const load=useCallback(async()=>{setError('');try{const [b,c,cat,co]=await Promise.all([api.listAll(withQuery('/presupuestos/',{q:search,estado:filter,cliente_id:clientFilter,categoria_servicio_id:categoryFilter,desde:from,hasta:to})),api.listAll('/clientes/'),api.listAll('/categorias-servicio/'),api.listAll('/contratos/')]);setRows(b);setClients(c);setCatalog(cat);setContracts(co);}catch(e){setError(e.message)}},[search,filter,clientFilter,categoryFilter,from,to]);
  useEffect(()=>{load()},[load]);
  const activeCategories=catalog;
  const table = useTablePagination(rows, { filterKey: load });
  const filtered=rows;
  const changeItem=(idx,key,value)=>setForm(f=>({...f,items:f.items.map((it,i)=>i===idx?{...it,[key]:value}:it)}));
  const [detalle, setDetalle] = useState(null);
  const [usarCostos, setUsarCostos] = useState(true);
  const open=(row=null)=>{setEditing(row);setUsarCostos(!row || row.margen_objetivo != null);setForm(row?{cliente:row.cliente,categoria_servicio:row.categoria_servicio,contacto:row.contacto,contrato:row.contrato||'',fecha_vencimiento:row.fecha_vencimiento||'',margen_objetivo:row.margen_objetivo??'',contingencia_porcentaje:row.contingencia_porcentaje??'',requiere_aprobacion_gerencia:row.requiere_aprobacion_gerencia,items:(row.items||[]).map(i=>({descripcion:i.descripcion,cantidad:i.cantidad,unidad:i.unidad,precio_unitario:i.precio_unitario,costo_unitario:i.costo_unitario??''}))}:blank);setError('');setModal(true)};
  async function save(event) {
    event.preventDefault();
    setBusy(true);
    setError('');
    const body = {
      ...form,
      fecha_vencimiento: form.fecha_vencimiento || null,
      cliente: Number(form.cliente),
      categoria_servicio: Number(form.categoria_servicio),
      contrato: form.contrato ? Number(form.contrato) : null,
      margen_objetivo: usarCostos ? form.margen_objetivo : null,
      contingencia_porcentaje: usarCostos ? form.contingencia_porcentaje : null,
      items: form.items.map(({ costo_unitario, precio_unitario, ...partida }) =>
        usarCostos ? { ...partida, costo_unitario } : { ...partida, precio_unitario }),
    };
    try {
      const path = editing ? '/presupuestos/' + editing.id + '/' : '/presupuestos/';
      const saved = await api.request(path, { method: editing ? 'PATCH' : 'POST', body });
      setModal(false);
      if (usarCostos) setDetalle(saved);
      await load();
    } catch (error) {
      setError(error.message);
    } finally {
      setBusy(false);
    }
  }
  const action=async (row,path,body={})=>{setBusy(true);setError('');try{await api.request(`/presupuestos/${row.id}/${path}/`,{method:'POST',body});await load()}catch(e){setError(e.message)}finally{setBusy(false)}};
  const [presupuestoVersiones, setPresupuestoVersiones] = useState(null);
  const download=async row=>{try{const blob=await api.download(`/presupuestos/${row.id}/exportar-pdf/`);const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=`${row.numero_presupuesto}.pdf`;a.click();window.setTimeout(()=>URL.revokeObjectURL(url),1000)}catch(e){setError(e.message)}};
  const label={borrador:'Borrador',pendiente_gerencia:'Pendiente de aprobación interna',enviado:'Enviado al cliente',aprobado:'Aprobado',rechazado:'Rechazado'};
  return <div className="mx-auto flex w-full max-w-[1600px] flex-col gap-6 p-6"><header className="flex flex-wrap items-end justify-between gap-4"><div><p className="text-label-sm uppercase text-secondary">Gestión comercial</p><h1 className="text-3xl font-bold text-on-surface">Presupuestos y costos</h1><p className="mt-1 text-on-surface-variant">Partidas, aprobaciones internas y decisión del cliente.</p></div>{canCreate&&<button onClick={()=>open()} className="rounded-lg bg-primary-container px-4 py-2 font-semibold text-on-primary">Nuevo presupuesto</button>}</header>
    {error&&<p role="alert" className="rounded-lg bg-error-container p-3 text-on-error-container">{error}</p>}
    <section className="rounded-xl bg-surface-container-lowest p-4 shadow-sm"><div className="mb-4 grid gap-3 md:grid-cols-3 lg:grid-cols-6"><input className={input} placeholder="Buscar número, cliente o partida" value={search} onChange={e=>setSearch(e.target.value)}/><select className={input} value={filter} onChange={e=>setFilter(e.target.value)}><option value="">Todos los estados</option>{Object.entries(label).map(([id,l])=><option key={id} value={id}>{l}</option>)}</select><select className={input} value={clientFilter} onChange={e=>setClientFilter(e.target.value)}><option value="">Todos los clientes</option>{clients.map(c=><option value={c.id} key={c.id}>{c.razon_social}</option>)}</select><select className={input} value={categoryFilter} onChange={e=>setCategoryFilter(e.target.value)}><option value="">Todos los servicios</option>{activeCategories.map(c=><option value={c.id} key={c.id}>{c.nombre}</option>)}</select><input type="date" aria-label="Emitido desde" className={input} value={from} onChange={e=>setFrom(e.target.value)}/><input type="date" aria-label="Emitido hasta" className={input} value={to} onChange={e=>setTo(e.target.value)}/></div><button className="mb-4 rounded bg-surface-container px-4 py-2" onClick={load}>Actualizar</button><div className="overflow-x-auto"><table className="w-full text-left"><thead><tr className="border-b text-xs uppercase text-secondary">{[['Número', r => r.numero_presupuesto], ['Cliente', r => r.cliente_nombre], ['Servicio', r => r.categoria_servicio_nombre], ['Partidas', r => r.items?.length || 0], ['Total', r => Number(r.monto_total)], ['Estado', r => label[r.estado]], ['Aprobación interna', r => r.aprobacion_gerencia], ['Acciones']].map(([label, value]) => <SortableHeader key={label} label={label} value={value} table={table} />)}</tr></thead><tbody>{table.rows.map(r=><tr className="border-b border-surface-container" key={r.id}><td className="p-3">{r.numero_presupuesto}</td><td className="p-3">{r.cliente_nombre||clients.find(c=>c.id===r.cliente)?.razon_social}</td><td className="p-3">{r.categoria_servicio_nombre||activeCategories.find(c=>c.id===r.categoria_servicio)?.nombre}</td><td className="p-3">{r.items?.length||0}</td><td className="p-3">{money(r.monto_total)}</td><td className="p-3">{label[r.estado]||r.estado}</td><td className="p-3">{r.aprobacion_gerencia||'No requerida'}</td><td className="min-w-64 p-3"><div className="flex flex-wrap gap-2 text-sm">{r.estado==='borrador'&&canCreate&&<><button className="link-action" onClick={()=>open(r)}>Editar</button><button disabled={busy} className="link-action" onClick={()=>action(r,'enviar')}>Enviar</button>{isManager&&<button disabled={busy} className="link-action" onClick={()=>action(r,'exigir-aprobacion-gerencia')}>Exigir aprobación</button>}</>}{r.estado==='pendiente_gerencia'&&isManager&&<><button disabled={busy} className="link-action" onClick={()=>action(r,'aprobar-gerencia',{decision:'aprobada'})}>Aprobar</button><button disabled={busy} className="link-action link-action-danger" onClick={()=>action(r,'aprobar-gerencia',{decision:'rechazada'})}>Rechazar</button></>}{r.estado==='enviado'&&canRegisterClientDecision&&<><button disabled={busy} className="link-action" onClick={()=>action(r,'decision-cliente',{decision:'aprobado'})}>Registrar aceptación</button><button disabled={busy} className="link-action link-action-danger" onClick={()=>action(r,'decision-cliente',{decision:'rechazado'})}>Registrar rechazo</button></>}{<button className="link-action" onClick={()=>setPresupuestoVersiones(r)}>Versiones</button>}<button className="link-action" onClick={()=>setDetalle(r)}>Rentabilidad</button><button className="link-action" onClick={()=>download(r)}>PDF</button></div></td></tr>)}</tbody></table>{!filtered.length&&<p className="p-8 text-center text-secondary">No hay presupuestos para mostrar.</p>}</div><TablePagination table={table} /></section>
    {presupuestoVersiones && <VersionesPresupuesto presupuesto={presupuestoVersiones} format={money} onClose={() => setPresupuestoVersiones(null)} />}
    {detalle && <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <section role="dialog" aria-modal="true" aria-labelledby="rentabilidad-titulo" className="w-full max-w-xl space-y-4 rounded-xl bg-surface-container-lowest p-6">
        <h2 id="rentabilidad-titulo" className="text-xl font-bold">Rentabilidad · {detalle.numero_presupuesto}</h2>
        {detalle.margen_objetivo == null ? <p>Este presupuesto se guardó sin un desglose de costos, reserva y margen.</p> :
          <dl className="grid grid-cols-[1fr_auto] gap-x-4 gap-y-2">
            <dt>Costo base estimado</dt><dd>{money(detalle.costo_base)}</dd>
            <dt>Reserva para imprevistos ({porcentaje(detalle.contingencia_porcentaje)})</dt><dd>{money(detalle.reserva_imprevistos)}</dd>
            <dt>Margen objetivo sobre venta neta</dt><dd>{porcentaje(detalle.margen_objetivo)}</dd>
            <dt>Precio de venta neto</dt><dd>{money(detalle.monto_neto)}</dd>
            <dt className="font-semibold">Ganancia prevista con uso total de la reserva</dt><dd className="font-semibold">{money(detalle.ganancia_prevista)}</dd>
          </dl>}
        <button type="button" className="rounded bg-surface-container px-4 py-2" onClick={() => setDetalle(null)}>Cerrar</button>
      </section>
    </div>}
    {modal&&<div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"><form onSubmit={save} className="max-h-[90vh] w-full max-w-3xl space-y-4 overflow-y-auto rounded-xl bg-surface-container-lowest p-6"><h2 className="text-xl font-bold">{editing?'Editar borrador':'Crear presupuesto'}</h2>{error&&<p role="alert" className="rounded bg-error-container p-2 text-on-error-container">{error}</p>}<div className="grid gap-3 sm:grid-cols-2"><label>Cliente<select required className={`${input} mt-1 w-full`} value={form.cliente} onChange={e=>setForm({...form,cliente:e.target.value,contacto:clients.find(c=>c.id===Number(e.target.value))?.contacto_principal||''})}><option value="">Seleccionar cliente</option>{clients.filter(c=>c.estado==='activo').map(c=><option value={c.id} key={c.id}>{c.razon_social}</option>)}</select></label><label>Servicio<select required className={`${input} mt-1 w-full`} value={form.categoria_servicio} onChange={e=>setForm({...form,categoria_servicio:e.target.value})}><option value="">Seleccionar servicio</option>{activeCategories.map(c=><option key={c.id} value={c.id}>{c.nombre}</option>)}</select></label><label>Contacto<input required className={`${input} mt-1 w-full`} value={form.contacto} onChange={e=>setForm({...form,contacto:e.target.value})}/></label><label>Vencimiento<input type="date" className={`${input} mt-1 w-full`} value={form.fecha_vencimiento} onChange={e=>setForm({...form,fecha_vencimiento:e.target.value})}/></label><label>Contrato (opcional)<select className={`${input} mt-1 w-full`} value={form.contrato} onChange={e=>setForm({...form,contrato:e.target.value})}><option value="">Sin contrato</option>{contracts.filter(c=>!form.cliente||c.cliente===Number(form.cliente)).map(c=><option key={c.id} value={c.id}>{c.numero_contrato} · {c.nombre}</option>)}</select></label>{isManager&&<label className="flex items-center gap-2 self-end"><input type="checkbox" checked={!!form.requiere_aprobacion_gerencia} onChange={e=>setForm({...form,requiere_aprobacion_gerencia:e.target.checked})}/> Requiere aprobación interna</label>}</div>
      {editing && !usarCostos && <button type="button" className="link-action" onClick={() => setUsarCostos(true)}>Configurar costos y margen</button>}
      {usarCostos && <fieldset className="grid gap-3 sm:grid-cols-2">
        <legend className="mb-2 font-semibold">Rentabilidad</legend>
        <label>Reserva sobre costo base (%)
          <input className={`${input} mt-1 w-full`} required type="number" min="0" max="100" step="0.01" value={form.contingencia_porcentaje}
            onChange={event => setForm({ ...form, contingencia_porcentaje: event.target.value })} />
        </label>
        <label>Margen sobre venta neta (%)
          <input className={`${input} mt-1 w-full`} required type="number" min="0" max="99.99" step="0.01" value={form.margen_objetivo}
            onChange={event => setForm({ ...form, margen_objetivo: event.target.value })} />
        </label>
      </fieldset>}
      <h3 className="font-semibold">Partidas</h3>{form.items.map((item,i)=><div key={i} className="grid gap-2 sm:grid-cols-12"><input required placeholder="Descripción" className={`${input} self-end sm:col-span-5`} value={item.descripcion} onChange={e=>changeItem(i,'descripcion',e.target.value)}/><label className="min-w-0 sm:col-span-2"><span className="block text-body-sm text-on-surface">Cantidad</span><input required type="number" min="1" placeholder="Cantidad" className={`${input} mt-1 w-full min-w-0`} value={item.cantidad} onChange={e=>changeItem(i,'cantidad',Number(e.target.value))}/></label><label className="min-w-0 sm:col-span-2"><span className="block text-body-sm text-on-surface">Unidad</span><input placeholder="Unidad" className={`${input} mt-1 w-full min-w-0`} value={item.unidad} onChange={e=>changeItem(i,'unidad',e.target.value)}/></label><label className="min-w-0 sm:col-span-2"><span className="block text-body-sm text-on-surface">{usarCostos ? 'Costo unitario' : 'Precio unitario'}</span><input required type="number" min="0" max="999999999999" className={`${input} mt-1 w-full min-w-0`} value={usarCostos ? item.costo_unitario : item.precio_unitario} onChange={e=>changeItem(i, usarCostos ? 'costo_unitario' : 'precio_unitario', e.target.value)}/></label><button type="button" className="link-action link-action-danger self-end" onClick={()=>setForm({...form,items:form.items.filter((_,j)=>i!==j)})}>Quitar</button></div>)}<button type="button" className="link-action" onClick={()=>setForm({...form,items:[...form.items,partidaVacia]})}>+ Agregar partida</button><div className="flex justify-end gap-2"><button type="button" className="rounded px-4 py-2" onClick={()=>setModal(false)}>Cancelar</button><button disabled={busy||!form.items.length} className="rounded bg-primary-container px-4 py-2 text-on-primary">{busy?'Guardando…':'Guardar borrador'}</button></div></form></div>}
  </div>;
}
