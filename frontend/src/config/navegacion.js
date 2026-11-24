// src/config/navegacion.js

export const ROLES = {
  ADMIN_GENERAL: 'ADMIN_GENERAL',
  GERENCIA: 'GERENCIA',
  FINANZAS: 'FINANZAS',
  SUPERVISOR: 'SUPERVISOR',
  TECNICO: 'TECNICO',
  // Alias de compatibilidad para evitar romper código previo que use ROLES.ADMIN
  ADMIN: 'ADMIN_GENERAL'
};

const ROLE_ALIASES = {
  ADMIN: ROLES.ADMIN_GENERAL,
  ADMINISTRADOR: ROLES.ADMIN_GENERAL,
  GERENTE: ROLES.GERENCIA,
};

export function normalizeRole(role) {
  const value = String(role ?? '').trim().normalize('NFD').replace(/[\u0300-\u036f]/g, '').toUpperCase();
  return ROLE_ALIASES[value] || value;
}

export function getAllowedItems(role) {
  const normalizedRole = normalizeRole(role);
  return NAV_ITEMS.filter((item) => item.roles.some((itemRole) => normalizeRole(itemRole) === normalizedRole));
}

export function getDefaultPath(role) {
  return getAllowedItems(role)[0]?.path || null;
}

export function getRoleLabel(role) {
  const normalizedRole = normalizeRole(role);
  return {
    [ROLES.ADMIN_GENERAL]: 'Administrador general',
    [ROLES.GERENCIA]: 'Gerencia',
    [ROLES.FINANZAS]: 'Finanzas',
    [ROLES.SUPERVISOR]: 'Supervisor de Obras',
    [ROLES.TECNICO]: 'Técnico',
  }[normalizedRole] || 'Rol sin asignar';
}

// Las rutas y roles se centralizan aquí para que el Sidebar y la aplicación
// compartan una única definición de navegación y permisos RBAC.
export const NAV_ITEMS = [
  {
    id: 'dashboard',
    label: 'Dashboard Gerencial',
    icon: 'monitoring',
    path: '/dashboard',
    roles: [ROLES.ADMIN_GENERAL, ROLES.GERENCIA]
  },
  {
    id: 'obras',
    label: 'Obras y Proyectos',
    icon: 'foundation',
    path: '/obras',
    roles: [ROLES.ADMIN_GENERAL, ROLES.GERENCIA, ROLES.FINANZAS, ROLES.SUPERVISOR, ROLES.TECNICO]
  },
  {
    id: 'reportes',
    label: 'Reportes',
    icon: 'summarize',
    path: '/reportes',
    roles: [ROLES.ADMIN_GENERAL, ROLES.GERENCIA, ROLES.FINANZAS]
  },
  {
    id: 'recursos',
    label: 'Recursos',
    icon: 'category',
    path: '/recursos',
    roles: [ROLES.ADMIN_GENERAL, ROLES.GERENCIA, ROLES.SUPERVISOR]
  },
  {
    id: 'mi-horario',
    label: 'Mi horario',
    icon: 'calendar_month',
    path: '/mi-horario',
    roles: [ROLES.TECNICO]
  },
  {
    id: 'presupuestos',
    label: 'Presupuestos y Costos',
    icon: 'request_quote',
    path: '/presupuestos',
    roles: [ROLES.ADMIN_GENERAL, ROLES.GERENCIA, ROLES.FINANZAS]
  },
  {
    id: 'costos',
    label: 'Costos y Materiales',
    icon: 'inventory_2',
    path: '/costos',
    roles: [ROLES.ADMIN_GENERAL, ROLES.GERENCIA, ROLES.FINANZAS, ROLES.SUPERVISOR]
  },
  {
    id: 'facturacion',
    label: 'Facturación y Cobranza',
    icon: 'receipt_long',
    path: '/facturacion',
    roles: [ROLES.ADMIN_GENERAL, ROLES.GERENCIA, ROLES.FINANZAS]
  },
  {
    id: 'clientes',
    label: 'Clientes y Contratos',
    icon: 'group',
    path: '/clientes',
    roles: [ROLES.ADMIN_GENERAL, ROLES.GERENCIA, ROLES.FINANZAS, ROLES.SUPERVISOR]
  },
  {
    id: 'tecnicos',
    label: 'Disponibilidad Técnicos',
    icon: 'engineering',
    path: '/tecnicos',
    roles: [ROLES.ADMIN_GENERAL, ROLES.GERENCIA, ROLES.SUPERVISOR]
  },
  {
    id: 'auditoria',
    label: 'Auditoría del sistema',
    icon: 'history',
    path: '/auditoria',
    roles: [ROLES.ADMIN_GENERAL, ROLES.GERENCIA]
  }
];

// Alias por compatibilidad con consumidores que usan el nombre menuItems.
export const menuItems = NAV_ITEMS;
