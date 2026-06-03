# Informe final — Pruebas de usabilidad y evaluación del sistema Constru-Trans

**Proyecto:** Constru-Trans  
**Tecnología:** Django (Python), PostgreSQL/Neon, Bootstrap 5  
**Fecha del informe:** Junio 2026  
**Equipo / rama:** Edward_Fonseca  

---

## 1. Introducción

El presente informe documenta la evaluación del sistema **Constru-Trans**, plataforma web para gestión de pedidos de materiales de construcción, transporte y administración comercial. El trabajo responde a las indicaciones del instructor: organización del repositorio Git, identificación de tareas por rol, pruebas de usabilidad con usuarios externos al proyecto, registro de errores y propuesta de mejoras.

Constru-Trans atiende principalmente a **clientes** (solicitud y seguimiento de pedidos) y **administradores** (inventario, compras, pedidos, facturación, flota y reportes), con un rol adicional de **conductor** para entregas.

---

## 2. Objetivos

### Objetivo general

Evaluar la facilidad de uso, el funcionamiento y la claridad de la interfaz de Constru-Trans mediante pruebas con usuarios externos, con el fin de detectar errores y proponer mejoras accionables.

### Objetivos específicos

1. Identificar las tareas principales del sistema para los roles cliente y administrador.
2. Detectar errores funcionales durante la ejecución de tareas reales (incluidos cálculos de pedidos).
3. Analizar problemas de usabilidad, validación de datos y diseño visual.
4. Revisar el alcance geográfico de despachos (ciudades/destinos).
5. Proponer mejoras técnicas y de experiencia de usuario.
6. Corregir la configuración del repositorio según lineamientos del instructor.

---

## 3. Metodología

### 3.1 Revisión del repositorio

- Actualización de `.gitignore` para excluir migraciones Django (`**/migrations/` excepto `__init__.py`), backups JSON, entornos y artefactos locales.
- Eliminación del índice Git de archivos ya subidos (`git rm -r --cached`) sin borrar copias locales.
- Revisión de ramas `main`, `Revision-Instructor` y `Edward_Fonseca`.

### 3.2 Análisis del sistema

- Recorrido de rutas (`urls.py` por aplicación), vistas y plantillas.
- Revisión del modelo de pedidos (`Pedido`, `DetallePedido`) y script de totales en formulario de cliente.

### 3.3 Prueba de usabilidad (protocolo)

- **Participante:** compañero externo al desarrollo del proyecto (completar nombre en plantilla).
- **Facilitador:** observador sin dar indicaciones de navegación.
- **Instrucción:** una tarea por enunciado («Solicita un pedido», «Consulta tus pedidos», etc.).
- **Registro:** tiempo, éxito/fallo, confusiones, errores funcionales, comentarios espontáneos.
- **Instrumento:** `02-plantilla-prueba-usabilidad.md`.
- **Evidencia:** capturas o video en `docs/entrega/evidencia/`.

> **Nota para el equipo:** Este informe incluye hallazgos de revisión de código. Debes **completar la sección de resultados** tras ejecutar al menos una sesión con usuario externo y adjuntar evidencia.

---

## 4. Tareas evaluadas

| Rol | Tareas evaluadas (mínimo) |
|-----|---------------------------|
| Cliente | Inicio de sesión, solicitud de pedido, consulta y seguimiento de pedidos, edición de pedido pendiente |
| Administrador | Inicio de sesión, creación de material, consulta de pedidos, asignación de entrega, consulta de reportes |

Listado completo: ver `01-lista-tareas-sistema.md`.

---

## 5. Resultados obtenidos

### 5.1 Repositorio

| Aspecto | Estado |
|---------|--------|
| `.gitignore` con `.env`, `venv`, SQLite, migraciones, backups | Corregido |
| Migraciones fuera del control de versiones | Corregido (archivos locales conservados) |
| Backups JSON en `backups/` | Retirados del repositorio |

