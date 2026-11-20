import { NavLink } from 'react-router-dom';
import flyagLogo from '../assets/flyag-logo-pag.png';
import { getAllowedItems } from '../config/navegacion';

export default function Sidebar({ userRole }) {
  const items = getAllowedItems(userRole);

  return (
    <aside className="w-64 bg-surface-container-lowest border-r border-outline-variant flex flex-col justify-between shrink-0 min-h-screen">
      <div className="flex flex-col gap-6 p-4">
        <div className="flex items-center gap-3 px-2">
          <img src={flyagLogo} alt="FYAG Logo" className="h-10 w-auto object-contain" />
          <div className="flex flex-col">
            <span className="font-headline-sm text-on-surface font-bold text-sm">FYAG OBRAS</span>
            <span className="font-label-sm text-secondary text-[10px] tracking-wider">ERP Frio y agroindustria</span>
          </div>
        </div>

        <nav className="flex flex-col gap-1" aria-label="Navegación principal">
          <span className="font-label-sm text-[11px] text-secondary px-3 py-1 uppercase tracking-wider font-semibold">
            Módulos de Sistema
          </span>
          {items.map((item) => <NavLink
            key={item.id}
            to={item.path}
            end={item.id !== 'tecnicos'}
            className={({ isActive }) => `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-150 w-full ${isActive ? 'bg-primary text-on-primary font-medium shadow-sm' : 'text-secondary hover:bg-surface-container-low hover:text-on-surface'}`}
          >
            <span className="material-symbols-outlined text-[20px]">{item.icon}</span>
            <span className="truncate">{item.id === 'auditoria' ? 'Auditoría del sistema' : item.label}</span>
          </NavLink>)}
        </nav>
      </div>

      <div className="p-4 border-t border-outline-variant bg-surface-container-low/50">
        <div className="flex items-center gap-2 text-secondary text-[11px]">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse shrink-0" />
          <span className="truncate">Auditoría del sistema activa</span>
        </div>
      </div>
    </aside>
  );
}
