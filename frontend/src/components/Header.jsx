export default function Header({
  breadcrumb = 'FYAG ERP / Módulo Operativo',
  period = '10-2026',
  user = { name: 'Ing. R. Morales', roleLabel: 'Gerencia / Admin General' },
}) {
  return (
    <header className="w-full h-16 bg-surface-container-lowest border-b border-outline-variant px-6 flex items-center justify-between gap-4 sticky top-0 z-30">
      {/* Breadcrumb Contextual de la Vista */}
      <div className="flex items-center gap-2 text-xs text-secondary overflow-hidden">
        <span className="font-mono text-primary font-medium truncate">{breadcrumb}</span>
        <span className="bg-surface-container-low text-on-surface-variant font-mono px-2 py-0.5 rounded text-[11px] shrink-0">
          {period}
        </span>
      </div>

      {/* Buscador Global y Perfil de Usuario */}
      <div className="flex items-center gap-4 shrink-0">
        <div className="relative hidden md:flex items-center">
          <span className="material-symbols-outlined absolute left-2.5 text-secondary text-[18px]">
            search
          </span>
          <input
            type="text"
            placeholder="Buscar obra, cliente, RUT..."
            className="w-56 bg-surface-container-low text-on-surface text-xs pl-8 pr-3 py-1.5 rounded-lg focus:outline-none focus:ring-1 focus:ring-primary transition-all"
          />
        </div>

        {/* Perfil del Usuario Autenticado */}
        <div className="flex items-center gap-2.5 pl-2 border-l border-outline-variant">
          <div className="flex flex-col text-right">
            <span className="font-headline-sm text-xs text-on-surface font-semibold">
              {user.name}
            </span>
            <span className="font-label-sm text-[10px] text-primary">{user.roleLabel}</span>
          </div>
          <div className="w-8 h-8 rounded-full bg-primary/10 text-primary flex items-center justify-center font-bold text-xs border border-primary/20">
            {user.name.charAt(0)}
          </div>
        </div>
      </div>
    </header>
  );
}