# Estrategia de Persistencia - Hybrid Database

## Arquitectura real

Constru-Trans usa una estrategia **offline-first híbrida**:

- **`default`**: SQLite local
- **`remota`**: PostgreSQL/Neon cuando `DATABASE_URL` está disponible
- El router `EnrutadorInventario` decide en tiempo de ejecución dónde leer y escribir.

## Regla real del router

El archivo `core/routers.py` define `APPS_NUBE` así:

- `usuarios`
- `historial`
- `clientes`
- `ia`
- `ordenes`
- `transporte`
- `facturacion`
- `pagos`
- `reportes`
- `gestion_pedidos`
- `compras`

### Comportamiento

- Si la app pertenece a `APPS_NUBE` y la conexión remota está disponible, el router usa **`remota`**
- En cualquier otro caso usa **`default`**
- `inventario`, `inicio` y `licensing` permanecen siempre en `default`

## Tabla correcta

| App | Alias principal cuando hay conexión remota | Fallback |
|-----|--------------------------------------------|----------|
| usuarios | remota | default |
| historial | remota | default |
| clientes | remota | default |
| ia | remota | default |
| ordenes | remota | default |
| transporte | remota | default |
| facturacion | remota | default |
| pagos | remota | default |
| reportes | remota | default |
| gestion_pedidos | remota | default |
| compras | remota | default |
| inventario | default | default |
| inicio | default | default |
| licensing | default | default |

## Justificación

Esta estrategia permite:

1. Operación local incluso sin internet
2. Sincronización centralizada cuando la remota está disponible
3. Resiliencia ante caídas de red
4. Mejor trazabilidad entre datos operativos y administrativos

## Evidencia técnica

- `core/routers.py`
- `core/db_preference.py`
- `core/settings/base.py`
