import { getRoleLabel } from '../config/navegacion';
import AlertasFinancieras from './AlertasFinancieras';

export default function Header({
  breadcrumb = 'FYAG ERP / Módulo Operativo',
  period = '10-2026',
  user = {},
  onLogout,
}) {
  const userName = user?.name || 'Usuario';
  const roleLabel = user?.roleLabel || getRoleLabel(user?.role);
  return (
    <header className="w-full h-16 bg-surface-container-lowest border-b border-outline-variant px-6 flex items-center justify-between gap-4 sticky top-0 z-30">
      {/* Breadcrumb Contextual de la Vista */}
      <div className="flex items-center gap-2 text-xs text-secondary overflow-hidden">
        <span className="font-mono text-primary font-medium truncate">{breadcrumb}</span>
        <span className="bg-surface-container-low text-on-surface-variant font-mono px-2 py-0.5 rounded text-[11px] shrink-0">
          {period}
        </span>
      </div>

      {/* Perfil de Usuario */}
      <div className="flex items-center gap-3 shrink-0">
        {['ADMIN_GENERAL', 'GERENCIA', 'FINANZAS'].includes(user?.role) && <AlertasFinancieras />}
        <div className="flex items-center gap-2.5">
          <div className="flex flex-col text-right">
            <span className="font-headline-sm text-xs text-on-surface font-semibold">
              {userName}
            </span>
            <span className="font-label-sm text-[10px] text-primary">{roleLabel}</span>
          </div>
          <div className="w-8 h-8 rounded-full bg-primary/10 text-primary flex items-center justify-center font-bold text-xs border border-primary/20">
            {userName.charAt(0)}
          </div>
        </div>
        <button
          onClick={onLogout}
          className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-2 text-xs font-semibold text-secondary hover:bg-surface-container-low hover:text-on-surface focus:outline-none focus:ring-2 focus:ring-primary"
          type="button"
          aria-label="Cerrar sesión"
          title="Cerrar sesión"
        >
          <span className="material-symbols-outlined text-[18px]">logout</span>
          <span className="hidden sm:inline">Salir</span>
        </button>
      </div>
    </header>
  );
}
