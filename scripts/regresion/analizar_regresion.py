#!/usr/bin/env python3
"""
analizar_regresion.py

Analiza si commits recientes pudieron romper tus casos de prueba (CP1-CP4),
cruzando:
  1) qué archivos tocaron los commits sospechosos
  2) el resultado real de correr `python manage.py test` sobre los módulos
     afectados
  3) detección específica del error típico de router/alias de BD en tests

Uso:
    python analizar_regresion.py

Requisitos: correr desde la raíz del repo (donde está manage.py), con git
disponible y el entorno virtual/dependencias ya activadas.
"""

import subprocess
import re
import sys
from pathlib import Path
from datetime import datetime

# ======================================================================
# CONFIG — AJUSTA ESTO A TU PROYECTO
# ======================================================================

# Commits que quieres auditar (los que mencionaste). Puedes poner más.
COMMITS_SOSPECHOSOS = ["4d6bfbb", "2531856"]

# Si prefieres comparar contra una rama/tag base en vez de listar commits
# sueltos, pon aquí el ref base (ej. "main", "origin/main") y déjalo en
# None si no lo vas a usar.
BASE_REF = None  # ej: "origin/main"

# Mapa de bloques de prueba -> (archivos clave que los afectan, labels de
# `manage.py test` a correr). Ajusta nombres de apps/tests a los tuyos.
CP_BLOQUES = {
    "CP1 - Inventario/Pedido/Pago": {
        "archivos_clave": [
            "inventario/", "pedidos/", "core/routers.py",
        ],
        "test_labels": ["inventario", "pedidos"],
    },
    "CP2 - Conductor": {
        "archivos_clave": [
            "usuarios/views.py", "usuarios/urls.py",
        ],
        "test_labels": ["usuarios"],
    },
    "CP3 - Inicio/Usuarios/Transporte": {
        "archivos_clave": [
            "usuarios/views.py", "transporte/views.py", "core/urls.py",
        ],
        "test_labels": ["usuarios", "transporte"],
    },
    "CP4 - Facturacion/Pagos": {
        "archivos_clave": [
            "facturacion/views.py",
        ],
        "test_labels": ["facturacion"],
    },
}

# Patrón del error típico de router/alias de BD no declarado en tests
PATRON_ERROR_ROUTER = re.compile(
    r"(database.*not.*configured.*test|"
    r"alias.*not.*declared|"
    r"DatabaseError.*alias|"
    r"allow_migrate|"
    r"databases\s*=\s*\[.*\].*not.*declared)",
    re.IGNORECASE,
)

MANAGE_PY = "manage.py"
PYTHON_BIN = sys.executable or "python"

# ======================================================================
# LÓGICA — normalmente no necesitas tocar de aquí para abajo
# ======================================================================

ROJO = "\033[91m"
AMARILLO = "\033[93m"
VERDE = "\033[92m"
GRIS = "\033[90m"
RESET = "\033[0m"
NEGRITA = "\033[1m"


def run(cmd, timeout=300):
    try:
        r = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -1, "", f"TIMEOUT tras {timeout}s ejecutando: {cmd}"


def check_repo():
    if not Path("manage.py").exists():
        print(f"{ROJO}✗ No encuentro manage.py en el directorio actual.{RESET}")
        print("  Corre este script desde la raíz del repo Django.")
        sys.exit(1)
    code, _, _ = run("git rev-parse --is-inside-work-tree")
    if code != 0:
        print(f"{ROJO}✗ Este directorio no parece un repo git.{RESET}")
        sys.exit(1)


def archivos_tocados_por_commits(commits):
    """Devuelve set de archivos tocados por la lista de commits."""
    tocados = set()
    for c in commits:
        code, out, err = run(f"git show --name-only --pretty=format: {c}")
        if code != 0:
            print(f"{AMARILLO}  ! No pude leer el commit {c}: {err.strip()}{RESET}")
            continue
        for line in out.splitlines():
            line = line.strip()
            if line:
                tocados.add(line)
    return tocados


def archivos_tocados_desde_base(base_ref):
    code, out, err = run(f"git diff --name-only {base_ref}...HEAD")
    if code != 0:
        print(f"{AMARILLO}  ! No pude diff contra {base_ref}: {err.strip()}{RESET}")
        return set()
    return {l.strip() for l in out.splitlines() if l.strip()}


def bloque_afectado(archivos_tocados, archivos_clave):
    afectados = []
    for tocado in archivos_tocados:
        for clave in archivos_clave:
            if tocado.startswith(clave) or clave in tocado:
                afectados.append(tocado)
                break
    return afectados


def correr_tests(labels):
    label_str = " ".join(labels)
    cmd = f"{PYTHON_BIN} {MANAGE_PY} test {label_str} -v 2"
    code, out, err = run(cmd, timeout=600)
    salida_completa = out + "\n" + err
    return code, salida_completa


def parsear_resultado_tests(salida):
    fallos = len(re.findall(r"^FAIL:", salida, re.MULTILINE))
    errores = len(re.findall(r"^ERROR:", salida, re.MULTILINE))
    m = re.search(r"Ran (\d+) tests?", salida)
    total = int(m.group(1)) if m else None
    error_router = bool(PATRON_ERROR_ROUTER.search(salida))

    # Extrae nombre del test + primera línea útil del traceback para cada
    # FAIL/ERROR, buscando el bloque entre "===...===" que Django imprime.
    detalles = []
    bloques = re.split(r"^={70}$", salida, flags=re.MULTILINE)
    for b in bloques:
        m2 = re.match(r"\s*(FAIL|ERROR):\s*(.+)", b.strip())
        if not m2:
            continue
        tipo, nombre_test = m2.group(1), m2.group(2).strip()
        # última línea no vacía del traceback suele ser la excepción real
        lineas = [l.strip() for l in b.strip().splitlines() if l.strip()]
        motivo = lineas[-1] if len(lineas) > 1 else "(sin detalle)"
        detalles.append((tipo, nombre_test, motivo))

    return {
        "total": total,
        "fallos": fallos,
        "errores": errores,
        "error_router": error_router,
        "detalles": detalles,
        "salida_completa": salida,
    }