Tras clonar el proyecto, cada desarrollador debe ejecutar:

```bash
python manage.py makemigrations
python manage.py migrate
```

### 5.2 Revisión de commits relevantes (rama principal / instructor)

| Commit | Cambio observado | Impacto |
|--------|------------------|---------|
| `e4266db` | Arreglar relaciones y nombres de campos en pedidos | Corrige errores funcionales en módulo pedidos |
| `3ba7228` | Campos inventario/órdenes, middleware licencias, signals | Estabilidad de totales y licencias |
| `d7feede` | Reorganizar sidebar y estilos | Navegación admin |
| `3fbd2e6` | Diseño responsive | Usabilidad en móvil |
| `027ff55` | Errores estéticos en compras y proveedores | Mejora visual módulo compras |
| `b249ca4` | Errores de accesibilidad | Contraste y accesibilidad parcial |
| `d96f0b0` | Stock al agregar materiales, validación fechas | Menos errores en inventario y formularios |

La rama `Revision-Instructor` está alineada con los mismos commits base que `main` en el remoto analizado.

### 5.3 Hallazgos principales (tabla resumida)

Ver detalle en `03-tabla-errores-mejoras.md`. Resumen:

- **Destinos (Fase 7):** se implementó selector de ciudades autorizadas y validación en servidor (`core/despacho.py`).
- **Cálculos (Fase 6):** los tres casos del instructor (3×2850, 5×1000, 2×3499) coinciden con la lógica backend; script `verificar_calculos_pedido.py` documenta la evidencia.
- **Visual (Fase 8):** se corrigió acento naranja y visibilidad de botones secundarios en `principal.css`.
- **Admin (Fase 9):** protocolo de prueba en `07-protocolo-prueba-admin.md`; botón «Asignar Conductor» existe en detalle de pedido.

### 5.4 Resultados de prueba con usuario externo

_[Completar tras la sesión — copiar tablas desde `02-plantilla-prueba-usabilidad.md`]_

---

## 6. Mejoras propuestas

| # | Mejora | Tipo | Prioridad |
|---|--------|------|-----------|
| 1 | ~~Selector de ciudades~~ **Implementado** | Funcional + UX | — |
| 2 | ~~Contraste y acento~~ **Implementado** | Visual | — |
| 3 | Botón «Asignar entrega» visible en detalle de pedido admin | Usabilidad | Alta |
| 4 | Validación de stock y fecha en tiempo real en formulario de pedido | Validación | Media |
| 5 | Documentar en README política de migraciones locales | Proceso | Media |
| 6 | Segunda ronda de pruebas tras implementar mejoras altas | Metodología | Media |

---

## 7. Conclusiones

La evaluación de Constru-Trans combinó **auditoría técnica del código** y un **protocolo de usabilidad** alineado con las indicaciones del instructor. Se corrigió la organización del repositorio eliminando migraciones y backups del historial de Git, lo que reduce conflictos y cumple el lineamiento académico.

El sistema cubre un flujo de negocio amplio (pedidos, inventario, compras, facturación, transporte y reportes). Los principales puntos de mejora detectados en esta fase son la **definición explícita de zonas de despacho**, la **claridad visual en interfaz oscura** y la **simplificación del flujo administrativo de entregas**. La participación de usuarios externos es indispensable para validar hipótesis de usabilidad que el equipo desarrollador no percibe.

Se recomienda ejecutar las pruebas con al menos un participante por rol, registrar tiempos y evidencias, y priorizar las mejoras de prioridad alta antes de la entrega final al docente.

---

## Anexos

- `01-lista-tareas-sistema.md` — Inventario de tareas  
- `02-plantilla-prueba-usabilidad.md` — Protocolo y tablas de sesión  
- `03-tabla-errores-mejoras.md` — Hallazgos detallados  
- `05-revision-commits-instructor.md` — Notas de Git  
- `evidencia/` — Capturas y videos (crear carpeta al realizar pruebas)
