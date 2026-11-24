"""PageEditor: el área de escritura (una hoja blanca sobre el lienzo).

Se apoya en QTextEdit/QTextDocument, que ya trae deshacer, tablas, listas, imágenes,
HTML y Markdown.  Aquí solo añadimos los comandos de formato "tipo Word".
"""
from __future__ import annotations

import html as _html
import re
import uuid

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, QRectF, QSizeF, QUrl, Qt, Signal
from PySide6.QtGui import (QBrush, QColor, QDesktopServices, QFont, QImage, QPixmap, QTextBlockFormat,
                           QTextCharFormat, QTextCursor, QTextDocument, QTextFormat, QTextFrameFormat,
                           QTextImageFormat, QTextLength, QTextListFormat, QTextTableFormat, QPainter, QPen)
from PySide6.QtWidgets import QTextEdit

from .config import DEFAULT_FONT, DEFAULT_SIZE, MAX_EMBED_IMAGE_PX, PAGINATE
from .pagedraw import paint_header_footer
from .pagesetup import CM_TO_PX, PageSetup
from .theme import PALETTE

# Estilos de párrafo: (nombre, nivel de título, tamaño en pt, negrita)
PARAGRAPH_STYLES = [
    ("Normal", 0, DEFAULT_SIZE, False),
    ("Título 1", 1, 20, True),
    ("Título 2", 2, 16, True),
    ("Título 3", 3, 13, True),
]

_PROPORTIONAL = 1  # QTextBlockFormat.LineHeightTypes.ProportionalHeight
_BOLD, _NORMAL = 700, 400


