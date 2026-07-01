# Stack Tecnológico - Justificación Técnica

## Versión de Python Unificada: **3.12**

| Componente | Versión | Justificación | Ventajas | Límites |
|------------|---------|---------------|----------|--------|
| **Python** | 3.12 | Compatibilidad con Django 5.1 + balance entre estabilidad y features modernas | Tipado mejorado, performance, soporte largo | - |
| **Django** | 5.1 | Framework web robusto, ORM potente, seguridad integrada | Admin automático, auth, migrations, escalable | Curva de aprendizaje inicial |
| **SQLite** | 3.x | Base de datos local para modo offline | Cero configuración, portátil, rápido para escritorio | No recomendado para alta concurrencia |
| **PostgreSQL (Neon)** | 16 | Base de datos remota para sincronización | ACID, escalable, soporte JSON, Neon serverless | Requiere conexión a internet |
| **django-environ** | Latest | Manejo seguro de variables de entorno | Separa config de código, .env fácil | - |
| **Bootstrap** | 5.x | Framework CSS para frontend responsive | Diseño profesional rápido, mobile-first | - |
| **ReportLab** | Latest | Generación de PDFs | Crea reportes profesionales | - |
| **openpyxl** | Latest | Manejo de archivos Excel | Exporta reportes a .xlsx | - |
| **OpenAI API** | Latest | Asistente inteligente | Respuestas contextualizadas, LLM potente | Requiere API Key y costos |
| **Ruff** | Latest | Linter y formatter Python | Velocidad 10-100x > flake8, reemplaza varios tools | - |
| **pytest** | Latest | Framework de pruebas | Sintaxis simple, plugins, coverage | - |
| **GitHub Actions** | - | CI/CD Pipeline | Integración nativa con GitHub, gratis | - |

---

## Entornos

| Entorno | BD | Debug | Seguridad |
|---------|----|-------|-----------|
| **Desarrollo** | SQLite local | True | Cors abierto, logs detallados |
| **Producción** | PostgreSQL Neon | False | SSL, secure cookies, HSTS |
