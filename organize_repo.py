#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
organize_repo.py
================

Organizador idempotente del repositorio: elimina archivos huérfanos de la
raíz, mueve artefactos a su directorio correcto y borra directorios legacy,
sin tocar rutas protegidas. Por defecto solo INFORMA (dry-run); los cambios
se aplican con --apply.

Ejemplos
--------
    python organize_repo.py                              # dry-run (no toca nada)
    python organize_repo.py --apply                      # aplica los cambios
    python organize_repo.py --apply --commit             # aplica + commit automático
    python organize_repo.py --apply --commit --push      # aplica + commit + push
    python organize_repo.py --rollback --report organize_report_<ts>.json
    python organize_repo.py --apply --allow-dirty        # ignora cambios sin commitear

Salidas
-------
    organize_plan.json           mapa completo de movimientos (siempre)
    organize_report_<ts>.json    acciones ejecutadas / propuestas / omitidas

Garantías
---------
    * Rutas protegidas nunca se tocan ni borran.
    * Usa `git mv` cuando el archivo está trackeado (preserva historial).
    * Idempotente: correrlo dos veces no rompe nada ni duplica .gitignore.
    * Safe-stop: aborta si hay cambios sin commitear (salvo --allow-dirty).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

DEFAULT_COMMIT_MSG = "chore: limpiar archivos huérfanos y reorganizar documentación"

# --------------------------------------------------------------------------
# Configuración del repo (resultado de la auditoría previa)
# --------------------------------------------------------------------------

FILES_TO_DELETE = [
    "CAMBIOS_NORMALIZACION_BD.md",
    "CHECKLIST_IMPLEMENTACION.md",
    "GUIA_TRANSACCIONES_ATOMICIDAD.md",
    "INDICE_DOCUMENTACION.md",
    "RESUMEN_VISUAL_NORMALIZACION.md",
    "MER.drawio 3.drawio (1).pdf",
    "agregar_metodos_pago.py",
    "check_db.py",
    "check_settings.py",
    "reporte_rubrica.html",
    "reporte_rubrica.pdf",
    "script_verificaccion_LC3.py",
    "scratch_pagos_diff.txt",
    "push_to_github.ps1",
    "tablas_default.txt",
]

MOVES = [
    ("fix_neon_columnas_faltantes.sql", "docs/sql-migration-notes/fix_neon_columnas_faltantes.sql"),
    ("fix_neon_tables.sql",              "docs/sql-migration-notes/fix_neon_tables.sql"),
    ("sqlmigrate_ayuda.sql",             "docs/sql-migration-notes/sqlmigrate_ayuda.sql"),
    ("sql_compras_0005.txt",             "docs/sql-migration-notes/sql_compras_0005.txt"),
    ("sql_gestion_pedidos_0001.txt",     "docs/sql-migration-notes/sql_gestion_pedidos_0001.txt"),
    ("sql_historial_0001.txt",           "docs/sql-migration-notes/sql_historial_0001.txt"),
    ("sql_historial_0002.txt",           "docs/sql-migration-notes/sql_historial_0002.txt"),
    ("sql_historial_0003.txt",           "docs/sql-migration-notes/sql_historial_0003.txt"),
    ("sql_inventario_0003.txt",          "docs/sql-migration-notes/sql_inventario_0003.txt"),
    ("sql_reportes_0001.txt",            "docs/sql-migration-notes/sql_reportes_0001.txt"),
    ("sql_reportes_0002.txt",            "docs/sql-migration-notes/sql_reportes_0002.txt"),
    ("sql_usuarios_0001.txt",            "docs/sql-migration-notes/sql_usuarios_0001.txt"),
    ("sql_usuarios_0007.txt",            "docs/sql-migration-notes/sql_usuarios_0007.txt"),
    ("MIGRACIONES_FINALES_3FN.md",       "docs/rubrica/MIGRACIONES_FINALES_3FN.md"),
    ("analizar_regresion.py",            "scripts/regresion/analizar_regresion.py"),
]

DIRS_TO_DELETE = ["cache"]

GITIGNORE_ADDITIONS = [
    "cache/",
    "*.djcache",
]

