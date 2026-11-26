import GastosGenerales from '../components/GastosGenerales';
import TablePagination, { SortableHeader } from '../components/TablePagination';
import { useTablePagination } from '../components/useTablePagination';
import { useCallback, useEffect, useState } from 'react';
import { api, withQuery } from '../api/client';

const CATEGORIES=['MATERIALES','MANO_DE_OBRA','SUBCONTRATO','EQUIPAMIENTO','VARIOS'];
const FIELD='w-full rounded-lg bg-surface-container-low px-3 py-2 text-on-surface';
const CLP=new Intl.NumberFormat('es-CL',{style:'currency',currency:'CLP',maximumFractionDigits:0});
export default function CostosMateriales({userRole='ADMIN_GENERAL'}){
 const canManage=['ADMIN_GENERAL','FINANZAS','SUPERVISOR'].includes(userRole);
 const [rows,setRows]=useState([]),[works,setWorks]=useState([]),[clients,setClients]=useState([]),[search,setSearch]=useState(''),[categoryFilter,setCategoryFilter]=useState(''),[workFilter,setWorkFilter]=useState(''),[clientFilter,setClientFilter]=useState(''),[techFilter,setTechFilter]=useState(''),[statusFilter,setStatusFilter]=useState(''),[from,setFrom]=useState(''),[to,setTo]=useState('');
 const [modal,setModal]=useState(false),[form,setForm]=useState({obra:'',categoria:CATEGORIES[0],monto:'',descripcion:'',comprobante:''}),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 const consultar = useCallback(() => Promise.all([
   api.listAll(withQuery('/costos/', {
     q: search, categoria: categoryFilter, obra_id: workFilter, cliente_id: clientFilter,
     tecnico_id: techFilter, estado: statusFilter, desde: from, hasta: to,
   })),
   api.listAll('/obras/'),
   api.listAll('/clientes/'),
 ]), [search, categoryFilter, workFilter, clientFilter, techFilter, statusFilter, from, to]);
 const actualizar = useCallback(([costos, obras, clientes]) => {
   setRows(costos);
   setWorks(obras);
   setClients(clientes);
   setError('');
 }, []);
 const load = () => consultar().then(actualizar).catch((err) => setError(err.message));
 useEffect(() => {
   let activo = true;
   consultar().then((datos) => {
     if (activo) actualizar(datos);
   }).catch((err) => { if (activo) setError(err.message); });
   return () => { activo = false; };
 }, [actualizar, consultar]);
 const table = useTablePagination(rows, { filterKey: consultar });
 const [proveedores, setProveedores] = useState([]);
 const [errorProveedores, setErrorProveedores] = useState('');
 useEffect(() => {
   if (!modal) return;
   let activo = true;
   api.listAll('/proveedores/')
     .then((filas) => {
       if (activo) {
         setProveedores(filas);
         setErrorProveedores('');
       }
     })
     .catch((err) => { if (activo) setErrorProveedores(err.message); });
   return () => { activo = false; };
 }, [modal]);
 const [despachos, setDespachos] = useState([]);
 const [errorDespachos, setErrorDespachos] = useState('');
 const obraDespacho = modal && form.categoria === 'MATERIALES' ? form.obra : null;
 useEffect(() => {
   if (!obraDespacho) return;
   const controller = new AbortController();
   api.request('/costos/despachos/' + obraDespacho + '/', { signal: controller.signal })
     .then((data) => {
       if (!controller.signal.aborted) {
         setDespachos(data);
         setErrorDespachos('');
       }
     })
     .catch((err) => { if (!controller.signal.aborted) setErrorDespachos(err.message); });
   return () => controller.abort();
 }, [obraDespacho]);

 const despachoSeleccionado = despachos.find((item) => item.id === Number(form.despacho));
 const desglosado=['MANO_DE_OBRA','MATERIALES'].includes(form.categoria);
 const cantidadValorizada = Number(despachoSeleccionado?.cantidad ?? form.cantidad_real);
 const tarifaValorizada = Number(form.costo_unitario_real);
 const costoRedondeaACero = desglosado && cantidadValorizada > 0 && tarifaValorizada > 0
   && Math.round(cantidadValorizada * 1000) * Math.round(tarifaValorizada * 100) < 50000;

 async function save(event) {
   event.preventDefault();
   if (costoRedondeaACero) return;
   setBusy(true);
   setError('');
   const { id, obra, categoria, descripcion, comprobante, monto, cantidad_real, unidad_real, costo_unitario_real, despacho, proveedor } = form;
   const importe = desglosado
     ? { ...(despacho ? { despacho: Number(despacho) } : { cantidad_real, unidad_real: categoria === 'MANO_DE_OBRA' ? 'h' : unidad_real }), costo_unitario_real }
     : { monto };
   try {
     await api.request(id ? '/costos/' + id + '/' : '/costos/', {
       method: id ? 'PATCH' : 'POST', body: { ...(id ? {} : { obra: Number(obra) }), categoria, descripcion, proveedor: proveedor ? Number(proveedor) : null, comprobante: comprobante || null, ...importe },
     });
     setModal(false);
     await load();
   } catch (err) {
     setError(err.message);
   } finally {
     setBusy(false);
   }
 }
 async function anularDuplicado() {
   const motivo = window.prompt('Motivo para anular este costo duplicado:');
   if (!motivo?.trim()) return;
   setBusy(true);
   setError('');
   try {
     await api.request('/costos/' + form.id + '/', { method: 'DELETE', body: { motivo: motivo.trim() } });
     setModal(false);
     await load();
   } catch (err) {
     setError(err.message);
   } finally {
     setBusy(false);
   }
 }
 const total=rows.reduce((sum,c)=>sum+Number(c.monto||0),0);
 return <div className="mx-auto flex w-full max-w-[1600px] flex-col gap-6 p-6"><header className="flex flex-wrap items-end justify-between gap-4"><div><p className="text-label-sm uppercase text-secondary">Obras y servicios</p><h1 className="text-3xl font-bold text-on-surface">Costos y materiales</h1><p className="mt-1 text-on-surface-variant">Gastos directos vinculados a una obra.</p></div>{canManage&&<button onClick={()=>{setDespachos([]);setErrorDespachos('');setError('');setForm({obra:works.find(w=>['en-proceso','suspendida'].includes(w.estado_operativo))?.id||'',categoria:CATEGORIES[0],monto:'',descripcion:'',comprobante:''});setModal(true)}} className="rounded-lg bg-primary-container px-4 py-2 text-on-primary">Imputar costo</button>}</header>{error&&<p role="alert" className="rounded-lg bg-error-container p-3 text-on-error-container">{error}</p>}
 <section className="grid gap-4 sm:grid-cols-2"><article className="rounded-xl bg-surface-container-lowest p-5 shadow-sm"><span className="text-sm text-secondary">Gasto de los resultados actuales</span><div className="mt-2 text-2xl font-bold">{CLP.format(total)}</div></article><article className="rounded-xl bg-surface-container-lowest p-5 shadow-sm"><span className="text-sm text-secondary">Imputaciones encontradas</span><div className="mt-2 text-2xl font-bold">{rows.length}</div></article></section>
 <section className="rounded-xl bg-surface-container-lowest p-4 shadow-sm"><div className="mb-4 grid gap-3 md:grid-cols-3 lg:grid-cols-4"><input className={FIELD} placeholder="Buscar descripción u obra" value={search} onChange={e=>setSearch(e.target.value)}/><select className={FIELD} value={categoryFilter} onChange={e=>setCategoryFilter(e.target.value)}><option value="">Todas las categorías</option>{CATEGORIES.map(c=><option key={c}>{c}</option>)}</select><select className={FIELD} value={workFilter} onChange={e=>setWorkFilter(e.target.value)}><option value="">Todas las obras</option>{works.map(w=><option key={w.id} value={w.id}>{w.codigo_obra} · {w.nombre_obra}</option>)}</select><select className={FIELD} value={clientFilter} onChange={e=>setClientFilter(e.target.value)}><option value="">Todos los clientes</option>{clients.map(c=><option value={c.id} key={c.id}>{c.razon_social}</option>)}</select><select className={FIELD} value={techFilter} onChange={e=>setTechFilter(e.target.value)}><option value="">Todos los técnicos</option>{[...new Map(works.filter(w=>w.tecnico_responsable).map(w=>[w.tecnico_responsable,{id:w.tecnico_responsable,name:w.tecnico_nombre}])).values()].map(t=><option value={t.id} key={t.id}>{t.name}</option>)}</select><select className={FIELD} value={statusFilter} onChange={e=>setStatusFilter(e.target.value)}><option value="">Todos los estados</option>{['en-proceso','finalizada','suspendida','cancelada'].map(s=><option key={s}>{s}</option>)}</select><input aria-label="Fecha desde" type="date" className={FIELD} value={from} onChange={e=>setFrom(e.target.value)}/><input aria-label="Fecha hasta" type="date" className={FIELD} value={to} onChange={e=>setTo(e.target.value)}/></div><button className="mb-4 rounded bg-surface-container px-4 py-2" onClick={load}>Actualizar</button><div className="overflow-x-auto"><table className="w-full text-left"><thead className="bg-surface-container-low text-xs uppercase text-secondary"><tr>{[['Fecha', c => c.fecha], ['Obra', c => c.obra_codigo], ['Categoría', c => c.categoria], ['Descripción', c => c.descripcion], ['Monto', c => Number(c.monto)], ['Comprobante']].map(([label, value]) => <SortableHeader key={label} label={label} value={value} table={table} />)}</tr></thead><tbody>{table.rows.map(c=><tr className="border-b border-surface-container" key={c.id}><td className="p-3">{c.fecha}</td><td className="p-3">{c.obra_codigo}<div>{works.find(w=>w.id===c.obra)?.nombre_obra}</div></td><td className="p-3">{c.categoria}</td><td className="p-3">{c.descripcion}{c.proveedor_nombre && <div className="text-sm text-secondary">{c.proveedor_nombre}</div>}{c.cantidad_real != null && <div className="text-sm text-secondary">{Number(c.cantidad_real)} {c.unidad_real} ? {CLP.format(Number(c.costo_unitario_real))}</div>}</td><td className="p-3 text-right font-semibold">{CLP.format(Number(c.monto))}</td><td className="p-3">{canManage && ((c.categoria === "MATERIALES" && !c.despacho) || (c.categoria === "MANO_DE_OBRA" && c.cantidad_real == null)) && works.some(w=>w.id===c.obra && ["en-proceso","suspendida"].includes(w.estado_operativo)) && <button type="button" className="link-action mb-1" onClick={()=>{setDespachos([]);setErrorDespachos("");setError("");setForm(c);setModal(true)}}>Completar costo</button>}{c.comprobante?<a className="link-action" href={c.comprobante} target="_blank" rel="noreferrer">Ver comprobante</a>:'—'}</td></tr>)}</tbody></table>{!rows.length&&<p className="p-8 text-center text-secondary">No hay costos para estos filtros.</p>}</div><TablePagination table={table} /></section>
 {['ADMIN_GENERAL','FINANZAS','GERENCIA'].includes(userRole) && <GastosGenerales editable={userRole !== 'GERENCIA'} format={(value) => CLP.format(Number(value))} />}
 {modal&&<div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"><form onSubmit={save} className="w-full max-w-xl space-y-4 rounded-xl bg-surface-container-lowest p-6"><h2 className="text-xl font-bold">{form.id ? "Completar costo registrado" : "Imputar costo a obra"}</h2>{error&&<p role="alert" className="rounded bg-error-container p-2 text-on-error-container">{error}</p>}<label className="block">Obra<select required className={`${FIELD} mt-1`} value={form.obra} disabled={Boolean(form.id)} onChange={e=>{setDespachos([]);setErrorDespachos("");setForm({...form,obra:e.target.value,despacho:""})}}><option value="">Seleccionar obra</option>{works.filter(w=>['en-proceso','suspendida'].includes(w.estado_operativo)&&w.estado_comercial!=='cerrada').map(w=><option key={w.id} value={w.id}>{w.codigo_obra} · {w.nombre_obra}</option>)}</select></label><label className="block">Categoría<select className={`${FIELD} mt-1`} value={form.categoria} disabled={Boolean(form.id)} onChange={e=>{setDespachos([]);setErrorDespachos("");setForm({...form,categoria:e.target.value,despacho:""})}}>{CATEGORIES.map(c=><option key={c}>{c}</option>)}</select></label>{obraDespacho && <label className="block">Despacho de Recursos<select className={FIELD} value={form.despacho ?? ""} onChange={e=>setForm({...form,despacho:e.target.value})}><option value="">Sin despacho vinculado</option>{despachos.map(item=><option key={item.id} value={item.id}>{item.asignacion__material__nombre} ? {Number(item.cantidad)} {item.asignacion__material__unidad} ? {new Date(item.fecha).toLocaleDateString("es-CL")} ? #{item.id}</option>)}</select></label>}{obraDespacho && errorDespachos && <p role="alert" className="text-error">{errorDespachos}</p>}{desglosado ? <div className="grid gap-3 sm:grid-cols-2">{despachoSeleccionado ? <p>{Number(despachoSeleccionado.cantidad)} {despachoSeleccionado.asignacion__material__unidad} despachados</p> : <label>{form.categoria === "MANO_DE_OBRA" ? "Horas trabajadas" : "Cantidad real"}<input required type="number" min="0.001" max="999999999.999" step="0.001" className={FIELD} value={form.cantidad_real ?? ""} onChange={e=>setForm({...form,cantidad_real:e.target.value})} /></label>}<label>{form.categoria === "MANO_DE_OBRA" ? "Costo por hora (CLP)" : "Costo por unidad (CLP)"}<input required type="number" min="0.01" max="9999999999.99" step="0.01" className={FIELD} value={form.costo_unitario_real ?? ""} onChange={e=>setForm({...form,costo_unitario_real:e.target.value})} /></label>{form.categoria === "MATERIALES" && !despachoSeleccionado && <label>Unidad de medida<input required maxLength={20} className={FIELD} value={form.unidad_real ?? ""} onChange={e=>setForm({...form,unidad_real:e.target.value})} /></label>}</div> : <label className="block">Monto (CLP)<input required min="1" type="number" className={`${FIELD} mt-1`} value={form.monto} onChange={e=>setForm({...form,monto:e.target.value})}/></label>}<label className="block">Descripción<textarea required className={`${FIELD} mt-1`} value={form.descripcion} onChange={e=>setForm({...form,descripcion:e.target.value})}/></label>{costoRedondeaACero && <p role="status" className="text-error">El costo se redondea a $0. Aumenta la cantidad o el costo unitario para llegar al menos a $1.</p>}<label className="block">Proveedor (opcional)<select className={FIELD} value={form.proveedor ?? ""} onChange={e=>setForm({...form,proveedor:e.target.value})}><option value="">Sin proveedor</option>{proveedores.filter(item=>item.activo || item.id === Number(form.proveedor)).map(item=><option key={item.id} value={item.id}>{item.razon_social}</option>)}</select></label>{errorProveedores && <p role="alert" className="text-error">{errorProveedores}</p>}<label className="block">URL del comprobante (opcional)<input type="url" className={`${FIELD} mt-1`} value={form.comprobante} onChange={e=>setForm({...form,comprobante:e.target.value})}/></label><div className="flex justify-end gap-2">{form.id && form.categoria === "MATERIALES" && <button type="button" disabled={busy} className="link-action link-action-danger" onClick={anularDuplicado}>Anular duplicado</button>}<button type="button" onClick={()=>setModal(false)} className="rounded px-4 py-2">Cancelar</button><button disabled={busy||costoRedondeaACero||!works.some(w=>['en-proceso','suspendida'].includes(w.estado_operativo))} className="rounded bg-primary-container px-4 py-2 text-on-primary">{busy?'Guardando…':'Guardar costo'}</button></div></form></div>}
 </div>;
}
