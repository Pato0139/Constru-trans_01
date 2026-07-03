# scripts/check_inline_styles.py
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
errores = []

for file in ROOT.rglob("*.html"):
    if ".git" in file.parts or "venv" in file.parts or "__pycache__" in file.parts:
        continue

    try:
        text = file.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue

    for num, line in enumerate(text.splitlines(), start=1):
        if 'style="' in line or "style='" in line:
            errores.append(f"{file.relative_to(ROOT)}:{num}")

if errores:
    print("Se encontraron estilos inline:")
    for item in errores:
        print(f"- {item}")
    sys.exit(1)

print("OK: no hay estilos inline.")
