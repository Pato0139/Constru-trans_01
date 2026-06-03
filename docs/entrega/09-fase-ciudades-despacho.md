# Fase 7 — Destinos y ciudades de despacho

## Decisión de negocio adoptada

**Opción B:** despacho a varias ciudades concretas de Boyacá y zona de influencia.

## Ciudades autorizadas (configuración)

Definidas en `core/despacho.py`:

- Tunja  
- Duitama  
- Paipa  
- Sogamoso  
- Chiquinquirá  
- Villa de Leyva  
- Samacá  
- Nobsa  

Origen de bodega: **Bodega Central - Tunja** (referencia en constante `BODEGA_ORIGEN`).

## Implementación en el sistema

| Componente | Cambio |
|------------|--------|
| Formulario cliente | Selector `<select name="ciudad">` + campo `direccion_detalle` |
| Backend | `ciudad_valida()` antes de guardar pedido |
| Almacenamiento | `direccion_destino` = `"Ciudad — Calle..."` |
| Edición | `separar_direccion_destino()` recupera ciudad y detalle |

## Validación

- Si no se elige ciudad → mensaje: datos incompletos.
- Si ciudad no está en lista → mensaje: fuera de zona autorizada.

## Texto para el informe

«Se identificó que el sistema no definía el alcance geográfico de los despachos. Como mejora se implementó un selector de ciudades permitidas y validación en servidor, evitando direcciones libres sin control y mejorando la claridad para el usuario.»

## Prueba de usabilidad (observar)

- ¿El participante entiende que solo puede elegir ciudades de la lista?
- ¿Escribe la calle en el segundo campo sin confundirlo con la ciudad?
