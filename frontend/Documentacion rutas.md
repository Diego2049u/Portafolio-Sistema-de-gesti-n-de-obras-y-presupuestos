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
- Administrador general: gestión de todos los módulos operativos.
- Gerencia: Dashboard y consulta de los demás módulos operativos.
- Finanzas: Dashboard, Obras y Proyectos, Presupuestos y Costos, Costos y Materiales, Facturación y Cobranza, Clientes y Contratos.
- Supervisor: Obras y Proyectos, Costos y Materiales, Clientes y Contratos, Disponibilidad de Técnicos.
- Técnico: Obras y Proyectos.

El primer módulo habilitado para cada rol es su ruta de inicio. Administrador general y Gerencia inician en Dashboard. Finanzas, Supervisor y Técnico inician en Obras y Proyectos. Un rol sin módulos permitidos no recibe el menú completo por defecto.

COMPORTAMIENTO
--------------
- Los enlaces del sidebar son `NavLink` y conservan el estado activo según la URL.
- El acceso directo a una ruta se valida por rol. Si el rol no tiene acceso, se muestra la vista de acceso restringido.
- La raíz `/` redirige a la ruta de inicio del rol. Las rutas desconocidas regresan al inicio permitido o muestran que no hay módulos asignados.
- El navegador puede recargar, guardar y compartir URLs, y atrás/adelante recorren las páginas visitadas.
- Las páginas actuales siguen incluyendo `MainLayout`; el layout global las envuelve y evita duplicar sidebar y encabezado.

SEGURIDAD Y SIGUIENTE INTEGRACIÓN
---------------------------------
Las guardas y el sidebar controlan la navegación en el cliente. No sustituyen los permisos de la API. La aplicación usa el rol devuelto por la sesión autenticada de la API. Los módulos de Gerencia mantienen los controles de consulta y ocultan las acciones que modifican registros.

Para cambiar la asignación de módulos, editar el arreglo `NAV_ITEMS`; no duplicar matrices independientes en Sidebar y App.
