"""Dibujo del encabezado y el pie de una hoja.  Lo usan la pantalla (editor) y la impresión/PDF."""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QTextOption

from .config import DEFAULT_FONT
from .pagesetup import PageSetup, expand_tokens

HEADER_FOOTER_COLOR = "#6B7780"
LINE_HEIGHT = 16.0


def paint_header_footer(painter: QPainter, page: PageSetup, index: int, pages: int,
                        top_y: float, x_offset: float = 0.0, gap: float = 0.0) -> None:
    """Dibuja el encabezado y el pie de la hoja número `index` (desde 0).

    top_y: coordenada vertical donde empieza esa hoja.  x_offset: desplazamiento horizontal (scroll).
    gap: alto de la franja gris que separa hojas en pantalla (0 al imprimir).
    """
    if page.first_page_different and index == 0:
        return
    slots = page.composed()
    if not any(any(s) for s in slots.values()):
        return
    w, h = page.page_px()
    left, top, right, bottom = page.margins_px()
    font = QFont(DEFAULT_FONT)
    font.setPixelSize(12)  # en píxeles: así no se agranda al imprimir (el pintor ya viene escalado)
    painter.save()
    painter.setFont(font)
    painter.setPen(QColor(HEADER_FOOTER_COLOR))
    x, width = left + x_offset, w - left - right
    for key in ("header", "footer"):
        texts = slots[key]
        if not any(texts):
            continue
        if key == "header":
            y = top_y + max(gap / 2 + 4, top * 0.35)
        else:
            y = top_y + h - max(gap / 2 + 4, bottom * 0.35) - LINE_HEIGHT
        rect = QRectF(x, y, width, LINE_HEIGHT)
        for text, align in zip(texts, (Qt.AlignmentFlag.AlignLeft, Qt.AlignmentFlag.AlignHCenter,
                                       Qt.AlignmentFlag.AlignRight)):
            if text:
                option = QTextOption(align | Qt.AlignmentFlag.AlignVCenter)
                option.setWrapMode(QTextOption.WrapMode.NoWrap)
                painter.drawText(rect, expand_tokens(text, index + 1, pages), option)
    painter.restore()
