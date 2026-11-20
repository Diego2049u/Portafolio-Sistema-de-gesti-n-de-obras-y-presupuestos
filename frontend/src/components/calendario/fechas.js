export function fechaChile(ahora = new Date()) {
  const partes = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Santiago', year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(ahora);
  const valor = (tipo) => partes.find((parte) => parte.type === tipo).value;
  return new Date(`${valor('year')}-${valor('month')}-${valor('day')}T12:00:00Z`);
}

export function sumarDias(fecha, dias) {
  const resultado = new Date(fecha);
  resultado.setUTCDate(resultado.getUTCDate() + dias);
  return resultado;
}

export function diasVisibles(fecha, vista) {
  if (vista === 'dia') return [fecha];
  const domingo = sumarDias(fecha, -fecha.getUTCDay());
  return Array.from({ length: 7 }, (_, indice) => sumarDias(domingo, indice));
}

export const claveFecha = (fecha) => fecha.toISOString().slice(0, 10);
export const formatearFecha = (fecha, opciones) => new Intl.DateTimeFormat('es-CL', {
  ...opciones, timeZone: 'UTC',
}).format(fecha);