class PageEditor(QTextEdit):
    modified_changed = Signal(bool)   # el documento cambió / se guardó
    content_changed = Signal()        # el texto cambió (para contar palabras)
    file_dropped = Signal(str)        # se soltó un archivo sobre la hoja
    page_count_changed = Signal(int)  # cambió el número de hojas

    def __init__(self, parent=None):
        super().__init__(parent)
        self.default_page = PageSetup()   # hoja de los documentos nuevos (la ventana principal la actualiza)
        self.page_setup = PageSetup()     # hoja del documento actual
        self.setObjectName("page")
        self.setAcceptRichText(True)
        self.setMinimumWidth(320)
        self.setTabStopDistance(48)
        self.fresh_document()

    # ------------------------------------------------------------------ documento
    def fresh_document(self, page: PageSetup | None = None) -> QTextDocument:
        """Reemplaza el documento por uno vacío con los valores por defecto y la hoja indicada."""
        self.page_setup = (page or self.default_page).sanitized()
        doc = QTextDocument(self)
        doc.setDefaultFont(QFont(DEFAULT_FONT, DEFAULT_SIZE))
        doc.setDocumentMargin(0)  # los márgenes de la hoja se ponen en el marco raíz (ver _apply_geometry)
        self.setDocument(doc)  # el documento anterior (hijo del editor) se libera solo
        doc.modificationChanged.connect(self.modified_changed)
        doc.contentsChanged.connect(self.content_changed)
        doc.documentLayout().pageCountChanged.connect(self.page_count_changed)
        doc.setUndoRedoEnabled(False)
        bf = QTextBlockFormat()
        bf.setBottomMargin(8)
        bf.setLineHeight(108, _PROPORTIONAL)
        QTextCursor(doc).setBlockFormat(bf)
        self._apply_geometry(doc)
        doc.setUndoRedoEnabled(True)
        doc.setModified(False)
        return doc

    def _finish_load(self, doc: QTextDocument) -> None:
        self._apply_geometry(doc)  # por si al cargar el contenido Qt tocó los márgenes
        doc.setUndoRedoEnabled(True)
        doc.setModified(False)
        self.moveCursor(QTextCursor.MoveOperation.Start)

    def load_html(self, html: str, images: dict | None = None, base_dir: str | None = None,
                  page: PageSetup | None = None) -> None:
        doc = self.fresh_document(page)
        for name, data in (images or {}).items():
            img = QImage.fromData(data)
            if not img.isNull():
                doc.addResource(QTextDocument.ResourceType.ImageResource, QUrl(name), img)
        if base_dir:
            doc.setBaseUrl(QUrl.fromLocalFile(base_dir.rstrip("/\\") + "/"))
        doc.setUndoRedoEnabled(False)
        doc.setHtml(html)
        self._finish_load(doc)

    def load_markdown(self, text: str, page: PageSetup | None = None) -> None:
        doc = self.fresh_document(page)
        doc.setUndoRedoEnabled(False)
        doc.setMarkdown(text)
        self._finish_load(doc)

    def load_plain(self, text: str, page: PageSetup | None = None) -> None:
        doc = self.fresh_document(page)
        doc.setUndoRedoEnabled(False)
        doc.setPlainText(text)
        self._finish_load(doc)

    # ------------------------------------------------------------------ hoja: tamaño, márgenes, páginas
    def _apply_geometry(self, doc: QTextDocument) -> None:
        """Márgenes de la hoja (en el marco raíz) y tamaño de página: así Qt reparte el texto en hojas."""
        w, h = self.page_setup.page_px()
        left, top, right, bottom = self.page_setup.margins_px()
        root = doc.rootFrame()
        fmt = root.frameFormat()
        fmt.setLeftMargin(left)
        fmt.setRightMargin(right)
        fmt.setTopMargin(top)
        fmt.setBottomMargin(bottom)
        root.setFrameFormat(fmt)
        doc.setPageSize(QSizeF(w, h if PAGINATE else -1))
        self.setMaximumWidth(int(w) + 14)  # hoja + barra de desplazamiento + borde

    def apply_page_layout(self) -> None:
        """Aplica la hoja actual al documento abierto (esto reinicia el historial de Deshacer)."""
        doc = self.document()
        was_modified = doc.isModified()
        doc.setUndoRedoEnabled(False)
        self._apply_geometry(doc)
        doc.setUndoRedoEnabled(True)
        doc.setModified(was_modified)
        self.viewport().update()
        self.page_count_changed.emit(self.page_count())

    def set_page_setup(self, page: PageSetup) -> None:
        self.page_setup = page.sanitized()
        self.apply_page_layout()
        self.document().setModified(True)

    def _enforce_page_size(self) -> None:
        """QTextEdit vuelve a poner la hoja "sin fin" cada vez que cambia de tamaño: se la devolvemos."""
        w, h = self.page_setup.page_px()
        want = QSizeF(w, h if PAGINATE else -1)
        doc = self.document()
        if doc.pageSize() != want:
            doc.setPageSize(want)

    def page_count(self) -> int:
        return max(1, self.document().documentLayout().pageCount())

    def current_page(self) -> int:
        """Número de la hoja donde está el cursor."""
        h = self.page_setup.page_px()[1]
        y = self.cursorRect().center().y() + self.verticalScrollBar().value()
        return min(max(int(y // h) + 1, 1), self.page_count())

    def resizeEvent(self, e) -> None:
        super().resizeEvent(e)
        self._enforce_page_size()

    def paintEvent(self, e) -> None:
        super().paintEvent(e)
        try:
            self._paint_page_chrome()
        except Exception:
            pass  # el adorno de las hojas nunca debe impedir escribir

    def _paint_page_chrome(self) -> None:
        """Dibuja encima del texto: la franja gris entre hojas, el fondo tras la última y los encabezados/pies."""
        if not PAGINATE:
            return
        ps = self.page_setup
        w, h = ps.page_px()
        _, top, _, bottom = ps.margins_px()
        pages = self.page_count()
        viewport = self.viewport()
        off_x, off_y = self.horizontalScrollBar().value(), self.verticalScrollBar().value()
        gap = max(8.0, min(26.0, top + bottom - 10))
        canvas, line = QColor(PALETTE["canvas"]), QColor(PALETTE["line"])
        painter = QPainter(viewport)
        view_w, view_h = float(viewport.width()), float(viewport.height())
        first = max(0, int(off_y // h))
        last = min(pages - 1, int((off_y + view_h) // h))
        painter.setPen(QPen(line, 1))
        for k in range(max(first, 1), last + 1):  # franja gris entre la hoja k-1 y la k
            y = k * h - off_y
            painter.fillRect(QRectF(0, y - gap / 2, view_w, gap), canvas)
            painter.drawLine(QPointF(0, y - gap / 2), QPointF(view_w, y - gap / 2))
            painter.drawLine(QPointF(0, y + gap / 2), QPointF(view_w, y + gap / 2))
        end = pages * h - off_y  # lo que queda debajo de la última hoja
        if end < view_h:
            painter.fillRect(QRectF(0, max(end, 0.0), view_w, view_h - max(end, 0.0)), canvas)
            painter.drawLine(QPointF(0, end), QPointF(view_w, end))
        if ps.has_decorations():
            for k in range(first, last + 1):
                paint_header_footer(painter, ps, k, pages, k * h - off_y, -off_x, gap)
        painter.end()

    def clean_html(self) -> str:
        """HTML del documento sin el envoltorio que Qt añade cuando los márgenes de la hoja no son los normales."""
        clone = self.document().clone()
        clone.setDocumentMargin(0)
        root = clone.rootFrame()
        fmt = root.frameFormat()
        fmt.setMargin(0)
        root.setFrameFormat(fmt)
        html = clone.toHtml()
        clone.deleteLater()
        return html

    def html_and_images(self) -> tuple[str, dict[str, bytes]]:
        """HTML del documento y las imágenes que usa, listos para convertir a .docx."""
        html = self.clean_html()
        images: dict[str, bytes] = {}
        for raw in set(re.findall(r'<img\b[^>]*?\bsrc="([^"]*)"', html)):
            name = _html.unescape(raw)
            data = self._image_bytes(name)
            if data:
                images[raw] = data
                images[name] = data
        return html, images

    def _image_bytes(self, name: str) -> bytes | None:
        value = self.document().resource(QTextDocument.ResourceType.ImageResource, QUrl(name))
        img = None
        if isinstance(value, QImage):
            img = value
        elif isinstance(value, QPixmap):
            img = value.toImage()
        elif isinstance(value, (QByteArray, bytes)):
            img = QImage.fromData(value)
        if img is None or img.isNull():
            img = QImage(name)  # quizá es una ruta a un archivo
        if img.isNull():
            return None
        buf = QBuffer()
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        img.save(buf, "PNG" if img.hasAlphaChannel() else "JPG", 90)
        return buf.data().data()

    # ------------------------------------------------------------------ formato de texto
    def merge_format(self, fmt: QTextCharFormat) -> None:
        """Aplica el formato a la selección o, sin selección, a la palabra bajo el cursor."""
        cursor = self.textCursor()
        if not cursor.hasSelection():
            cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        cursor.mergeCharFormat(fmt)
        self.mergeCurrentCharFormat(fmt)

    def set_bold(self, on: bool) -> None:
        fmt = QTextCharFormat()
        fmt.setFontWeight(_BOLD if on else _NORMAL)
        self.merge_format(fmt)

    def set_italic(self, on: bool) -> None:
        fmt = QTextCharFormat()
        fmt.setFontItalic(on)
        self.merge_format(fmt)

    def set_underline(self, on: bool) -> None:
        fmt = QTextCharFormat()
        fmt.setFontUnderline(on)
        self.merge_format(fmt)

    def set_strike(self, on: bool) -> None:
        fmt = QTextCharFormat()
        fmt.setFontStrikeOut(on)
        self.merge_format(fmt)

    def set_script(self, kind: str | None) -> None:
        """kind: 'sub', 'sup' o None (texto normal)."""
        va = QTextCharFormat.VerticalAlignment
        fmt = QTextCharFormat()
        fmt.setVerticalAlignment({"sub": va.AlignSubScript, "sup": va.AlignSuperScript}.get(kind, va.AlignNormal))
        self.merge_format(fmt)

    def set_font_family(self, family: str) -> None:
        fmt = QTextCharFormat()
        fmt.setFontFamilies([family])
        self.merge_format(fmt)

    def set_font_size(self, points: float) -> None:
        if points > 0:
            fmt = QTextCharFormat()
            fmt.setFontPointSize(points)
            self.merge_format(fmt)

    def set_text_color(self, color: QColor | None) -> None:
        fmt = QTextCharFormat()
        fmt.setForeground(QBrush(color if color is not None else QColor("#000000")))
        self.merge_format(fmt)

    def set_highlight(self, color: QColor | None) -> None:
        fmt = QTextCharFormat()
        fmt.setBackground(QBrush(color) if color is not None else QBrush())  # QBrush() = sin fondo
        self.merge_format(fmt)

    def clear_formatting(self) -> None:
        """Devuelve el texto a la fuente por defecto (sin tocar imágenes ni tablas)."""
        fmt = QTextCharFormat()
        fmt.setFontFamilies([DEFAULT_FONT])
        fmt.setFontPointSize(DEFAULT_SIZE)
        fmt.setFontWeight(_NORMAL)
        fmt.setFontItalic(False)
        fmt.setFontUnderline(False)
        fmt.setFontStrikeOut(False)
        fmt.setVerticalAlignment(QTextCharFormat.VerticalAlignment.AlignNormal)
        fmt.setForeground(QBrush(QColor("#000000")))
        fmt.setBackground(QBrush())
        fmt.setAnchor(False)
        self.merge_format(fmt)

    # ------------------------------------------------------------------ párrafos
    def _selected_blocks(self) -> list:
        cur = self.textCursor()
        start, end = cur.selectionStart(), cur.selectionEnd()
        block = self.document().findBlock(start)
        blocks = []
        while block.isValid():
            blocks.append(block)
            if block.position() + block.length() >= end:
                break
            block = block.next()
        return blocks

    def set_align(self, kind: str) -> None:
        flags = Qt.AlignmentFlag
        self.setAlignment({"left": flags.AlignLeft, "center": flags.AlignHCenter,
                           "right": flags.AlignRight, "justify": flags.AlignJustify}[kind])

    def set_line_spacing(self, percent: float) -> None:
        bf = QTextBlockFormat()
        bf.setLineHeight(percent, _PROPORTIONAL)
        self.textCursor().mergeBlockFormat(bf)

    def apply_paragraph_style(self, index: int) -> None:
        _, level, size, bold = PARAGRAPH_STYLES[index]
        cf = QTextCharFormat()
        cf.setFontPointSize(size)
        cf.setFontWeight(_BOLD if bold else _NORMAL)
        cur = self.textCursor()
        cur.beginEditBlock()
        for block in self._selected_blocks():
            c = QTextCursor(block)
            bf = c.blockFormat()
            bf.setHeadingLevel(level)
            bf.setTopMargin(12 if level else 0)
            bf.setBottomMargin(4 if level else 8)
            c.setBlockFormat(bf)
            c.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            c.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
            c.mergeCharFormat(cf)
        cur.endEditBlock()
        self.mergeCurrentCharFormat(cf)

    def toggle_list(self, style: QTextListFormat.Style) -> None:
        cur = self.textCursor()
        cur.beginEditBlock()
        current = cur.currentList()
        if current is not None and current.format().style() == style:
            for block in self._selected_blocks():  # ya era de este tipo: se quita la lista
                lst = block.textList()
                if lst is not None:
                    lst.remove(block)
                c = QTextCursor(block)
                bf = c.blockFormat()
                bf.setIndent(0)
                c.setBlockFormat(bf)
        else:
            fmt = QTextListFormat()
            fmt.setStyle(style)
            fmt.setIndent(1)
            cur.createList(fmt)
        cur.endEditBlock()

    def change_indent(self, delta: int) -> None:
        cur = self.textCursor()
        cur.beginEditBlock()
        for block in self._selected_blocks():
            c = QTextCursor(block)
            lst = c.currentList()
            if lst is not None:
                lf = lst.format()
                level = lf.indent() + delta
                if level < 1:
                    continue
                above = block.previous()
                above_list = above.textList() if above.isValid() else None
                if above_list is not None and above_list.format().indent() == level:
                    above_list.add(block)
                else:
                    lf.setIndent(level)
                    c.createList(lf)
            else:
                bf = c.blockFormat()
                bf.setIndent(max(0, bf.indent() + delta))
                c.setBlockFormat(bf)
        cur.endEditBlock()

    # ------------------------------------------------------------------ insertar
    def insert_table(self, rows: int, cols: int) -> None:
        fmt = QTextTableFormat()
        fmt.setBorder(1)
        fmt.setCellPadding(4)
        fmt.setCellSpacing(0)
        fmt.setWidth(QTextLength(QTextLength.Type.PercentageLength, 100))
        try:  # borde liso en vez del relieve por defecto de Qt
            fmt.setBorderStyle(QTextFrameFormat.BorderStyle.BorderStyle_Solid)
        except AttributeError:
            pass
        self.textCursor().insertTable(rows, cols, fmt)

    def insert_image_file(self, path: str) -> bool:
        img = QImage(path)
        if img.isNull():
            return False
        if img.width() > MAX_EMBED_IMAGE_PX:
            img = img.scaledToWidth(MAX_EMBED_IMAGE_PX, Qt.TransformationMode.SmoothTransformation)
        name = f"img_{uuid.uuid4().hex[:8]}.png"
        self.document().addResource(QTextDocument.ResourceType.ImageResource, QUrl(name), img)
        width = min(img.width(), int(self.page_setup.text_width_cm() * CM_TO_PX))
        fmt = QTextImageFormat()
        fmt.setName(name)
        fmt.setWidth(width)
        fmt.setHeight(round(img.height() * width / img.width()))
        cur = self.textCursor()
        cur.insertImage(fmt)
        self.setTextCursor(cur)
        return True

    def insert_link(self, url: str) -> None:
        fmt = QTextCharFormat()
        fmt.setAnchor(True)
        fmt.setAnchorHref(url)
        fmt.setForeground(QBrush(QColor("#0563C1")))
        fmt.setFontUnderline(True)
        cur = self.textCursor()
        if cur.hasSelection():
            cur.mergeCharFormat(fmt)
        else:
            cur.insertText(url, fmt)
        self.setTextCursor(cur)
        self.setCurrentCharFormat(QTextCharFormat())  # lo que se escriba después ya no es enlace

    def insert_rule(self) -> None:
        self.textCursor().insertHtml("<hr>")

    @staticmethod
    def _break_format() -> QTextBlockFormat:
        bf = QTextBlockFormat()
        bf.setPageBreakPolicy(QTextFormat.PageBreakFlag.PageBreak_AlwaysBefore)
        return bf

    def insert_page_break(self) -> None:
        """Lo que sigue al cursor empieza en una hoja nueva."""
        cur = self.textCursor()
        cur.insertBlock(self._break_format())
        self.setTextCursor(cur)

    def insert_blank_page(self) -> None:
        """Deja una hoja completamente vacía en el cursor (lo anterior arriba, lo siguiente después)."""
        cur = self.textCursor()
        cur.beginEditBlock()
        cur.insertBlock(self._break_format())  # empieza la hoja en blanco
        cur.insertBlock(self._break_format())  # y lo que sigue empieza otra hoja
        cur.endEditBlock()
        self.setTextCursor(cur)

    def insert_text(self, text: str) -> None:
        self.textCursor().insertText(text)

    # ------------------------------------------------------------------ ventana «Párrafo»
    def paragraph_values(self) -> dict:
        """Medidas del párrafo donde está el cursor, en las unidades de la ventana «Párrafo»."""
        bf = self.textCursor().blockFormat()
        left, indent = bf.leftMargin() / CM_TO_PX, bf.textIndent() / CM_TO_PX
        if indent < -0.01:
            special, special_cm, left_cm = "hanging", -indent, left + indent
        elif indent > 0.01:
            special, special_cm, left_cm = "first", indent, left
        else:
            special, special_cm, left_cm = "none", 1.25, left
        spacing = bf.lineHeight() / 100 if bf.lineHeightType() == _PROPORTIONAL and bf.lineHeight() > 0 else 1.0
        return {"left_cm": max(left_cm, 0.0), "special": special, "special_cm": special_cm,
                "before_pt": bf.topMargin() * 0.75, "after_pt": bf.bottomMargin() * 0.75, "spacing": spacing}

    def apply_paragraph_values(self, left_cm: float, special: str, special_cm: float, before_pt: float,
                               after_pt: float, spacing: float) -> None:
        bf = QTextBlockFormat()
        if special == "hanging":      # francesa: la primera línea sale hacia la izquierda
            bf.setLeftMargin((left_cm + special_cm) * CM_TO_PX)
            bf.setTextIndent(-special_cm * CM_TO_PX)
        elif special == "first":      # primera línea con sangría
            bf.setLeftMargin(left_cm * CM_TO_PX)
            bf.setTextIndent(special_cm * CM_TO_PX)
        else:
            bf.setLeftMargin(left_cm * CM_TO_PX)
            bf.setTextIndent(0)
        bf.setTopMargin(before_pt / 0.75)
        bf.setBottomMargin(after_pt / 0.75)
        bf.setLineHeight(spacing * 100, _PROPORTIONAL)
        self.textCursor().mergeBlockFormat(bf)

    # ------------------------------------------------------------------ tablas
    def current_table(self):
        return self.textCursor().currentTable()

    def _table_and_cell(self):
        cur = self.textCursor()
        table = cur.currentTable()
        return (table, table.cellAt(cur)) if table is not None else (None, None)

    def table_add_row(self, below: bool = True) -> None:
        table, cell = self._table_and_cell()
        if table is not None:
            table.insertRows(cell.row() + (1 if below else 0), 1)

    def table_add_column(self, right: bool = True) -> None:
        table, cell = self._table_and_cell()
        if table is not None:
            table.insertColumns(cell.column() + (1 if right else 0), 1)

    def table_delete_row(self) -> None:
        table, cell = self._table_and_cell()
        if table is not None:
            if table.rows() <= 1:
                self.table_delete()
            else:
                table.removeRows(cell.row(), 1)

    def table_delete_column(self) -> None:
        table, cell = self._table_and_cell()
        if table is not None:
            if table.columns() <= 1:
                self.table_delete()
            else:
                table.removeColumns(cell.column(), 1)

    def table_delete(self) -> None:
        table = self.current_table()
        if table is not None:
            cur = QTextCursor(self.document())
            cur.setPosition(table.firstPosition() - 1)
            cur.setPosition(table.lastPosition() + 1, QTextCursor.MoveMode.KeepAnchor)
            cur.removeSelectedText()

    def table_merge_cells(self) -> None:
        table = self.current_table()
        if table is not None:
            table.mergeCells(self.textCursor())

    def _table_move(self, step: int) -> None:
        cur = self.textCursor()
        table = cur.currentTable()
        cell = table.cellAt(cur)
        index = cell.row() * table.columns() + cell.column() + step
        if index < 0:
            return
        if index >= table.rows() * table.columns():
            table.appendRows(1)
        row, col = divmod(index, table.columns())
        self.setTextCursor(table.cellAt(row, col).firstCursorPosition())

    # ------------------------------------------------------------------ eventos
    def keyPressEvent(self, e):
        key, mods = e.key(), e.modifiers()
        plain = not (mods & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier))
        if key in (Qt.Key.Key_Tab, Qt.Key.Key_Backtab) and plain:
            cur = self.textCursor()
            step = 1 if key == Qt.Key.Key_Tab else -1
            if cur.currentTable() is not None:
                self._table_move(step)
                return
            if cur.currentList() is not None:
                self.change_indent(step)
                return
        super().keyPressEvent(e)
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._drop_inherited_page_break()

    def _drop_inherited_page_break(self) -> None:
        """Al pulsar Intro, el párrafo nuevo no debe heredar el salto de página."""
        before = QTextFormat.PageBreakFlag.PageBreak_AlwaysBefore
        cur = self.textCursor()
        prev = cur.block().previous()
        bf = cur.blockFormat()
        if prev.isValid() and (bf.pageBreakPolicy() & before) and (prev.blockFormat().pageBreakPolicy() & before):
            bf.setPageBreakPolicy(QTextFormat.PageBreakFlag.PageBreak_Auto)
            cur.setBlockFormat(bf)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and (e.modifiers() & Qt.KeyboardModifier.ControlModifier):
            href = self.anchorAt(e.position().toPoint())
            if href:
                QDesktopServices.openUrl(QUrl(href))
                return
        super().mouseReleaseEvent(e)

    def canInsertFromMimeData(self, source) -> bool:
        return source.hasUrls() or super().canInsertFromMimeData(source)

    def insertFromMimeData(self, source) -> None:
        if source.hasUrls():
            for url in source.urls():
                if url.isLocalFile():
                    self.file_dropped.emit(url.toLocalFile())
                    return
        super().insertFromMimeData(source)
