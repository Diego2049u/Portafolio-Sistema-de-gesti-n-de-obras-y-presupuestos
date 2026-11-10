import flyagLogo from '../assets/flyag-logo-pag.png';
import { NAV_ITEMS, ROLES } from '../config/navegacion';

const ROLE_ALIASES = {
  ADMIN: ROLES.ADMIN,
  ADMINISTRADOR: ROLES.ADMIN,
  GERENCIA: 'GERENCIA',
  GERENTE: 'GERENCIA',
  FINANZAS: ROLES.FINANZAS,
  SUPERVISOR: ROLES.SUPERVISOR,
  TECNICO: ROLES.TECNICO,
  TÉCNICO: ROLES.TECNICO
};

function normalizeRole(role) {
  const normalizedRole = String(role ?? '').trim().toUpperCase();
  return ROLE_ALIASES[normalizedRole] || normalizedRole;
}

function getAllowedItems(userRole) {
  const normalizedUserRole = normalizeRole(userRole || ROLES.ADMIN);
  const allowedItems = NAV_ITEMS.filter((item) =>
    Array.isArray(item.roles) && item.roles.some((role) => normalizeRole(role) === normalizedUserRole)
  );

  // Evita que un rol inesperado o una configuración incompleta deje el menú vacío.
  return allowedItems.length > 0 ? allowedItems : NAV_ITEMS;
}

function SidebarContent({ items, currentTab, onSelectTab }) {
  const renderItem = (item) => {
    const active = currentTab === item.id;
    const className = `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-150 ${
      active
        ? 'bg-primary text-on-primary font-medium shadow-sm'
        : 'text-secondary hover:bg-surface-container-low hover:text-on-surface'
    }`;
    const contents = (
      <>
        <span className="material-symbols-outlined text-[20px]">{item.icon}</span>
        <span className="truncate">{item.label}</span>
      </>
    );

    return (
      <button
        key={item.id}
        type="button"
        onClick={() => onSelectTab?.(item.id)}
        aria-current={active ? 'page' : undefined}
        className={`${className} w-full text-left`}
      >
        {contents}
      </button>
    );
  };

  return (
    <aside className="w-64 bg-surface-container-lowest border-r border-outline-variant flex flex-col justify-between shrink-0 min-h-screen">
      <div className="flex flex-col gap-6 p-4">
        <div className="flex items-center gap-3 px-2">
          <img src={flyagLogo} alt="FYAG Logo" className="h-10 w-auto object-contain" />
          <div className="flex flex-col">
            <span className="font-headline-sm text-on-surface font-bold text-sm">FYAG OBRAS</span>
            <span className="font-label-sm text-secondary text-[10px] tracking-wider">ERP v2.4 ENTERPRISE</span>
          </div>
        </div>

        <nav className="flex flex-col gap-1" aria-label="Navegación principal">
          <span className="font-label-sm text-[11px] text-secondary px-3 py-1 uppercase tracking-wider font-semibold">
            Módulos de Sistema
          </span>
          {items.map(renderItem)}
        </nav>
      </div>

      <div className="p-4 border-t border-outline-variant bg-surface-container-low/50">
        <div className="flex items-center gap-2 text-secondary text-[11px]">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse shrink-0" />
          <span className="truncate">Auditoría PostgreSQL Activa</span>
        </div>
      </div>
    </aside>
  );
}

export default function Sidebar({
  userRole = ROLES.ADMIN,
  onSelectTab,
  currentTab
}) {
  const items = getAllowedItems(userRole);

  return <SidebarContent items={items} currentTab={currentTab} onSelectTab={onSelectTab} />;
}
