import { Link, useLocation } from 'react-router-dom';
import flyagLogo from '../assets/flyag-logo-pag.png';
import { NAV_ITEMS } from '../config/navegacion';

export default function Sidebar({ userRole = 'gerencia' }) {
  const location = useLocation();

  // Filtra los ítems permitidos para el rol actual
  const allowedItems = NAV_ITEMS.filter((item) => item.roles.includes(userRole));

  return (
    <aside className="w-64 bg-surface-container-lowest border-r border-outline-variant flex flex-col justify-between shrink-0 min-h-screen">
      <div className="flex flex-col gap-6 p-4">
        {/* Branding Institucional */}
        <div className="flex items-center gap-3 px-2">
          <img src={flyagLogo} alt="FYAG Logo" className="h-10 w-auto object-contain" />
          <div className="flex flex-col">
            <span className="font-headline-sm text-on-surface font-bold text-sm">FYAG OBRAS</span>
            <span className="font-label-sm text-secondary text-[10px] tracking-wider">ERP v2.4 ENTERPRISE</span>
          </div>
        </div>

        {/* Menú Dinámico según RBAC */}
        <nav className="flex flex-col gap-1">
          <span className="font-label-sm text-[11px] text-secondary px-3 py-1 uppercase tracking-wider font-semibold">
            Módulos de Sistema
          </span>
          {allowedItems.map((item) => {
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.id}
                to={item.path}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-150 ${
                  isActive
                    ? 'bg-primary text-on-primary font-medium shadow-sm'
                    : 'text-secondary hover:bg-surface-container-low hover:text-on-surface'
                }`}
              >
                <span className="material-symbols-outlined text-[20px]">{item.icon}</span>
                <span className="truncate">{item.label}</span>
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Pie del Sidebar - Auditoría en Tiempo Real */}
      <div className="p-4 border-t border-outline-variant bg-surface-container-low/50">
        <div className="flex items-center gap-2 text-secondary text-[11px]">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse shrink-0" />
          <span className="truncate">Auditoría PostgreSQL Activa</span>
        </div>
      </div>
    </aside>
  );
}