# Artefactos que genera este script: el safe-stop no debe considerarles
# "cambios sin commitear" (si no, dry-run bloquearía el apply posterior).
SCRIPT_ARTIFACTS_PREFIXES = ("organize_report_", "neon_report")
SCRIPT_ARTIFACTS_EXACT = {"organize_plan.json"}

# Rutas que el script jamás toca ni borra.
PROTECTED_EXACT = {"manage.py", "requirements.txt", "Dockerfile", "docker-compose.yml", "core/wsgi.py", ".env"}
PROTECTED_PREFIXES = (
    "core/settings/", "docs/", "scripts/", "static/", "templates/",
    ".github/", "migrations/", "alembic/", "apps/", "ai_platform/",
)
PROTECTED_ANY_PART = {"docs", "scripts", "static", "templates", ".github", "migrations", "alembic"}


def is_protected(rel: str) -> bool:
    """True si la ruta está en la lista de protección (nunca tocar)."""
    rel = rel.strip("/")
    if rel in PROTECTED_EXACT:
        return True
    if any(rel.startswith(p) for p in PROTECTED_PREFIXES):
        return True
    parts = rel.split("/")
    return any(p in PROTECTED_ANY_PART for p in parts[:-1])


# --------------------------------------------------------------------------
# Helpers de git
# --------------------------------------------------------------------------

def git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    cmd = ["git", "-C", str(root)] + list(args)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} falló: {r.stderr.strip()}")
    return r


def is_tracked(root: Path, rel: str) -> bool:
    r = git(root, "ls-files", "--error-unmatch", "--", rel, check=False)
    return r.returncode == 0


def has_uncommitted_changes(root: Path) -> bool:
    """True si hay cambios sin commitear, ignorando los artefactos propios."""
    r = git(root, "status", "--porcelain", check=False)
    for line in r.stdout.splitlines():
        path = line.strip()[3:].strip('"')
        if path in SCRIPT_ARTIFACTS_EXACT:
            continue
        if any(path.startswith(p) for p in SCRIPT_ARTIFACTS_PREFIXES):
            continue
        return True
    return False


# --------------------------------------------------------------------------
# Planificador
# --------------------------------------------------------------------------

def build_plan() -> list[dict]:
    actions: list[dict] = []
    for f in FILES_TO_DELETE:
        actions.append({"action": "delete", "kind": "file", "src": f, "dst": None})
    for src, dst in MOVES:
        actions.append({"action": "move", "kind": "file", "src": src, "dst": dst})
    for d in DIRS_TO_DELETE:
        actions.append({"action": "delete", "kind": "dir", "src": d, "dst": None})
    actions.append({"action": "gitignore", "kind": "meta", "src": ".gitignore", "dst": None})
    return actions


def propose(entry: dict, root: Path) -> dict:
    """Rellena el estado de una acción sin ejecutar nada."""
    src, dst, kind = entry["src"], entry.get("dst"), entry["kind"]
    row = {"action": entry["action"], "kind": kind, "src": src, "dst": dst,
           "state": "proposed", "message": ""}

    if is_protected(src):
        row["state"] = "error"
        row["message"] = f"ruta protegida, no se toca: {src}"
        return row

    p = root / src
    if row["action"] == "delete":
        if not p.exists() and not p.is_symlink():
            row["state"] = "skipped"
            row["message"] = "no existe (ya estaba limpio)"
        else:
            row["message"] = "git rm -f" if is_tracked(root, src) else "rm (untracked)"
    elif row["action"] == "move":
        if not p.exists() and not p.is_symlink():
            row["state"] = "skipped"
            row["message"] = "no existe (origen ausente)"
        elif (root / dst).exists():
            row["state"] = "skipped"
            row["message"] = "el destino ya existe, no se pisa"
        else:
            row["message"] = "git mv" if is_tracked(root, src) else "mover (untracked)"
    elif row["action"] == "gitignore":
        gi = root / ".gitignore"
        existing = gi.read_text(encoding="utf-8", errors="ignore").splitlines() if gi.exists() else []
        missing = [ln for ln in GITIGNORE_ADDITIONS if ln not in existing]
        if not missing:
            row["state"] = "skipped"
            row["message"] = "entradas ya presentes en .gitignore"
        else:
            row["message"] = "añadir: " + ", ".join(missing)
    return row


