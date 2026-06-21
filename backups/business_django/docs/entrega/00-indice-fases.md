# Índice de fases — Entrega Constru-Trans

Estado de cada fase del plan del instructor.

| Fase | Tema | Estado | Entregable |
|------|------|--------|------------|
| **1** | Corregir repositorio Git | ✅ Hecho | `.gitignore`, migraciones/backups fuera de Git |
| **2** | Lista de tareas del sistema | ✅ Hecho | [01-lista-tareas-sistema.md](01-lista-tareas-sistema.md) |
| **3** | Preparar prueba de usabilidad | ✅ Hecho | [02-plantilla-prueba-usabilidad.md](02-plantilla-prueba-usabilidad.md) |
| **4** | Qué observar en la prueba | ✅ Hecho | Incluido en plantilla § «Registro por tarea» |
| **5** | Formato de registro | ✅ Hecho | Tablas en plantilla + [06-evidencia-calculos.md](06-evidencia-calculos.md) |
| **6** | Revisar cálculos del pedido | ✅ Hecho | Script `scripts/verificar_calculos_pedido.py` + doc 06 |
| **7** | Direcciones y ciudades | ✅ Hecho (código) | `core/despacho.py` + selector en formulario pedido |
| **8** | Diseño visual / contraste | ✅ Hecho (código) | `principal.css` acento naranja, botones visibles |
| **9** | Pruebas administrador | ✅ Protocolo | [07-protocolo-prueba-admin.md](07-protocolo-prueba-admin.md) |
| **10** | Clasificar errores | ✅ Hecho | Leyenda en [03-tabla-errores-mejoras.md](03-tabla-errores-mejoras.md) |
| **11** | Tabla final de hallazgos | ✅ Hecho | Mismo archivo 03 (actualizar tras prueba real) |
| **12** | Informe final | ✅ Hecho | [04-informe-final.md](04-informe-final.md) |

## Pendiente solo con tu equipo (no automatizable)

| Acción | Responsable |
|--------|-------------|
| Sesión de usabilidad con compañero **externo** al proyecto | Estudiante |
| Capturas / video en `evidencia/` | Estudiante |
| Completar filas vacías en tabla de errores (prueba real) | Estudiante |
| `git commit` y `git push` del repo corregido | Estudiante |

## Orden recomendado para cerrar la entrega

1. `python scripts/verificar_calculos_pedido.py`
2. `python manage.py runserver` → probar pedido con ciudad + materiales
3. Prueba cliente (30–45 min) con plantilla 02
4. Prueba admin (30–45 min) con protocolo 07
5. Copiar resultados a tabla 03 y sección 5.4 del informe 04
6. Commit y push
