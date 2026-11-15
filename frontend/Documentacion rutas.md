NAVEGACIÓN POR RUTAS Y ACCESO POR ROL
=====================================

La aplicación usa React Router para que cada módulo tenga una URL navegable. El mapa de rutas y roles está centralizado en `src/config/navegacion.js`; el sidebar y las rutas protegidas consumen esa misma configuración.

RUTAS
-----
- `/dashboard`
- `/obras`
- `/presupuestos`
- `/costos`
- `/facturacion`
- `/clientes`
- `/tecnicos`
- `/auditoria`

ASIGNACIÓN ACTUAL DE MÓDULOS
----------------------------
- Gerencia: todos los módulos.
- Finanzas: Dashboard, Obras y Proyectos, Presupuestos y Costos, Costos y Materiales, Facturación y Cobranza, Clientes y Contratos.
- Supervisor: Obras y Proyectos, Costos y Materiales, Clientes y Contratos, Disponibilidad de Técnicos.
- Técnico: Obras y Proyectos.

El primer módulo habilitado para cada rol es su ruta de inicio: Dashboard para Gerencia y Finanzas; Obras y Proyectos para Supervisor y Técnico. Un rol sin módulos permitidos no recibe el menú completo por defecto.

COMPORTAMIENTO
--------------
- Los enlaces del sidebar son `NavLink` y conservan el estado activo según la URL.
- El acceso directo a una ruta se valida por rol. Si el rol no tiene acceso, se muestra la vista de acceso restringido.
- La raíz `/` redirige a la ruta de inicio del rol. Las rutas desconocidas regresan al inicio permitido o muestran que no hay módulos asignados.
- El navegador puede recargar, guardar y compartir URLs, y atrás/adelante recorren las páginas visitadas.
- Las páginas actuales siguen incluyendo `MainLayout`; el layout global las envuelve y evita duplicar sidebar y encabezado.

SEGURIDAD Y SIGUIENTE INTEGRACIÓN
---------------------------------
Las guardas y el sidebar controlan la navegación en el cliente. No sustituyen los permisos de la API. El usuario de demostración de `App.jsx` aún simula una sesión de Gerencia y `Auth.jsx` todavía no carga la sesión real. En la integración posterior se debe obtener el rol desde la sesión autenticada por cookies HttpOnly, restaurar la sesión al recargar y mantener la autorización correspondiente en el backend.

Para cambiar la asignación de módulos, editar el arreglo `NAV_ITEMS`; no duplicar matrices independientes en Sidebar y App.
