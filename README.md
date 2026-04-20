# Constru-trans 🏗️🚛

Sistema integral de gestión para transporte y materiales de construcción. Este proyecto permite administrar usuarios, inventarios, compras, transporte, órdenes de servicio, facturación y reportes.

## 🚀 Tecnologías Utilizadas

- **Backend:** Django (Python)
- **Base de Datos:** SQLite (Desarrollo)
- **Frontend:** HTML, CSS (Bootstrap), JavaScript
- **Reportes:** ReportLab (Generación de PDFs)
- **Gestión de Entorno:** python-dotenv, venv

## ⚙️ Instalación

Sigue estos pasos para configurar el proyecto localmente:

1. **Clonar el repositorio:**
   ```bash
   git clone <url-del-repositorio>
   cd Constru-trans_01
   ```

2. **Crear y activar el entorno virtual:**
   ```powershell
   # En Windows
   python -m venv .venv
   .\.venv\Scripts\activate
   ```

3. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar variables de entorno:**
   Copia el archivo `.env.example` a `.env` y ajusta los valores necesarios.
   ```bash
   cp .env.example .env
   ```

5. **Realizar migraciones:**
   ```bash
   python manage.py migrate
   ```

## 🔐 Configuración de Variables de Entorno

El proyecto utiliza un archivo `.env` para manejar información sensible. Asegúrate de configurar las siguientes variables:

- `SECRET_KEY`: Tu clave secreta de Django.
- `DEBUG`: `True` para desarrollo, `False` para producción.
- `EMAIL_HOST_USER`: Tu correo de Gmail para envío de notificaciones.
- `EMAIL_HOST_PASSWORD`: Contraseña de aplicación de Google.

## 🛠️ Ejecución del Proyecto

Para iniciar el servidor de desarrollo:
```bash
python manage.py runserver
```
El sistema estará disponible en `http://127.0.0.1:8000/`.

## ✅ Ejecución de Tests

Para correr las pruebas unitarias:
```bash
python manage.py test apps.usuarios.tests
```

## 📁 Estructura del Proyecto

- `apps/`: Contiene todas las aplicaciones del sistema (usuarios, inventario, compras, historial, etc.).
- `core/`: Configuración principal del proyecto Django.
- `static/`: Archivos estáticos (CSS, JS, Imágenes).
- `templates/`: Plantillas HTML base.
