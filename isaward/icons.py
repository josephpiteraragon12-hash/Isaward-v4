"""Dibuja los iconos definidos en icon_defs.py con QPainter (sin archivos de imagen)."""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPen, QPixmap, QPolygonF

from .icon_defs import ICONS

INK = "#2B3A44"
_cache: dict[tuple, QPixmap] = {}


def _poly(points) -> QPolygonF:
    return QPolygonF([QPointF(x, y) for x, y in points])


def _draw(p: QPainter, op: tuple, default: str) -> None:
    kind, args = op[0], list(op[1:])
    color = QColor(default)
    if args and isinstance(args[-1], str) and args[-1].startswith("#"):
        color = QColor(args.pop())
    stroke = QPen(color, 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)

    if kind == "l":
        p.setPen(stroke)
        p.drawLine(QPointF(args[0], args[1]), QPointF(args[2], args[3]))
    elif kind == "pl":
        p.setPen(stroke)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPolyline(_poly(args[0]))
    elif kind == "pg":
        p.setPen(stroke)
        p.setBrush(color)
        p.drawPolygon(_poly(args[0]))
    elif kind in ("r", "rf"):
        x, y, w, h = args
        if kind == "rf":
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(color)
        else:
            p.setPen(stroke)
            p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(x, y, w, h), 1.5, 1.5)
    elif kind in ("e", "ef"):
        cx, cy, rx, ry = args
        if kind == "ef":
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(color)
        else:
            p.setPen(stroke)
            p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), rx, ry)
    elif kind == "t":
        text, cx, cy, size, style = args[:5]
        font = QFont("Times New Roman" if "s" in style else "Arial")
        font.setPixelSize(max(1, round(size)))
        font.setBold("b" in style)
        font.setItalic("i" in style)
        p.setFont(font)
        p.setPen(color)
        p.drawText(QRectF(cx - 12, cy - 12, 24, 24), Qt.AlignmentFlag.AlignCenter, text)


def make_pixmap(name: str, color: str = INK, size: int = 48) -> QPixmap:
    key = (name, color, size)
    if key not in _cache:
        pm = QPixmap(size, size)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        p.scale(size / 24, size / 24)
        for op in ICONS[name]:
            _draw(p, op, color)
        p.end()
        _cache[key] = pm
    return _cache[key]


def make_icon(name: str, color: str = INK) -> QIcon:
    """Icono para botones y menús (hay que llamarlo después de crear QApplication)."""
    return QIcon(make_pixmap(name, color))