def execute(row: dict, root: Path) -> None:
    """Ejecuta la acción y actualiza la fila."""
    src, dst = row["src"], row.get("dst")
    p = root / src

    if row["action"] == "delete":
        if is_tracked(root, src):
            # -r necesario para directorios no vacíos (apps/, ai_platform/, cache/)
            git(root, "rm", "-r", "-f", "--quiet", "--", src)
        else:
            if p.is_dir() and not p.is_symlink():
                shutil.rmtree(p)
            elif p.exists() or p.is_symlink():
                p.unlink()
        row["message"] = "borrado"
    elif row["action"] == "move":
        (root / dst).parent.mkdir(parents=True, exist_ok=True)
        if is_tracked(root, src):
            git(root, "mv", src, dst)
        else:
            shutil.move(str(p), str(root / dst))
        row["message"] = "movido"
    elif row["action"] == "gitignore":
        gi = root / ".gitignore"
        existing = gi.read_text(encoding="utf-8", errors="ignore").splitlines() if gi.exists() else []
        lines = []
        for ln in GITIGNORE_ADDITIONS:
            if ln not in existing:
                lines.append(ln)
        if lines:
            with gi.open("a", encoding="utf-8") as fh:
                if existing and existing[-1] != "":
                    fh.write("\n")
                fh.write("\n".join(lines) + "\n")
        row["message"] = f"gitignore actualizado: {', '.join(lines)}"
    row["state"] = "applied"


def rollback_entry(entry: dict, root: Path) -> dict:
    """Revierte una acción previamente aplicada."""
    src, dst, kind = entry["src"], entry.get("dst"), entry["kind"]
    row = {"action": entry["action"], "kind": kind, "src": src, "dst": dst,
           "state": "rolled_back", "message": ""}
    if entry.get("state") != "applied":
        row["state"] = "skipped"
        row["message"] = "no estaba aplicada, nada que revertir"
        return row

    try:
        if entry["action"] == "delete":
            git(root, "restore", "--source=HEAD", "--staged", "--worktree", "--", src, check=False)
            if not (root / src).exists():
                git(root, "checkout", "HEAD", "--", src, check=False)
            row["message"] = "restaurado (si estaba en HEAD); si era untracked, no se puede recuperar"
        elif entry["action"] == "move":
            if (root / dst).exists() and not (root / src).exists():
                if is_tracked(root, dst):
                    git(root, "mv", dst, src)
                else:
                    shutil.move(str(root / dst), str(root / src))
            row["message"] = "movido de vuelta a " + src
        elif entry["action"] == "gitignore":
            gi = root / ".gitignore"
            if gi.exists():
                lines = gi.read_text(encoding="utf-8").splitlines()
                cleaned = [ln for ln in lines if ln not in GITIGNORE_ADDITIONS]
                gi.write_text("\n".join(cleaned).rstrip() + "\n", encoding="utf-8")
            row["message"] = "entradas de .gitignore eliminadas"
    except Exception as exc:  # noqa: BLE001
        row["state"] = "error"
        row["message"] = f"rollback falló: {exc}"
    return row


# --------------------------------------------------------------------------
# I/O y reportes
# --------------------------------------------------------------------------

