# 🚛 CONSTRU-TRANS
### Sistema Integral de Gestión para Transporte y Materiales de Construcción
**Versión 1.0**

---

## ✅ Cumple 12 Criterios sin Excepciones

Este repositorio incluye **toda la documentación formal** requerida en la carpeta `docs/`.

---

## 🏗️ Arquitectura híbrida (offline-first)

- **BD local (SQLite):** `db.sqlite3` en cada PC. Funciona **offline**.
- **BD remota (Neon PostgreSQL):** centraliza usuarios, sesiones, clientes e historial entre todos los compañeros.
- Si no hay internet, todo cae a la BD local automáticamente (gracias al router `EnrutadorInventario`).

---

## 🚀 Setup en un nuevo computador

### Requisitos
- **Python 3.12** (versión unificada)
- Git
- Acceso al Bitwarden del equipo (para las credenciales)

### Pasos

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/Pato0139/Constru-trans_01.git
   cd Constru-trans_01
   ```

2. **Pedir al admin (vía Bitwarden) las credenciales reales:**
   - `SECRET_KEY`
   - `DATABASE_URL` (Neon) — opcional, solo si quieres sincronizar con la nube
   - `EMAIL_HOST_PASSWORD` (Gmail App Password)
   - `DJANGO_ENV=development`

3. **Ejecutar el setup:**
   - Windows: doble clic en `setup_project.bat`
   - Linux/Mac: `bash setup_project.sh`

La primera vez el script crea un archivo `.env` local usando `.env.example` y te pedirá completar las credenciales necesarias. Pega las credenciales reales en `.env` y vuelve a ejecutar el script si es necesario.

> Para desarrollo local, `DJANGO_ENV` debe ser `development`. En producción debe usarse `DJANGO_ENV=production` para activar los ajustes de seguridad.

¡Listo! El servidor arranca en http://127.0.0.1:8000

---

## 🔐 Recuperación de contraseña

En la pantalla de login → "¿Olvidaste tu contraseña?" → ingresa tu correo → revisa tu bandeja (también el spam) → haz clic en el enlace (válido 30 min) → ingresa nueva contraseña.

---

## 📦 Tecnologías

| Componente | Detalle |
|---|---|
| Backend | Django 5.1 + Python 3.12 |
| Base de datos local | SQLite 3.x (offline-first) |
| Base de datos remota | PostgreSQL 16 — Neon serverless |
| Frontend | Bootstrap 5 + Django Templates |
| Seguridad | Argon2, django-otp, validaciones en modelos/formularios |
| Reportes | ReportLab (PDF) + openpyxl (Excel) |
| IA | OpenAI API |
| Configuración | django-environ |
| Linting | Ruff |
| Pruebas | pytest + coverage |
| CI/CD | GitHub Actions |

---

## 🗂️ Estructura REAL (Actualizada — v1.0)

```
core/settings/         Configuración modular (base/dev/prod)
core/routers.py        Router de BD (decide local vs nube)
usuarios/              App: Usuarios, Conductores, Vehículos
clientes/              App: Clientes
inventario/            App: Materiales, Stock, Movimientos (Kardex)
compras/               App: Proveedores, Compras
gestion_pedidos/       App: Pedidos de clientes y DetallesPedido
ordenes/               App: Órdenes de entrega asignadas a conductores
facturacion/           App: Facturas
pagos/                 App: Pagos (con services y prototype)
reportes/              App: Reportes PDF/Excel
ia/                    App: Asistente IA (OpenAI + services + training)
inicio/                App: Página de inicio
historial/             App: Auditoría del sistema
licensing/             App: Licencias (middleware + services + tasks)
media/                 Archivos subidos (perfiles, etc.)
docs/                  Documentación formal
.github/workflows/     CI/CD Pipeline
```

---

## 📚 Documentación Formal

Ver la carpeta `docs/`:
- `docs/gestion/`: Cronograma sprints, historias de usuario, recursos, Git workflow
- `docs/arquitectura/`: Estructura modular, stack tecnológico justificado, MER, estrategia persistencia
- `docs/integracion/`: Endpoints frontend-backend, matriz de validaciones
- `docs/calidad/`: Estándares de codificación, dependencias, criterios de aceptación, plan de pruebas

---

## 🧪 Comandos útiles

```bash
python manage.py runserver       # Servidor desarrollo
python manage.py createsuperuser # Crear admin
python manage.py migrate         # Aplicar migraciones
python manage.py seed_mer        # Datos iniciales
python manage.py sincronizar     # Sincronizar local ↔ nube (si aplica)
pytest                           # Todos los tests
pytest --cov=usuarios --cov=clientes --cov=inventario \
       --cov=compras --cov=ordenes --cov=gestion_pedidos \
       --cov=facturacion --cov=pagos --cov=ia    # Tests + coverage completo
ruff check .                     # Linting
```

---

## 🔄 Workflow Git Oficial

- Rama principal: `main` (código estable)
- Rama de integración: `develop`
- Ramas de feature: `edward/*` o `feature/*`
- CI ejecuta en cualquier push y PR (main, develop, features)
- Antes de PR: `ruff check .` y `pytest` pasan sin errores
- Commits: `feat:`, `fix:`, `docs:`, `style:`, `refactor:`, `test:`, `chore:`

Ver `docs/gestion/04-git-workflow.md` para detalles.
