"""Colores y hoja de estilos (QSS) de IsaWard.

Idea visual: lienzo gris azulado, hoja blanca y un solo acento verde azulado.
Todo es plano (sin sombras ni degradados) para que funcione bien en PCs modestas.
"""
from string import Template

PALETTE = {
    "ink": "#1F2B33",
    "muted": "#5B6B76",
    "canvas": "#DCE2E7",
    "paper": "#FFFFFF",
    "bar": "#F4F6F8",
    "line": "#C9D1D8",
    "hover": "#E6ECF0",
    "accent": "#0E7C86",
    "accent_dark": "#0A5F67",
    "accent_soft": "#D4ECEE",
}

_QSS = Template("""
QMainWindow, QDialog { background: $bar; color: $ink; }
QLabel { color: $ink; }
QWidget#canvas { background: $canvas; }

QMenuBar { background: $bar; color: $ink; border-bottom: 1px solid $line; }
QMenuBar::item { padding: 4px 10px; background: transparent; }
QMenuBar::item:selected { background: $accent_soft; }
QMenu { background: $paper; color: $ink; border: 1px solid $line; padding: 3px; }
QMenu::item { padding: 5px 26px 5px 24px; }
QMenu::item:selected { background: $accent_soft; color: $ink; }
QMenu::item:disabled { color: #9AA6AF; }
QMenu::separator { height: 1px; background: $line; margin: 4px 8px; }

QToolBar { background: $bar; border: none; border-bottom: 1px solid $line; spacing: 2px; padding: 3px 6px; }
QToolBar::separator { background: $line; width: 1px; margin: 4px 6px; }
QToolButton { border: 1px solid transparent; border-radius: 4px; padding: 3px; background: transparent; }
QToolButton:hover { background: $hover; border-color: $line; }
QToolButton:checked { background: $accent_soft; border-color: $accent; }
QToolButton:pressed { background: #CFE3E5; }
QToolButton::menu-indicator { image: none; }

QComboBox { background: $paper; color: $ink; border: 1px solid $line; border-radius: 4px;
            padding: 2px 6px; min-height: 22px; }
QComboBox:hover, QComboBox:focus { border-color: $accent; }
QComboBox QAbstractItemView { background: $paper; color: $ink; border: 1px solid $line;
            selection-background-color: $accent_soft; selection-color: $ink; }

QPushButton { background: $paper; color: $ink; border: 1px solid $line; border-radius: 4px; padding: 5px 14px; }
QPushButton:hover { border-color: $accent; }
QPushButton:default { background: $accent; color: white; border-color: $accent; }
QPushButton:default:hover { background: $accent_dark; }

QLineEdit, QSpinBox { background: $paper; color: $ink; border: 1px solid $line; border-radius: 4px; padding: 3px 6px; }
QLineEdit:focus, QSpinBox:focus { border-color: $accent; }
QCheckBox { color: $ink; spacing: 6px; }

QStatusBar { background: $bar; color: $muted; border-top: 1px solid $line; }
QStatusBar::item { border: none; }

QTextEdit#page { background: $paper; color: $ink; border: 1px solid $line;
                 selection-background-color: $accent_soft; selection-color: $ink; }
QScrollBar:vertical { background: transparent; width: 12px; margin: 0; }
QScrollBar::handle:vertical { background: #B7C1C9; border-radius: 5px; min-height: 30px; margin: 2px; }
QScrollBar::handle:vertical:hover { background: $accent; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }

QScrollArea { border: none; background: transparent; }
QToolTip { background: $paper; color: $ink; border: 1px solid $line; padding: 4px; }
""")


def stylesheet() -> str:
    return _QSS.substitute(PALETTE)
