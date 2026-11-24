import { useState } from 'react';
import { NavLink } from 'react-router-dom';
import flyagLogo from '../assets/flyag-logo-pag.png';
import { getAllowedItems } from '../config/navegacion';

export default function Sidebar({ userRole }) {
  const [collapsed, setCollapsed] = useState(() => window.matchMedia('(max-width: 767px)').matches);
  const items = getAllowedItems(userRole);
  const toggleLabel = collapsed ? 'Expandir menú lateral' : 'Plegar menú lateral';
  const labelClass = 'overflow-hidden whitespace-nowrap transition-[max-width,opacity] duration-300 motion-reduce:transition-none';
  const labelWidth = collapsed ? 'max-w-0 opacity-0' : 'max-w-44 opacity-100';

  return (
    <aside className={`relative flex min-h-screen shrink-0 flex-col justify-between border-r border-outline-variant bg-surface-container-lowest transition-[width] duration-300 ease-in-out motion-reduce:transition-none ${collapsed ? 'w-16' : 'w-64'}`}>
      <button
        type="button"
        aria-label={toggleLabel}
        title={toggleLabel}
        aria-expanded={!collapsed}
        aria-controls="fyag-sidebar-navigation"
        onClick={() => setCollapsed((current) => !current)}
        className="absolute -right-4 top-[4.75rem] z-10 grid h-8 w-8 place-items-center rounded-full border border-outline-variant bg-surface-container-lowest text-on-surface shadow-sm hover:bg-surface-container-low focus-visible:outline-2 focus-visible:outline-primary"
      >
        <span aria-hidden="true" className={`material-symbols-outlined transition-transform duration-300 motion-reduce:transition-none ${collapsed ? 'rotate-180' : ''}`}>chevron_left</span>
      </button>
      <div className="flex flex-col gap-6 overflow-hidden px-2 py-4">
        <div className="flex h-10 items-center">
          <img src={flyagLogo} alt="FYAG Logo" className="h-10 w-12 shrink-0 object-contain" />
          <div className={`flex flex-col ${labelClass} ${labelWidth}`}>
            <span className="font-headline-sm text-on-surface font-bold text-sm">FYAG OBRAS</span>
            <span className="font-label-sm text-secondary text-[10px] tracking-wider">ERP Frio y agroindustria</span>
          </div>
        </div>

        <nav id="fyag-sidebar-navigation" className="flex flex-col gap-1" aria-label="Navegación principal">
          <span aria-hidden={collapsed} className={`font-label-sm px-3 py-1 text-[11px] font-semibold uppercase tracking-wider text-secondary ${labelClass} ${labelWidth}`}>
            Módulos de Sistema
          </span>
          {items.map((item) => <NavLink
            key={item.id}
            to={item.path}
            end={item.id !== 'tecnicos'}
            aria-label={item.label}
            title={collapsed ? item.label : undefined}
            className={({ isActive }) => `flex w-full items-center rounded-lg py-2.5 text-sm transition-colors ${isActive ? 'bg-primary text-on-primary font-medium shadow-sm' : 'text-secondary hover:bg-surface-container-low hover:text-on-surface'}`}
          >
            <span aria-hidden="true" className="material-symbols-outlined w-12 shrink-0 text-center text-[20px]">{item.icon}</span>
            <span className={`truncate ${labelClass} ${labelWidth}`}>{item.label}</span>
          </NavLink>)}
        </nav>
      </div>

      <div className="overflow-hidden border-t border-outline-variant bg-surface-container-low/50 px-2 py-4">
        <div className="flex items-center text-[11px] text-secondary" title={collapsed ? 'Auditoría del sistema activa' : undefined}>
          <span className="grid w-12 shrink-0 place-items-center">
            <span className="h-2 w-2 rounded-full bg-emerald-500 motion-safe:animate-pulse" />
          </span>
          <span className={`truncate ${labelClass} ${labelWidth}`}>Auditoría del sistema activa</span>
        </div>
      </div>
    </aside>
  );
}
