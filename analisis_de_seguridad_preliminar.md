# Análisis de seguridad preliminar

**Sistema:** ERP de Obras y Presupuestos FYAG  
**Fecha:** 21 de noviembre de 2026

## 1. Resumen ejecutivo

La aplicación mantiene los JWT en cookies `HttpOnly`, valida CSRF para las operaciones de escritura y aplica permisos en la API. En las vistas React revisadas, las entradas se renderizan como texto y no se identificó un punto directo que las interprete como HTML. El generador de cotizaciones PDF sí recibe varios campos de usuario sin escapar antes de pasarlos al intérprete de marcado de ReportLab.

Antes de un despliegue público, las prioridades son retirar y rotar la credencial de PostgreSQL que figura en el código, apartar las cuentas demo con contraseña conocida, verificar HTTPS y los atributos de cookies en el entorno real, y corregir la interpretación de marcado en las cotizaciones.

## 2. Alcance y método

Se revisó el código del directorio de trabajo, incluido el módulo de Reportes, junto con la configuración efectiva de Django en el entorno local. Se siguieron entradas de formularios y parámetros de consulta desde React hasta los serializadores, consultas, servicios y salidas HTML, JSON, PDF y Excel. Se usaron búsquedas por patrones, lectura manual de las coincidencias y pruebas existentes en una base PostgreSQL de pruebas.

**Confirmado en código** indica que la condición se observó directamente. **Riesgo inferido** indica que el código permite razonar sobre un efecto posible que no se reprodujo. **Pendiente de entorno** requiere evidencia del despliegue. El alcance excluyó pruebas activas contra servicios, evaluación del proxy de producción, verificación en navegador del DOM de todas las pantallas y certificación de ausencia de vulnerabilidades. No se cambió el código ni se escribieron datos en la base de la aplicación.

## 3. Hallazgos y comprobaciones

### S-01 · Alta · Credencial de PostgreSQL incluida en el código

**Estado:** confirmado en código. Se inspeccionó `DATABASES` y se comprobó con `git ls-files` que el archivo de configuración está versionado. La conexión usa una contraseña literal y el usuario `postgres`. El host configurado es local. La revisión no determinó si la credencial se reutiliza, si el repositorio fue compartido ni si la base es accesible desde otras máquinas.

**Impacto:** quien obtenga el código recibe una credencial de base de datos. Si está vigente y el entorno permite conectarse, el alcance depende de los privilegios de esa cuenta. También conviene reducir el alcance de una eventual intrusión separando la cuenta de la aplicación de la cuenta con permisos para aplicar migraciones.

