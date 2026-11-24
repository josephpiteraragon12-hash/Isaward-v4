"""Crea un .zip limpio del proyecto para pasarlo a otra cuenta de Claude o respaldarlo.

    python tools/empaquetar.py [etiqueta]      (ejemplo: python tools/empaquetar.py segmento3)

Deja IsaWard-proyecto-AAAAMMDD.zip en la carpeta superior. No incluye entornos
virtuales, compilados ni cachés.
"""
import os
import sys
import zipfile
from datetime import date

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SKIP_DIRS = {".git", ".venv", ".venv-build", "build", "dist", "__pycache__", ".idea", ".vscode"}
SKIP_EXT = {".pyc", ".zip", ".spec"}


def main() -> None:
    label = sys.argv[1] if len(sys.argv) > 1 else f"{date.today():%Y%m%d}"
    out = os.path.join(os.path.dirname(ROOT), f"IsaWard-proyecto-{label}.zip")
    count = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for folder, dirs, files in os.walk(ROOT):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for name in files:
                if os.path.splitext(name)[1] in SKIP_EXT:
                    continue
                full = os.path.join(folder, name)
                zf.write(full, os.path.join("IsaWard", os.path.relpath(full, ROOT)))
                count += 1
    print(f"Listo: {out}  ({count} archivos)")


if __name__ == "__main__":
    sys.exit(main())
