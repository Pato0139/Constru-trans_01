# Entrega — Usabilidad y evaluación Constru-Trans

## Los 5 productos solicitados

| # | Producto | Archivo |
|---|----------|---------|
| 1 | Repositorio corregido | `.gitignore` + cambios staged (migraciones/backups fuera de Git) |
| 2 | Lista de tareas del sistema | [01-lista-tareas-sistema.md](01-lista-tareas-sistema.md) |
| 3 | Evidencia de pruebas de usabilidad | [02-plantilla-prueba-usabilidad.md](02-plantilla-prueba-usabilidad.md) + carpeta [evidencia/](evidencia/) |
| 4 | Tabla de errores y mejoras | [03-tabla-errores-mejoras.md](03-tabla-errores-mejoras.md) |
| 5 | Informe final | [04-informe-final.md](04-informe-final.md) |

**Índice de todas las fases:** [00-indice-fases.md](00-indice-fases.md)

| Fase | Documento |
|------|-----------|
| 6 Cálculos | [06-evidencia-calculos.md](06-evidencia-calculos.md) |
| 7 Ciudades | [09-fase-ciudades-despacho.md](09-fase-ciudades-despacho.md) |
| 8 Diseño visual | [08-auditoria-diseno-visual.md](08-auditoria-diseno-visual.md) |
| 9 Admin | [07-protocolo-prueba-admin.md](07-protocolo-prueba-admin.md) |

Extra: [05-revision-commits-instructor.md](05-revision-commits-instructor.md)

## Qué debes hacer tú (obligatorio académico)

1. **Prueba con compañero externo** — Usa la plantilla `02`; no le expliques el sistema.
2. **Llenar filas 11+** en `03-tabla-errores-mejoras.md` con observaciones reales.
3. **Completar sección 5.4** del informe final con tiempos y capturas en `evidencia/`.
4. **Commit y push** del repositorio corregido:

```powershell
cd "c:\Users\edwar\Downloads\c\Constru-trans_01"
git add .gitignore docs/entrega/
git add -f apps/*/migrations/__init__.py
git status
git commit -m "Corrige .gitignore, documenta entrega de usabilidad y retira migraciones del repo"
git push origin Edward_Fonseca
```

## Migraciones en clones nuevos

Las migraciones ya no están en Git. En cada máquina:

```bash
python manage.py makemigrations
python manage.py migrate
```
