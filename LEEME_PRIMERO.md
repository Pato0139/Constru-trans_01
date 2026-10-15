# Constru-trans_01 — Arreglos (plantillas, migraciones, validaciones)

Este paquete NO reemplaza tu repo: son los cambios listos para aplicar, con los
comandos exactos. Trabaja en una RAMA nueva, nunca en `main`.

## Contenido
- `copiar_encima/`  -> archivos ya corregidos. Se copian sobre el repo respetando la ruta.
- `BORRAR_ESTOS_ARCHIVOS.txt` -> copias duplicadas de plantillas que hay que eliminar.
- `cambios_constru_trans.patch` -> TODO el cambio en un solo parche (`git apply`).
- `ARCHIVOS_CAMBIADOS.txt` -> resumen M/A/D.

## Opcion A (recomendada): aplicar el parche
    git clone https://github.com/Pato0139/Constru-trans_01.git
    cd Constru-trans_01
    git checkout main
    git pull --ff-only origin main
    git checkout -b fix/plantillas-migraciones-validaciones
    git apply --stat  /ruta/cambios_constru_trans.patch   # revisa que aplica limpio
    git apply         /ruta/cambios_constru_trans.patch
    python -m compileall -q apps config
    python manage.py check
    python manage.py makemigrations --check --dry-run     # no debe querer crear nada nuevo
    git add -A
    git commit -m "fix: plantillas unicas, migraciones historial/reporte y validacion de comprobante en servidor"
    git push -u origin fix/plantillas-migraciones-validaciones
    # Abrir Pull Request en GitHub y que lo revise otra persona NO Edward.

## Opcion B (manual, si el parche no aplica)
    git checkout -b fix/plantillas-migraciones-validaciones
    # 1) copiar archivos
    cp -r /ruta/copiar_encima/* .
    # 2) borrar duplicados (estan listados en BORRAR_ESTOS_ARCHIVOS.txt)
    git rm apps/pedidos/templates/pagos/*.html
    git rm config/templates/auditoria/lista.html config/templates/inicio/home.html config/templates/reportes/lista.html
    git rm templates/auditoria/lista.html templates/reportes/lista.html
    git add -A && git commit -m "fix: unificar plantillas, migraciones y validacion de comprobante"

## Reglas para que NO se vuelvan a perder cambios
1. NADIE empuja a `main`. `main` se actualiza solo por Pull Request.
2. Cada persona: rama propia con su nombre (`feat/tu-nombre-lo-que-haces`).
3. Antes de subir: `git pull --ff-only origin main`  y luego merge/rebase de main en tu rama.
4. PROHIBIDO `git push --force` y `git reset --hard` sobre una rama compartida.
   Si algo se rompio: `git revert <hash>` (crea commit que deshace) en vez de borrar historia.
5. Nunca `git checkout .` / `git clean -fd` con trabajo sin commitear.
6. Protege `main` en GitHub: Settings > Branches > Require pull request + Require approvals.

## Que se arreglo y por que (resumen)
1. `.gitignore` tenia marcadores de un merge sin resolver (`<<<<<<< HEAD`, `>>>>>>> origin/GRUPO_7_ADSO/FIX`).
2. Ocho plantillas existian DOS veces (una en la app correcta y otra en `templates/`, `config/templates/`
   o `apps/pedidos/templates/`). Django cargaba solo una segun el orden de `INSTALLED_APPS`, asi que los
   cambios de una persona no se veian: quedaban en la copia que nunca se renderiza.
3. `config/migrations/0002` y `0003` creaban `historial`, `reporte` y `historial_reporte`, que YA crean
   `apps/auditoria` y `apps/reportes` -> `manage.py migrate` moria con "relation already exists".
   Ahora esas migraciones estan neutralizadas (`operations = []`).
4. `apps/pagos/views.py` usaba `Factura`, `PagoFactura`, `render_factura_pdf`, `obtener_ip`,
   `registrar_warning`, `registrar_evento` y `_respuesta_no_autorizada` SIN importarlos -> NameError.
5. El comprobante de pago se validaba con el `accept` del navegador y con `content_type`, que el cliente
   puede falsear (justo el bypass que hicieron por Inspect). Ahora `apps/pedidos/validators.py` lee los
   BYTES reales (magic number), la extension y el tamano, en el servidor.
