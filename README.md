# Constru-trans 🏗️🚛

Sistema integral de gestión para transporte y materiales de construcción. Este proyecto permite administrar usuarios, inventarios, compras, transporte, órdenes de servicio, facturación y reportes.

## 🚀 Tecnologías Utilizadas

- **Backend:** Django (Python)
- **Base de Datos:** SQLite (Desarrollo)
- **Frontend:** HTML, CSS (Bootstrap), JavaScript
- **Reportes:** ReportLab (Generación de PDFs)

## ⚙️ Instalación Rápida (Recomendado)

Si estás configurando este proyecto en un nuevo computador con Windows, simplemente haz doble clic en el archivo:
- **`setup_project.bat`**

Este script automatizado se encargará de:
1. Crear el entorno virtual (`venv`).
2. Instalar todas las dependencias necesarias.
3. Configurar la base de datos y realizar las migraciones.
4. Cargar los datos iniciales (clientes, conductores, vehículos, etc.) desde `db_backup.json`.
5. Ofrecerte iniciar el servidor de desarrollo inmediatamente.

---

## 🛠️ Instalación Manual

Si prefieres hacerlo manualmente o estás en otro sistema operativo:

1. **Crear y activar el entorno virtual:**
   ```bash
   python -m venv venv
   # En Windows:
   venv\Scripts\activate
   # En Linux/Mac:
   source venv/bin/activate
   ```

2. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Realizar migraciones:**
   ```bash
   python manage.py migrate
   ```

4. **Cargar datos iniciales:**
   ```bash
   python manage.py loaddata db_backup.json
   ```

5. **Iniciar el servidor:**
   ```bash
   python manage.py runserver
   ```

---

## 🔐 Configuración de Variables de Envío (Correo)

El sistema envía notificaciones por correo. Debes configurar tu archivo `.env` (basado en `.env.example`):

- `EMAIL_HOST_USER`: Tu correo de Gmail.
- `EMAIL_HOST_PASSWORD`: Tu contraseña de aplicación de Google.

## 📁 Estructura del Proyecto

- `apps/`: Aplicaciones del sistema (usuarios, inventario, transporte, etc.).
- `core/`: Configuración principal de Django.
- `static/`: Archivos CSS, JS e Imágenes.
- `templates/`: Plantillas HTML globales.
- `db_backup.json`: Respaldo completo de la información actual.
