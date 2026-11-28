# Despliegue de FYAG en Render

## PostgreSQL y Django

1. Crea una base PostgreSQL y un Web Service Python en la misma región. Vincula al Web Service la rama del repositorio que contiene estos cambios.
2. Configura el Web Service con directorio raíz `backend`.

| Opción | Valor |
|---|---|
| Build Command | `python -m pip install -r requirements.txt && python manage.py collectstatic --noinput` |
| Start Command | `python manage.py migrate --noinput && gunicorn central.wsgi:application --bind 0.0.0.0:$PORT` |
| `DATABASE_URL` | URL interna de PostgreSQL de Render |
| `DJANGO_SECRET_KEY` | Clave generada para este entorno |
| `DJANGO_DEBUG` | `false` |
| `FYAG_ALLOWED_HOSTS` | Host de Django y host del frontend, separados por comas, sin esquema ni ruta |
| `FYAG_FRONTEND_ORIGINS` | URL HTTPS del frontend, sin barra final |
| `FYAG_TRUST_PROXY_HEADERS` | `true` |
| `FYAG_SECURE_SSL_REDIRECT` | `true` |

Si el frontend todavía no existe, configura primero el host de Django y completa los valores del frontend cuando tengas su URL. El arranque aplica las migraciones pendientes antes de iniciar Gunicorn. WhiteNoise sirve los archivos de Django recolectados durante el build. Para trabajar en local, configura los valores `FYAG_DB_*` del ejemplo con los datos de tu PostgreSQL. Una vez comprobado HTTPS en el dominio de Django, puedes activar HSTS con `FYAG_HSTS_SECONDS=3600`.

## React

Crea un Static Site con directorio raíz `frontend`, comando `npm ci && npm run build`, directorio de publicación `dist` y variable `VITE_API_URL=/api`. En **Redirects/Rewrites**, agrega estas reglas en este orden:

| Acción | Origen | Destino |
|---|---|---|
| Rewrite | `/api/*` | `https://HOST-BACKEND.onrender.com/api/*` |
| Rewrite | `/*` | `/index.html` |

Sustituye el host de ejemplo por el del servicio Django. Comprueba en la URL del frontend que el login y una consulta autenticada funcionan, y que puedes recargar una ruta interna. La primera reescritura conserva `/api` en el origen visible para el navegador.

## Datos iniciales de demostración

Ejecuta `seed_demo` una vez, tras el primer arranque de Django, únicamente contra la base destinada a la demo. El comando también actualiza las cuentas demo existentes y restablece sus contraseñas.

En el plan gratuito puedes ejecutarlo desde el clon local con el entorno virtual activo y la **URL externa** de PostgreSQL. Restringe temporalmente el acceso externo a tu IP y usa TLS con `sslmode=require` en la URL. Ejecuta estos comandos desde la raíz del repositorio:

```powershell
$env:DATABASE_URL = Read-Host 'URL externa de la base Render de demo, con sslmode=require'
$env:FYAG_DEMO_PASSWORD = Read-Host 'Contraseña exclusiva de la demo'
try {
    python backend/manage.py seed_demo
} finally {
    Remove-Item Env:DATABASE_URL, Env:FYAG_DEMO_PASSWORD
}
```

El comando lista los correos creados. Entra con `gerencia@fyag.cl` y la clave que elegiste. Retira el acceso externo cuando termines si el servicio Django usa la URL interna.
