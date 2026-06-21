# Constru-Trans

Sistema integral de gestión para transporte y materiales de construcción para una ferreteria

## 🏗️ Arquitectura híbrida (offline-first)

- **BD local (SQLite):** `db.sqlite3` en cada PC. Funciona **offline**.
- **BD remota (Neon PostgreSQL):** centraliza usuarios, sesiones, clientes e historial entre todos los compañeros.
- Si no hay internet, todo cae a la BD local automáticamente (gracias al router `EnrutadorInventario`).

## 🚀 Setup en un nuevo computador

### Requisitos
- Python 3.11 o superior
- Git
- Acceso al Bitwarden del equipo (para las credenciales)

### Pasos

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/Pato0139/Constru-trans_01.git
   cd Constru-trans_01
   ```

2. **Pedir al admin (vía Bitwarden) las credenciales reales:**
   - SECRET_KEY
   - DATABASE_URL (Neon) — opcional, solo si quieres sincronizar con la nube
   - EMAIL_HOST_PASSWORD (Gmail App Password)
   - DJANGO_ENV=development

3. **Ejecutar el setup:**
   - Windows: doble clic en `setup_project.bat`
   - Linux/Mac: `bash setup_project.sh`

La primera vez el script crea un archivo `.env` local usando `.env.example` y te pedirá completar las credenciales necesarias.
Pega las credenciales reales en `.env` y vuelve a ejecutar el script si es necesario.

> Para desarrollo local, `DJANGO_ENV` debe ser `development`.
> En producción debe usarse `DJANGO_ENV=production` para activar los ajustes de seguridad.

¡Listo! El servidor arranca en http://127.0.0.1:8000.

## 🔐 Recuperación de contraseña
En la pantalla de login → "¿Olvidaste tu contraseña?" → ingresa tu correo → revisa tu bandeja (también el spam) → haz clic en el enlace (válido 30 min) → ingresa nueva contraseña.

## 📦 Tecnologías
- Backend: Django 5.1 + SQLite local + PostgreSQL Neon
- Frontend: Bootstrap + Django Templates
- Seguridad: Argon2, django-axes, django-otp
- Reportes: ReportLab, openpyxl
- Configuración: django-environ

## 🗂️ Estructura
```
core/settings/         Configuración modular (base/dev/prod)
core/routers.py        Router de BD (decide local vs nube)
apps/                  Apps del sistema
templates/             HTML compartidos
templates/registration/   Templates de password reset
static/                CSS, JS, imágenes
media/                 Archivos subidos
```

## 🧪 Comandos útiles
```bash
python manage.py runserver       # Servidor desarrollo
python manage.py createsuperuser # Crear admin
python manage.py migrate         # Aplicar migraciones
python manage.py seed_mer        # Datos iniciales
python manage.py sincronizar     # Sincronizar local ↔ nube (si aplica)
pytest                           # Tests
ruff check .                     # Linting
```

## 🔄 Workflow del equipo
- Cada compañero clona el repo y configura su `.env`
- Trabaja localmente en SQLite (offline)
- Al estar online, el router sincroniza usuarios/sesiones/historial con Neon
- Las migraciones se versionan en git (NO ejecutar `makemigrations` en cada PC)
- Antes de hacer push, ejecutar `pytest` y `ruff check .`

