// src/config/navegacion.js

export const ROLES = {
  GERENCIA: 'GERENCIA',
  FINANZAS: 'FINANZAS',
  SUPERVISOR: 'SUPERVISOR',
  TECNICO: 'TECNICO',
  // Alias de compatibilidad para evitar romper código previo que use ROLES.ADMIN
  ADMIN: 'GERENCIA'
};

// Las rutas y roles se centralizan aquí para que el Sidebar y la aplicación
// compartan una única definición de navegación y permisos RBAC.
export const NAV_ITEMS = [
  {
    id: 'dashboard',
    label: 'Dashboard Gerencial',
    icon: 'monitoring',
    path: '/dashboard',
    roles: [ROLES.GERENCIA, ROLES.FINANZAS]
  },
  {
    id: 'obras',
    label: 'Obras y Proyectos',
    icon: 'foundation',
    path: '/obras',
    roles: [ROLES.GERENCIA, ROLES.FINANZAS, ROLES.SUPERVISOR, ROLES.TECNICO]
  },
  {
    id: 'presupuestos',
    label: 'Presupuestos y Costos',
    icon: 'request_quote',
    path: '/presupuestos',
    roles: [ROLES.GERENCIA, ROLES.FINANZAS, ROLES.SUPERVISOR]
  },
  {
    id: 'costos',
    label: 'Costos y Materiales',
    icon: 'inventory_2',
    path: '/costos',
    roles: [ROLES.GERENCIA, ROLES.FINANZAS, ROLES.SUPERVISOR]
  },
  {
    id: 'facturacion',
    label: 'Facturación y Cobranza',
    icon: 'receipt_long',
    path: '/facturacion',
    roles: [ROLES.GERENCIA, ROLES.FINANZAS]
  },
  {
    id: 'clientes',
    label: 'Clientes y Contratos',
    icon: 'group',
    path: '/clientes',
    roles: [ROLES.GERENCIA, ROLES.FINANZAS, ROLES.SUPERVISOR]
  },
  {
    id: 'tecnicos',
    label: 'Disponibilidad Técnicos',
    icon: 'engineering',
    path: '/tecnicos',
    roles: [ROLES.GERENCIA, ROLES.SUPERVISOR]
  },
  {
    id: 'auditoria',
    label: 'Configuración / RBAC',
    icon: 'admin_panel_settings',
    path: '/auditoria',
    roles: [ROLES.GERENCIA]
  }
];

// Alias por compatibilidad con consumidores que usan el nombre menuItems.
export const menuItems = NAV_ITEMS;
