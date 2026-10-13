# Constru-trans

Sistema de gestión de materiales de construcción desarrollado con Django.

## Requisitos

- Python 3.11 o superior (se recomienda Python 3.12)
- Conexión a Internet durante la instalación para descargar las dependencias

El setup reutiliza un entorno virtual existente del proyecto (incluido el que ya
esté activado) o crea `.venv` si hace falta. Instala `requirements.txt`, crea
`.env` con una clave local solo si no existe y prepara la base de datos SQLite.
Conserva tanto el entorno como el `.env` existentes. Las migraciones del setup
no se ejecutan contra una base de datos remota.

## Instalación automática

### Windows (PowerShell)

Desde la carpeta del proyecto:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\setup\setup_windows.ps1
```

También puedes ejecutar `setup\setup_project.bat` desde el Explorador o CMD.

### macOS y Linux

Desde la carpeta del proyecto:

```bash
bash setup/setup_macos_linux.sh
```

El equipo debe tener Python 3.11 o superior instalado. El instalador descarga
los paquetes Python declarados en `requirements.txt`; no instala Python ni
servicios externos del sistema operativo.

## Iniciar el servidor

En Windows:

```powershell
python manage.py runserver
```

En macOS/Linux:

```bash
.venv/bin/python manage.py runserver
```

Abre <http://127.0.0.1:8000/> en el navegador. Si no activaste el entorno,
usa la ruta al Python del entorno que muestra el instalador al terminar.

La clave `SECRET_KEY` de `.env` debe ser fija: no la regeneres cada vez que
reinicies `runserver`, porque eso invalida las sesiones activas. En desarrollo,
Django guarda las sesiones en la base de datos y las mantiene hasta 14 días,
renovando su expiración mientras se usa la aplicación.

## Clima en el panel del conductor

El panel consulta el pronóstico de OpenWeather para la ciudad de la próxima
entrega asignada y su hora programada. Para habilitarlo, crea una API key en
[OpenWeather](https://openweathermap.org/api) y agrega esta variable al archivo
`.env` del proyecto:

```env
OPENWEATHER_API_KEY=tu_api_key
```

Reinicia el servidor después de guardar la variable. El pronóstico de 5 días se
actualiza en caché cada 10 minutos. El panel muestra un gráfico de lluvia,
temperatura y viento para los horarios diurnos disponibles, además de sugerir
la hora con menor lluvia y viento previstos. Sin una API key, o si OpenWeather
no está disponible, el panel informa el motivo y las demás funciones siguen
operando.

## Correo para recuperar contraseña

Por defecto, las solicitudes de recuperación usan el backend de correo
configurado en Django (`EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_HOST_USER` y demás
variables `EMAIL_*` de `.env`). Para Gmail, configura SMTP con una contraseña de
aplicación de Google.

También puedes usar la API de [Resend](https://resend.com/) como alternativa.
En ese caso, agrega y verifica un dominio propio en Resend y configura en `.env`
la API key y un remitente de ese dominio:

```env
RESEND_API_KEY=re_tu_api_key
RESEND_FROM_EMAIL=Constru-Trans <no-reply@correo.tudominio.com>
```

Reinicia Django después de guardar la configuración. Si no completas las dos
variables `RESEND_*`, la recuperación usa el backend de correo normal de Django.
Resend no envía desde un remitente arbitrario: el dominio debe estar verificado
antes de que acepte mensajes. Un envío aceptado por la API confirma que Resend
recibió la solicitud, no que el mensaje llegó a Recibidos; consulta el registro
de Emails en Resend para ver rebotes, rechazos o problemas de entrega.

## Desarrollo y pruebas

Después de completar la instalación automática, instala las herramientas de
desarrollo y ejecuta las comprobaciones:

En Windows:

```powershell
python -m pip install -r requirements/dev.txt
python manage.py check
python -m pytest
```

En macOS/Linux:

```bash
.venv/bin/python -m pip install -r requirements/dev.txt
.venv/bin/python manage.py check
.venv/bin/python -m pytest
```
