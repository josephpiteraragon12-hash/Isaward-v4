"""Punto de entrada de IsaWard: crea la aplicación y la ventana principal."""
from __future__ import annotations

import sys
import traceback
from datetime import datetime
from pathlib import Path

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QMessageBox

from . import APP_NAME
from .main_window import MainWindow
from .theme import stylesheet

LOG_FILE = Path.home() / "IsaWard-errores.log"


def _excepthook(exc_type, exc, tb) -> None:
    """Muestra los errores inesperados en una ventana (el .exe no tiene consola)."""
    text = "".join(traceback.format_exception(exc_type, exc, tb))
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as fh:
            fh.write(f"\n--- {datetime.now():%Y-%m-%d %H:%M:%S} ---\n{text}")
    except OSError:
        pass
    if QApplication.instance() is not None:
        QMessageBox.critical(
            None, f"{APP_NAME}: error inesperado",
            "Algo salió mal. Tu documento puede seguir abierto: intenta guardarlo con otro nombre.\n\n"
            f"El detalle quedó guardado en:\n{LOG_FILE}\n\n{text[-900:]}")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    sys.excepthook = _excepthook
    app = QApplication(argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_NAME)
    app.setStyle("Fusion")
    if sys.platform.startswith("win"):
        app.setFont(QFont("Segoe UI", 9))
    app.setStyleSheet(stylesheet())

    window = MainWindow(open_path=argv[1] if len(argv) > 1 else None)
    window.show()
    return app.exec()