def semaforo(afectados, resultado):
    """Determina rojo/amarillo/verde para un bloque CP."""
    if resultado is None:
        return AMARILLO, "INCONCLUSO (no se pudieron correr los tests)"
    if resultado["error_router"]:
        return ROJO, "ROJO — error de infraestructura (router/alias BD) bloquea las pruebas"
    if resultado["fallos"] > 0 or resultado["errores"] > 0:
        return ROJO, f"ROJO — {resultado['fallos']} fallos / {resultado['errores']} errores reales"
    if afectados:
        return AMARILLO, "AMARILLO — archivos clave tocados pero tests pasan (validar manualmente)"
    return VERDE, "VERDE — sin cambios en archivos clave y tests pasan"


def main():
    print(f"{NEGRITA}Analizando regresión por commits recientes...{RESET}\n")
    check_repo()

    if BASE_REF:
        print(f"Comparando contra base: {BASE_REF}")
        tocados = archivos_tocados_desde_base(BASE_REF)
    else:
        print(f"Commits a auditar: {', '.join(COMMITS_SOSPECHOSOS)}")
        tocados = archivos_tocados_por_commits(COMMITS_SOSPECHOSOS)

    if tocados:
        print(f"\n{NEGRITA}Archivos tocados:{RESET}")
        for f in sorted(tocados):
            print(f"  {GRIS}- {f}{RESET}")
    else:
        print(f"{AMARILLO}No se detectaron archivos tocados (revisa COMMITS_SOSPECHOSOS/BASE_REF).{RESET}")

    resumen = []

    for nombre_bloque, cfg in CP_BLOQUES.items():
        print(f"\n{NEGRITA}=== {nombre_bloque} ==={RESET}")
        afectados = bloque_afectado(tocados, cfg["archivos_clave"])
        if afectados:
            print(f"  Archivos clave afectados por los commits:")
            for a in afectados:
                print(f"    {GRIS}- {a}{RESET}")
        else:
            print(f"  {GRIS}Ningún archivo clave de este bloque fue tocado por los commits.{RESET}")

        print(f"  Corriendo: manage.py test {' '.join(cfg['test_labels'])} ...")
        code, salida = correr_tests(cfg["test_labels"])
        resultado = parsear_resultado_tests(salida)

        color, veredicto = semaforo(afectados, resultado)
        print(f"  {color}{NEGRITA}{veredicto}{RESET}")
        if resultado["total"] is not None:
            print(f"  Tests corridos: {resultado['total']} | fallos: {resultado['fallos']} | errores: {resultado['errores']}")
        if resultado["error_router"]:
            print(f"  {ROJO}→ Detectado patrón de error de router/alias de BD en tests.{RESET}")
            print(f"    Revisa DATABASE_ROUTERS / settings de test (TEST['MIGRATE'], alias declarado).")

        if resultado["detalles"]:
            print(f"  {NEGRITA}Detalle de fallos:{RESET}")
            for tipo, nombre_test, motivo in resultado["detalles"]:
                color_tipo = ROJO if tipo == "ERROR" else AMARILLO
                print(f"    {color_tipo}[{tipo}]{RESET} {nombre_test}")
                print(f"      {GRIS}{motivo}{RESET}")

        # Guarda log completo del bloque para inspección posterior
        log_dir = Path("regresion_logs")
        log_dir.mkdir(exist_ok=True)
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", nombre_bloque).strip("_").lower()
        log_path = log_dir / f"{slug}.log"
        log_path.write_text(resultado["salida_completa"], encoding="utf-8")
        print(f"  {GRIS}Log completo guardado en: {log_path}{RESET}")

        resumen.append((nombre_bloque, color, veredicto, resultado))

    # Resumen final
    print(f"\n{NEGRITA}{'='*60}{RESET}")
    print(f"{NEGRITA}RESUMEN FINAL — {datetime.now().strftime('%Y-%m-%d %H:%M')}{RESET}")
    print(f"{NEGRITA}{'='*60}{RESET}")
    for nombre_bloque, color, veredicto, resultado in resumen:
        print(f"{color}{nombre_bloque}: {veredicto}{RESET}")

    hay_rojo = any(c == ROJO for _, c, _, _ in resumen)
    if hay_rojo:
        print(f"\n{ROJO}{NEGRITA}Conclusión: SÍ hay evidencia real de regresión. No lo des por validado.{RESET}")
    else:
        print(f"\n{VERDE}{NEGRITA}Conclusión: no se encontró evidencia directa de rotura, pero valida manualmente los bloques en amarillo.{RESET}")

    # Lista consolidada de todos los tests que fallaron, para copiar/pegar
    total_fallos = sum(len(r["detalles"]) for _, _, _, r in resumen)
    if total_fallos:
        print(f"\n{NEGRITA}Todos los tests con fallo ({total_fallos}):{RESET}")
        for nombre_bloque, _, _, resultado in resumen:
            for tipo, nombre_test, motivo in resultado["detalles"]:
                print(f"  [{nombre_bloque}] {nombre_test} -> {motivo}")
        print(f"\n{GRIS}Logs completos en la carpeta ./regresion_logs/{RESET}")


if __name__ == "__main__":
    main()