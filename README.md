# Constru-trans

Sistema de gestión de materiales de construcción desarrollado con Django.

## Requisitos

- Python 3.11 o superior (se recomienda 3.12)
- Conexión a Internet durante la instalación para descargar las dependencias

## Instalación automática

### Windows (PowerShell)

Desde la carpeta del proyecto:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\setup\setup_windows.ps1
```

También puedes hacer doble clic en `setup\setup_project.bat`, o pasar opciones:

```powershell
.\setup\setup_project.bat --seed          # además carga datos de prueba
.\setup\setup_project.bat --reset-db      # aparta una base local dañada y crea una limpia
```

### macOS y Linux

```bash
bash setup/setup_macos_linux.sh
```

El mismo instalador con opciones:

```bash
bash setup/setup_project.sh --dev --seed            # herramientas de desarrollo + datos de prueba
bash setup/setup_project.sh --reset-db              # aparta una db.sqlite3 dañada y crea una limpia
bash setup/setup_project.sh --no-fetch-credentials  # no usar el repositorio compartido de credenciales
```

### Qué hace el instalador

1. Selecciona un Python 3.11 o superior.
2. Reutiliza el entorno virtual del proyecto (`.venv`, `venv`, `.venv-*` o el que esté activado) y,
   si no existe, crea `.venv`. Nunca borra un entorno ajeno.
3. Instala `requirements.txt` (y `requirements/dev.txt` con `--dev`).
4. Prepara `.env`: intenta traer las credenciales compartidas del repositorio privado del equipo
   (`--no-fetch-credentials` para omitirlo) y, si no puede, copia `.env.example`. **Nunca sobrescribe
   un `.env` existente.**
5. Garantiza una `SECRET_KEY` válida y **fija** en `.env` (no se regenera en cada arranque, así no se
   invalidan las sesiones al reiniciar `runserver`).
6. Comprueba la configuración de Django y aplica las migraciones. Si la base local quedó a medias
   entre dos versiones del esquema, lo indica y sugiere `--reset-db` (la base anterior se aparta como
   `db.sqlite3.broken-<fecha>`, no se borra).
7. Si `DATABASE_URL` está configurada, aplica también las migraciones a la base remota.

### Iniciar el servidor

```bash
# macOS / Linux
.venv/bin/python manage.py runserver

# Windows
.venv\Scripts\python.exe manage.py runserver
```

Abre <http://127.0.0.1:8000/> en el navegador.

## Variables de entorno

Todas las variables disponibles están documentadas en `.env.example`. Las más importantes:

| Variable | Para qué sirve |
| --- | --- |
| `SECRET_KEY` | Clave de firma de Django. Debe ser fija. |
| `DEBUG` | `True` en desarrollo. |
| `DATABASE_URL` | Vacía = SQLite local. Con URL de PostgreSQL/Neon, esa pasa a ser la base `default`. |
| `OPENWEATHER_API_KEY` | Habilita el pronóstico en el panel del conductor. |
| `EMAIL_*` / `RESEND_*` | Envío del correo de recuperación de contraseña. |

## Clima en el panel del conductor

El panel consulta el pronóstico de OpenWeather para la ciudad de la próxima entrega asignada y su hora
programada. Crea una API key en [OpenWeather](https://openweathermap.org/api) y agrega
`OPENWEATHER_API_KEY=tu_api_key` al `.env`. El pronóstico se actualiza en caché cada 10 minutos. Sin
API key, el panel informa el motivo y el resto de funciones siguen operando.

## Correo para recuperar contraseña

Por defecto se usa el backend de correo configurado en Django (`EMAIL_BACKEND`, `EMAIL_HOST`,
`EMAIL_HOST_USER` y demás variables `EMAIL_*`). Para Gmail, usa una contraseña de aplicación.

Como alternativa puedes usar [Resend](https://resend.com/) agregando al `.env`:

```env
RESEND_API_KEY=re_tu_api_key
RESEND_FROM_EMAIL=Constru-Trans <no-reply@correo.tudominio.com>
```

El dominio debe estar verificado en Resend. Si faltan esas variables, se usa el backend normal de Django.

## Desarrollo y pruebas

```bash
# macOS / Linux
.venv/bin/python -m pip install -r requirements/dev.txt
.venv/bin/python manage.py check
.venv/bin/python -m pytest
.venv/bin/python -m ruff check .

# Windows
.venv\Scripts\python.exe -m pip install -r requirements\dev.txt
.venv\Scripts\python.exe manage.py check
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m ruff check .
```

## Nota sobre la base de datos local

El historial de migraciones arrastra un cambio de ubicación de modelos entre las apps `usuarios` y
`catalogo` (las tablas `catalogo`, `material_construccion`, `stock`, etc. se crean en `usuarios/0001`
y luego se vuelven a crear en `catalogo/0001`). Por eso, una base SQLite **creada desde cero** puede
detenerse en `table "catalogo" already exists`. Las bases que ya existen y la base remota compartida
funcionan con normalidad. Si necesitas una base local nueva, el instalador te indica la salida
(`--reset-db`) y el detalle está en el reporte de la revisión.
