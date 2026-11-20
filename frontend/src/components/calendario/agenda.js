import { useCallback, useEffect, useState } from 'react';
import { api, withQuery } from '../../api/client';
import { claveFecha, diasVisibles, fechaChile } from './fechas';

export const ESTADOS_DISPONIBILIDAD = {
  disponible: 'Disponible', parcial: 'Disponibilidad parcial', ocupado: 'Ocupado', sin_determinar: 'Disponibilidad sin determinar',
};

export const claveConsulta = (form) => [form.inicio_programado, form.fin_estimado, form.tecnico_responsable || '', form.id || ''].join('|');

export function periodoInicial() {
  const dias = diasVisibles(fechaChile(), 'semana');
  return { desde: claveFecha(dias[0]), hasta: claveFecha(dias[6]) };
}

export function rangoLaboralActual() {
  const dias = diasVisibles(fechaChile(), 'semana');
  return { inicio: `${claveFecha(dias[1])}T08:00`, fin: `${claveFecha(dias[5])}T18:00` };
}

export function useAgendaTecnico(tecnicoId) {
  const [periodo, setPeriodo] = useState(periodoInicial);
  const [estado, setEstado] = useState({ data: null, loading: true, error: '' });
  const [version, setVersion] = useState(0);
  useEffect(() => {
    let vigente = true;
    const cargar = async () => {
      setEstado({ data: null, loading: true, error: '' });
      try {
        const data = await api.request(withQuery('/obras/agenda-tecnico/', { tecnico_id: tecnicoId, ...periodo }));
        if (vigente) setEstado({ data, loading: false, error: '' });
      } catch (error) {
        if (vigente) setEstado({ data: null, loading: false, error: error.message });
      }
    };
    cargar();
    return () => { vigente = false; };
  }, [tecnicoId, periodo, version]);

  const onPeriodoChange = useCallback((desde, hasta) => {
    setPeriodo((actual) => actual.desde === desde && actual.hasta === hasta ? actual : { desde, hasta });
  }, []);
  return { ...estado, onPeriodoChange, reintentar: () => setVersion((v) => v + 1) };
}

export function bloquesDelDia(fecha, eventos) {
  if ([0, 6].includes(fecha.getUTCDay())) return [];
  const ocupados = eventos.filter((evento) => evento.fecha === claveFecha(fecha));
  const libres = [];
  for (const [inicio, fin] of [[8, 13], [14, 18]]) {
    let cursor = inicio;
    for (const evento of [...ocupados].sort((a, b) => a.inicio - b.inicio)) {
      const a = Math.max(inicio, evento.inicio), b = Math.min(fin, evento.fin);
      if (a >= b) continue;
      if (a > cursor) libres.push({ inicio: cursor, fin: a, estado: 'disponible', titulo: 'Disponible' });
      cursor = Math.max(cursor, b);
    }
    if (cursor < fin) libres.push({ inicio: cursor, fin, estado: 'disponible', titulo: 'Disponible' });
  }
  return [...ocupados, ...libres, { id: 'colacion', inicio: 13, fin: 14, estado: 'descanso', titulo: 'Colación' }];
}