**Corrección:** rotar la credencial, cargarla desde el entorno o un gestor de secretos y usar un usuario de PostgreSQL con privilegios mínimos. Revisar exposición previa antes de decidir si hace falta sanear el historial del repositorio. [Configuración de Django](backend/central/settings.py#L163)

### S-02 · Alta si se usa en un entorno compartido · Cuentas demo previsibles

**Estado:** confirmado en código. Se revisó `seed_demo`, su lista de cuentas, el valor por defecto y el método que crea o actualiza las cuentas. El comando activa cuentas con una clave compartida por defecto, incluida la de Administrador general, y muestra la clave en su salida. El inicio de sesión de la cuenta demo se había verificado previamente en la base local.

**Impacto:** si se usan esas cuentas en un entorno accesible por terceros, una credencial conocida puede dar el acceso del rol correspondiente. Ejecutar el comando de nuevo también puede restablecer claves de cuentas demo existentes.

**Corrección:** limitar el comando a un entorno de demostración aislado, evitar imprimir contraseñas y retirar las cuentas demo de ambientes compartidos o productivos. [Carga de datos demo](backend/api/management/commands/seed_demo.py#L33)

### S-03 · Alta en producción si se replica la configuración local · Transporte y cookies

**Estado:** confirmado en configuración local y pendiente de entorno desplegado. Se ejecutó `manage.py check --deploy`. Django informó `W004` (HSTS), `W008` (redirección HTTPS), `W012` (cookie de sesión), `W016` (cookie CSRF) y `W018` (`DEBUG`). Por separado, se inspeccionó la emisión de JWT. Usa `JWT_COOKIE_SECURE = not DEBUG`, así que con el `DEBUG` local los JWT se emiten sin `Secure`. `HttpOnly` se aplica siempre. El chequeo de Django cubre las cookies propias de Django. El atributo del JWT se verificó por inspección de la configuración y del emisor.

**Impacto:** `Secure` restringe el envío de la cookie a HTTPS y `HttpOnly` impide que JavaScript lea su valor. El riesgo de CSRF surge porque el navegador adjunta las cookies automáticamente. Un script que ya se ejecute en el origen de la aplicación también puede realizar solicitudes con la sesión abierta aunque no pueda leer el JWT.

**Corrección:** desplegar con `DEBUG=false`, forzar HTTPS en el borde o en Django y comprobar en el entorno real que ambas cookies tengan `Secure`, `HttpOnly` y `SameSite=Lax`. Activar HSTS después de confirmar que HTTPS funciona de forma estable. Si se confía en `X-Forwarded-Proto`, el proxy debe reemplazar el valor recibido del cliente. Verificar además las cabeceras del sitio React, ya que las de Django podrían aplicarse solo a la API. [Emisión de cookies](backend/api/auth_views.py#L28) · [Configuración HTTP](backend/central/settings.py#L123) · [Django, lista de despliegue](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/) · [OWASP, CSRF](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)

### S-04 · Media · Marcado de usuario interpretado en el PDF de cotización

**Estado:** confirmado en código. Se siguieron los campos de cliente, contacto, contrato, dirección y unidad desde el modelo o serializador hasta `Paragraph`. En ese generador algunos valores llegan directamente al intérprete de marcado. La descripción de la partida sí tiene un escape explícito. El exportador del nuevo módulo de Reportes aplica `escape` a los valores antes de construir cada párrafo.

**Impacto:** entradas con sintaxis de marcado pueden alterar el documento o causar errores de generación. La revisión no confirmó ejecución de JavaScript ni acceso a recursos del servidor. Es un problema de codificación de salida para PDF, distinto de XSS en el navegador.

**Corrección:** escapar todos los valores dinámicos en el punto de salida y reservar el marcado para las etiquetas fijas del documento. Verificar que nombres como `Frío & Agroindustria` y textos con signos de comparación se impriman literalmente. [Cotización](backend/api/pdf_generador.py#L47) · [Exportación de reportes](backend/api/exportar_reportes.py#L58)

### S-05 · Media · Revocación parcial de sesiones y alcance de la cookie de renovación

**Estado:** confirmado en código. Se siguieron login, renovación, cierre de sesión y restablecimiento de contraseña. El login devuelve los datos del usuario en JSON y coloca los JWT en cookies de host con `Path=/`. El acceso dura 15 minutos. La renovación rota el refresh y lo agrega a la lista de revocación. El cierre de sesión borra ambas cookies e intenta revocar el refresh, pero captura cualquier excepción sin diferenciar una falla operativa. La validación de acceso consulta el estado de la cuenta, sin una comprobación adicional de versión de sesión que invalide de inmediato un token de acceso emitido antes del logout o de un restablecimiento.

**Impacto:** si una copia del JWT de acceso sigue vigente y la cuenta continúa activa, puede conservar validez hasta su vencimiento. El navegador también envía la cookie de refresh a rutas del mismo host que no la necesitan. La protección efectiva frente a carreras de renovación entre pestañas queda pendiente.

**Corrección:** registrar y monitorear fallos inesperados de revocación. Si el negocio requiere revocación inmediata, validar una versión de sesión o un identificador revocable en el servidor. Evaluar restringir la cookie de refresh al prefijo de autenticación de forma compatible con renovación y logout. [Flujos de sesión](backend/api/auth_views.py#L107) · [Validación del token](backend/api/authentication.py#L16) · [Restablecimiento](backend/api/views.py#L149)

### S-06 · Media · Protección contra intentos de login dependiente del proceso

**Estado:** confirmado en código, impacto inferido para varios procesos. Se revisaron el límite de login y el contador de fallos. El contador usa IP y correo, y actualiza con una lectura seguida de escritura. No se encontró una configuración de caché compartida en los ajustes revisados. El login también registra los fallos.

**Impacto:** con múltiples procesos y caché local, los contadores pueden quedar repartidos. Las actualizaciones concurrentes pueden perder incrementos. La IP que presenta el proxy también determina si usuarios distintos comparten el límite o si se atribuye correctamente cada intento.

**Corrección:** aplicar límites en el borde y usar contadores atómicos en una caché compartida. Verificar la procedencia de la IP detrás del proxy y considerar MFA para cuentas privilegiadas. [Login](backend/api/auth_views.py#L66) · [Límites configurados](backend/central/settings.py#L219)

### S-07 · Media · Exportaciones sin límite explícito de volumen

**Estado:** confirmado en código, impacto inferido. Se comparó la vista previa paginada con las descargas. La API valida que el rango de fechas esté ordenado, pero no lo limita. Excel se arma en memoria y el PDF acumula todas las filas. Las descargas están restringidas a dos roles y sujetas al límite general de la API.

**Impacto:** un rango muy grande puede consumir memoria y tiempo de proceso. Un número reducido de solicitudes puede seguir siendo costoso si cada reporte contiene muchos registros. No se realizó una prueba de carga.

**Corrección:** establecer límites de filas y concurrencia según el tamaño esperado de la base. Si se necesitan exportaciones masivas, moverlas a un proceso de fondo con límites y caducidad de archivos. [Consulta y descarga](backend/api/reportes.py#L32) · [Generación de archivos](backend/api/exportar_reportes.py#L16)

### S-08 · Media · Consistencia de los estados ante operaciones concurrentes

**Estado:** riesgo inferido. Se compararon los límites de transacción y los bloqueos. Los pagos bloquean la fila de su factura y las transiciones de obra bloquean la obra. Algunas transiciones de presupuesto usan transacciones sin volver a leer el estado bajo bloqueo. El cierre comercial consulta el conjunto de facturas y actualiza la obra, mientras pagos de facturas distintas pueden ejecutarse bajo bloqueos distintos.

**Impacto:** una transacción asegura que sus escrituras se confirmen juntas. Por sí sola no evita que dos operaciones validen el mismo estado anterior o produzcan una decisión de cierre desactualizada. Es un riesgo de integridad y trazabilidad financiera, pendiente de validación concurrente.

**Corrección:** serializar las transiciones por presupuesto y evaluar un orden común de bloqueo por obra y factura en las operaciones que determinan el cierre. Establecer qué eventos deben ser idempotentes y comprobar que el estado final concuerde con los movimientos registrados. [Transiciones de presupuesto](backend/api/services.py#L95) · [Cierre y pagos](backend/api/services.py#L198)

## 4. Controles y cobertura por superficie

| Superficie | Cómo se comprobó | Resultado y límite |
| --- | --- | --- |
| **XSS en navegador** | Se buscaron `dangerouslySetInnerHTML`, `innerHTML`, ejecución dinámica y destinos `href`. Se siguió el renderizado de nombres, errores, filas de reportes y descargas en JSX. | En las rutas revisadas, el contenido se interpola como texto. Las descargas construyen una URL de objeto a partir del archivo recibido. No se identificó un destino directo de HTML controlado por el usuario. Falta verificación interactiva en navegador y confirmar una política CSP en el sitio desplegado. [Reportes](frontend/src/pages/Reportes.jsx) · [OWASP, XSS](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html) |
| **CSRF y CORS** | Se siguió la solicitud a `/auth/csrf/`, el envío de `X-CSRFToken` y el chequeo para métodos de escritura. Se revisaron los decoradores de login, renovación y logout, y el origen permitido con credenciales. | El frontend conserva el token CSRF en memoria. Las escrituras autenticadas por cookie pasan por la validación de Django y las tres operaciones de sesión tienen protección explícita. La prueba existente cubre login sin CSRF y emisión de la cookie de acceso. Queda pendiente probar las demás operaciones sensibles con el navegador y la configuración del dominio real. [Cliente HTTP](frontend/src/api/client.js#L59) · [Autenticación](backend/api/authentication.py#L7) |
| **SQL e inputs** | Se buscaron consultas manuales y se revisó cómo los filtros `q`, identificadores y fechas se convierten en consultas. | En los caminos revisados se usa el ORM con valores de usuario y nombres de campos definidos por el código. No se identificó concatenación de SQL en esos flujos. Reportes valida fechas, enteros y estados. En vistas antiguas conviene homogeneizar los filtros de ID con serializadores para devolver errores de validación consistentes. [Filtros de API](backend/api/views.py#L64) · [Reportes](backend/api/reportes.py#L32) |
| **Autorización y acceso por objeto** | Se compararon el menú, las clases de permisos, el queryset de obras del técnico y las rutas de agenda y reportes. Se revisaron los campos de solo lectura de los serializadores. | La API limita Reportes a Gerencia y Administrador general. Finanzas no puede consultar el Dashboard. El técnico tiene un queryset de obras restringido a las asignadas y la agenda usa su identidad. Las pruebas no cubren todas las combinaciones de rol, método, objeto y campos devueltos. [Permisos](backend/api/permissions.py) · [Obras y agenda](backend/api/views.py#L315) · [Reportes](backend/api/reportes.py#L23) |
| **Excel e inyección de fórmulas** | Se revisó la escritura de celdas y la prueba que abre el XML del XLSX. | Las entradas se escriben como texto explícito. La conversión automática a fórmulas y enlaces está desactivada. La prueba comprueba que un texto válido con `=` se conserva como cadena y que la hoja no contiene fórmulas. [Exportador](backend/api/exportar_reportes.py#L16) · [Pruebas](backend/api/test_reportes.py) |
| **Facturación, pagos y auditoría** | Se revisaron la lista de campos editables, las validaciones de montos y la persistencia de eventos. | Los saldos se calculan en el servidor. Los pagos se corrigen con reversas y la API de auditoría es de lectura. Las instantáneas excluyen el campo de contraseña. La inmutabilidad observada es de aplicación y no equivale a un registro externo resistente a modificaciones por un administrador de base de datos. Los registros también contienen datos personales y financieros que requieren retención y accesos definidos. [Serializadores](backend/api/serializers.py#L371) · [Instantáneas y auditoría](backend/api/views.py#L85) |
| **Dependencias** | Se ejecutó `npm.cmd audit --omit=dev --json` contra el registro npm usando el árbol del frontend. El primer intento falló por acceso al registro y se repitió con autorización. | El informe exitoso devolvió cero avisos para el alcance auditado. Este resultado no incluye herramientas de desarrollo, paquetes Python ni infraestructura. Queda pendiente un escaneo de avisos del backend y un inventario del entorno desplegado. |

## 5. Registro de verificación

| Comprobación | Método y resultado |
| --- | --- |
| Revisión estática | Búsquedas con `rg` y lectura manual de los resultados en `frontend/src`, `backend/api` y `backend/central`. Las referencias de cada hallazgo identifican el código que respalda la conclusión. |
| Django local | `python manage.py check --deploy`. Cinco advertencias detalladas en S-03. No se imprimieron credenciales en este informe. |
| Dependencias del frontend | `npm.cmd audit --omit=dev --json`. Cero avisos en el alcance de ejecución auditado. |
| Pruebas de regresión | `python manage.py test api.tests.RolePermissionTests api.tests.AuthenticationSecurityTests api.tests.AuditTrailTests api.tests.FacturacionWorkflowTests api.test_reportes --noinput`. Pasaron 17 pruebas en PostgreSQL de pruebas. La primera invocación usó un nombre de clase incorrecto y se corrigió en la segunda. Django REST Framework avisó del orden no determinista de algunos listados paginados. |

## 6. Prioridad de corrección

1. **Antes de exponer el sistema:** rotar la credencial de PostgreSQL y retirarla del código, deshabilitar cuentas demo en ambientes compartidos, y verificar HTTPS, cookies y configuración del proxy en el despliegue real.
2. **En la siguiente iteración:** escapar todos los datos interpolados en la cotización PDF, reforzar límites de login y exportación, y decidir si la revocación de accesos debe ser inmediata.
3. **Para ampliar la cobertura:** verificar el DOM de las pantallas con datos representativos, comprobar CSRF y cookies en navegador, ampliar la matriz de permisos por objeto, validar la integridad de transiciones concurrentes y auditar los avisos de dependencias Python.