def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def print_table(rows: list[dict]) -> None:
    if not rows:
        return
    width = max(len(r["src"]) for r in rows) + 2
    for r in rows:
        icon = {"proposed": "·", "applied": "✓", "skipped": "–", "error": "✗",
                "rolled_back": "↩"}.get(r["state"], "?")
        dst = f" → {r['dst']}" if r.get("dst") else ""
        print(f"  {icon} {r['src']:<{width}}{dst}  [{r['state']}] {r['message']}")


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Organizador idempotente del repositorio")
    ap.add_argument("--root", default=".", help="Raíz del repo (por defecto: cwd)")
    ap.add_argument("--report-dir", default=None,
                    help="Directorio para los reportes JSON (por defecto: /tmp si existe)")
    ap.add_argument("--apply", action="store_true", help="Aplica los cambios (defecto: dry-run)")
    ap.add_argument("--commit", action="store_true", help="Commit automático tras aplicar")
    ap.add_argument("--push", action="store_true", help="Push al remoto (requiere --commit)")
    ap.add_argument("--commit-msg", default=DEFAULT_COMMIT_MSG, help="Mensaje de commit")
    ap.add_argument("--rollback", action="store_true", help="Revierte un informe previo")
    ap.add_argument("--report", help="Ruta del informe JSON a revertir (con --rollback)")
    ap.add_argument("--allow-dirty", action="store_true", help="No abortar con cambios sin commitear")
    args = ap.parse_args(argv)

    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        print(f"✗ La raíz no existe: {root}")
        return 1

    if not args.rollback:
        r = git(root, "rev-parse", "--is-inside-work-tree", check=False)
        if r.returncode != 0:
            print(f"✗ {root} no es un repositorio git")
            return 1

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_dir = (Path(args.report_dir) if args.report_dir
                  else (Path("/tmp") if Path("/tmp").exists() else root))

    if args.rollback:
        if not args.report:
            print("✗ --rollback requiere --report <archivo.json>")
            return 1
        report_path = Path(args.report)
        if not report_path.exists():
            print(f"✗ Informe no encontrado: {report_path}")
            return 1
        report = json.loads(report_path.read_text(encoding="utf-8"))
        rows = [rollback_entry(e, root) for e in report.get("actions", [])]
        print("↩  Rollback de", report_path.name)
        print_table(rows)
        rolled = [r for r in rows if r["state"] == "rolled_back"]
        errors = [r for r in rows if r["state"] == "error"]
        print(f"\nResumen: {len(rolled)} revertidas, {len(errors)} errores")
        return 0 if not errors else 2

    print("🧭  Modo:", "APPLY (modifica el repo)" if args.apply else "DRY-RUN (no se modifica nada)")

    if args.apply and not args.allow_dirty and has_uncommitted_changes(root):
        print("✗ Hay cambios sin commitear. Haz commit o usa --allow-dirty.")
        return 2

    # Plan JSON: mapa de movimientos (independiente del estado del repo)
    plan_payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "files_to_delete": FILES_TO_DELETE,
        "moves": [{"from": s, "to": d} for s, d in MOVES],
        "dirs_to_delete": DIRS_TO_DELETE,
        "gitignore_additions": GITIGNORE_ADDITIONS,
        "protected": sorted(PROTECTED_EXACT | set(PROTECTED_PREFIXES)),
    }
    save_json(root / "organize_plan.json", plan_payload)

    actions = build_plan()
    rows = [propose(a, root) for a in actions]

    if args.apply:
        for row in rows:
            if row["state"] == "proposed":
                try:
                    execute(row, root)
                except Exception as exc:  # noqa: BLE001
                    row["state"] = "error"
                    row["message"] = f"falló: {exc}"

        if args.commit:
            git(root, "add", "-A")
            git(root, "commit", "-m", args.commit_msg)
            print("✔  Commit creado:", args.commit_msg)
        if args.push:
            if not args.commit:
                print("⚠  --push requiere --commit; saltando push")
            else:
                git(root, "push", "origin", "HEAD")
                print("✔  Push a origin/HEAD completado")
    else:
        print("\nPlan propuesto (--apply para ejecutar):\n")

    print_table(rows)
    n_proposed = sum(1 for r in rows if r["state"] == "proposed")
    n_skipped = sum(1 for r in rows if r["state"] == "skipped")
    n_applied = sum(1 for r in rows if r["state"] == "applied")
    n_errors = sum(1 for r in rows if r["state"] == "error")

    report_path = report_dir / f"organize_report_{ts}.json"
    save_json(report_path, {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "mode": "apply" if args.apply else "dry-run",
        "actions": rows,
        "summary": {"applied": n_applied, "proposed": n_proposed,
                    "skipped": n_skipped, "errors": n_errors},
    })

    print(f"\n📄 Reporte: {report_path}")
    print(f"📄 Plan:    {root / 'organize_plan.json'}")
    print(f"Resumen: {n_applied} aplicadas · {n_proposed} propuestas · "
          f"{n_skipped} omitidas · {n_errors} errores")
    if n_errors:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
