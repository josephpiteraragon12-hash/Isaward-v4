"""Ventanas auxiliares: Buscar y reemplazar, Tabla, Configurar página, Encabezado y pie, Párrafo, Símbolos,
Fecha y la Guía de herramientas (con «Más información», recetas y atajos)."""
from __future__ import annotations

import html as _html
from datetime import datetime

from PySide6.QtCore import QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QTextCursor, QTextDocument, QTextOption
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox,
                               QFormLayout, QFrame, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                               QListView, QListWidget, QListWidgetItem, QMessageBox, QPushButton, QRadioButton,
                               QScrollArea, QSpinBox, QTabWidget, QTextBrowser, QVBoxLayout, QWidget)

from .datefmt import date_options
from .howto import RECIPES
from .icons import make_pixmap
from .symbols import SYMBOL_GROUPS, symbols_of
from .pagesetup import (CUSTOM, MARGIN_PRESETS, NUMBER_FORMATS, NUMBER_POSITIONS, PAGE_SIZES, SIZE_LABELS,
                        PageSetup)
from .theme import PALETTE
from .tools import (EXTRA_SHORTCUTS, GROUP_ORDER, TOOL_BY_ID, TOOLS, icon_of, matches, shortcut_text)


def _es(number: float) -> str:
    """Número con coma decimal, como se escribe en español."""
    return f"{number:.2f}".rstrip("0").rstrip(".").replace(".", ",")


class FindReplaceDialog(QDialog):
    """Ventana flotante (no bloquea el documento) para buscar y reemplazar."""

    def __init__(self, editor, parent=None):
        super().__init__(parent)
        self.editor = editor
        self.setWindowTitle("Buscar y reemplazar")
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        self.find_edit = QLineEdit()
        self.repl_edit = QLineEdit()
        self.case_chk = QCheckBox("Distinguir mayúsculas y minúsculas")
        self.word_chk = QCheckBox("Solo palabras completas")
        self.msg = QLabel("")
        self.msg.setStyleSheet(f"color: {PALETTE['muted']};")

        form = QFormLayout()
        form.addRow("Buscar:", self.find_edit)
        form.addRow("Reemplazar con:", self.repl_edit)

        btn_next = QPushButton("Buscar siguiente")
        btn_next.setDefault(True)
        btn_prev = QPushButton("Buscar anterior")
        btn_one = QPushButton("Reemplazar")
        btn_all = QPushButton("Reemplazar todo")
        btn_close = QPushButton("Cerrar")
        btn_next.clicked.connect(lambda: self.find_next(False))
        btn_prev.clicked.connect(lambda: self.find_next(True))
        btn_one.clicked.connect(self.replace_one)
        btn_all.clicked.connect(self.replace_all)
        btn_close.clicked.connect(self.close)
        self.find_edit.returnPressed.connect(lambda: self.find_next(False))

        grid = QGridLayout()
        grid.addWidget(btn_next, 0, 0)
        grid.addWidget(btn_prev, 0, 1)
        grid.addWidget(btn_one, 1, 0)
        grid.addWidget(btn_all, 1, 1)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.case_chk)
        layout.addWidget(self.word_chk)
        layout.addLayout(grid)
        layout.addWidget(self.msg)
        layout.addWidget(btn_close, 0, Qt.AlignmentFlag.AlignRight)
        self.setMinimumWidth(380)

    def open_for_selection(self) -> None:
        selected = self.editor.textCursor().selectedText()
        if selected and "\u2029" not in selected:
            self.find_edit.setText(selected)
        self.msg.setText("")
        self.show()
        self.raise_()
        self.activateWindow()
        self.find_edit.setFocus()
        self.find_edit.selectAll()

    def _flags(self, backwards: bool = False) -> QTextDocument.FindFlag:
        flags = QTextDocument.FindFlag(0)
        if self.case_chk.isChecked():
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        if self.word_chk.isChecked():
            flags |= QTextDocument.FindFlag.FindWholeWords
        if backwards:
            flags |= QTextDocument.FindFlag.FindBackward
        return flags

    def find_next(self, backwards: bool = False) -> bool:
        text = self.find_edit.text()
        if not text:
            return False
        flags = self._flags(backwards)
        if self.editor.find(text, flags):
            self.msg.setText("")
            return True
        cursor = self.editor.textCursor()  # se llegó al final: se vuelve a empezar
        cursor.movePosition(QTextCursor.MoveOperation.End if backwards else QTextCursor.MoveOperation.Start)
        self.editor.setTextCursor(cursor)
        if self.editor.find(text, flags):
            self.msg.setText("Se volvió a empezar desde el otro extremo del documento.")
            return True
        self.msg.setText(f"No se encontró «{text}».")
        return False

    def replace_one(self) -> None:
        text = self.find_edit.text()
        cursor = self.editor.textCursor()
        selected = cursor.selectedText()
        same = selected == text if self.case_chk.isChecked() else selected.lower() == text.lower()
        if text and same:
            cursor.insertText(self.repl_edit.text())
        self.find_next(False)

    def replace_all(self) -> None:
        text = self.find_edit.text()
        if not text:
            return
        doc = self.editor.document()
        flags = self._flags()
        guard = QTextCursor(doc)
        guard.beginEditBlock()  # un solo "deshacer" para todos los cambios
        pos, count = 0, 0
        while True:
            found = doc.find(text, pos, flags)
            if found.isNull():
                break
            found.insertText(self.repl_edit.text())
            pos = found.position()
            count += 1
        guard.endEditBlock()
        self.msg.setText(f"Se hicieron {count} reemplazo(s)." if count else f"No se encontró «{text}».")


class TableDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Insertar tabla")
        self.rows = QSpinBox()
        self.rows.setRange(1, 100)
        self.rows.setValue(3)
        self.cols = QSpinBox()
        self.cols.setRange(1, 20)
        self.cols.setValue(3)
        form = QFormLayout()
        form.addRow("Filas:", self.rows)
        form.addRow("Columnas:", self.cols)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Insertar")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)


class PagePreview(QWidget):
    """Dibujito de la hoja con sus márgenes (se actualiza al cambiar las medidas)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.page = PageSetup()
        self.setMinimumSize(180, 230)

    def set_page(self, page: PageSetup) -> None:
        self.page = page
        self.update()

    def paintEvent(self, e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.page.width_cm, self.page.height_cm
        area = QRectF(self.rect()).adjusted(12, 10, -16, -28)
        scale = min(area.width() / w, area.height() / h)
        pw, ph = w * scale, h * scale
        x, y = area.center().x() - pw / 2, area.top() + (area.height() - ph) / 2
        p.fillRect(QRectF(x + 4, y + 4, pw, ph), QColor("#C9D1D8"))  # sombra
        p.fillRect(QRectF(x, y, pw, ph), QColor("white"))
        p.setPen(QPen(QColor(PALETTE["line"]), 1))
        p.drawRect(QRectF(x, y, pw, ph))
        left, top = self.page.left_cm * scale, self.page.top_cm * scale
        right, bottom = self.page.right_cm * scale, self.page.bottom_cm * scale
        text = QRectF(x + left, y + top, pw - left - right, ph - top - bottom)
        if text.width() > 6 and text.height() > 6:
            p.setPen(QPen(QColor("#B7C1C9"), 1))  # rayitas que imitan el texto
            line_y = text.top() + 5
            while line_y < text.bottom() - 2:
                p.drawLine(int(text.left() + 2), int(line_y), int(text.right() - 2), int(line_y))
                line_y += 6
            p.setPen(QPen(QColor(PALETTE["accent"]), 1, Qt.PenStyle.DashLine))  # zona donde se escribe
            p.drawRect(text)
        p.setPen(QColor(PALETTE["muted"]))
        p.drawText(QRectF(0, self.height() - 24, self.width(), 20), f"{_es(w)} × {_es(h)} cm",
                   QTextOption(Qt.AlignmentFlag.AlignCenter))
        p.end()


def _cm_spin(low: float, high: float) -> QDoubleSpinBox:
    spin = QDoubleSpinBox()
    spin.setRange(low, high)
    spin.setDecimals(2)
    spin.setSingleStep(0.25)
    spin.setSuffix(" cm")
    return spin


def _help_button(dialog: QDialog, tool_id: str) -> QPushButton:
    button = QPushButton("Ayuda")
    button.setToolTip("Abre la guía con la explicación completa de esta ventana")
    button.clicked.connect(lambda: GuideDialog(dialog, tool_id=tool_id).exec())
    return button


class PageSetupDialog(QDialog):
    """Tamaño de la hoja, orientación y márgenes."""

    def __init__(self, parent, page: PageSetup):
        super().__init__(parent)
        self.setWindowTitle("Configurar página")
        self._base = PageSetup.from_dict(page.to_dict())  # copia: conserva encabezado, pie, etc.
        self._result = self._base
        self._busy = False

        self.size_combo = QComboBox()
        for name in PAGE_SIZES:
            self.size_combo.addItem(SIZE_LABELS[name], name)
        self.size_combo.addItem("Personalizado (escribe las medidas)", CUSTOM)
        self.portrait = QRadioButton("Vertical  (hoja alta)")
        self.landscape = QRadioButton("Horizontal  (hoja ancha)")
        group = QButtonGroup(self)
        group.addButton(self.portrait)
        group.addButton(self.landscape)
        self.width_spin, self.height_spin = _cm_spin(5, 100), _cm_spin(5, 150)

        self.margin_combo = QComboBox()
        for name in MARGIN_PRESETS:
            self.margin_combo.addItem(name)
        self.margin_combo.addItem("Personalizado (escribe las medidas)")
        self.top, self.bottom = _cm_spin(0, 15), _cm_spin(0, 15)
        self.left, self.right = _cm_spin(0, 15), _cm_spin(0, 15)

        self.preview = PagePreview()
        self.default_chk = QCheckBox("Usar esta hoja para los documentos nuevos")

        size_box = QGroupBox("Tamaño de la hoja")
        size_form = QFormLayout(size_box)
        size_form.addRow(self.size_combo)
        orient = QHBoxLayout()
        orient.addWidget(self.portrait)
        orient.addWidget(self.landscape)
        size_form.addRow("Orientación:", orient)
        size_form.addRow("Ancho:", self.width_spin)
        size_form.addRow("Alto:", self.height_spin)

        margin_box = QGroupBox("Márgenes (espacio en blanco en los bordes)")
        margin_form = QFormLayout(margin_box)
        margin_form.addRow(self.margin_combo)
        margin_form.addRow("Arriba:", self.top)
        margin_form.addRow("Abajo:", self.bottom)
        margin_form.addRow("Izquierda:", self.left)
        margin_form.addRow("Derecha:", self.right)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Aceptar")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.addButton(_help_button(self, "page_setup"), QDialogButtonBox.ButtonRole.HelpRole)

        left_col = QVBoxLayout()
        left_col.addWidget(size_box)
        left_col.addWidget(margin_box)
        main = QHBoxLayout()
        main.addLayout(left_col, 1)
        main.addWidget(self.preview, 0)
        layout = QVBoxLayout(self)
        layout.addLayout(main)
        layout.addWidget(self.default_chk)
        layout.addWidget(buttons)

        self._load(self._base)
        self.size_combo.currentIndexChanged.connect(self._on_size)
        self.landscape.toggled.connect(self._on_orientation)
        self.width_spin.valueChanged.connect(self._on_dims)
        self.height_spin.valueChanged.connect(self._on_dims)
        self.margin_combo.currentIndexChanged.connect(self._on_margin_preset)
        for spin in (self.top, self.bottom, self.left, self.right):
            spin.valueChanged.connect(self._on_margin_spin)

    # ---- estado ----
    def _load(self, page: PageSetup) -> None:
        self._busy = True
        index = self.size_combo.findData(page.size_name())
        self.size_combo.setCurrentIndex(index if index >= 0 else self.size_combo.count() - 1)
        (self.landscape if page.landscape else self.portrait).setChecked(True)
        self.width_spin.setValue(page.width_cm)
        self.height_spin.setValue(page.height_cm)
        self.top.setValue(page.top_cm)
        self.bottom.setValue(page.bottom_cm)
        self.left.setValue(page.left_cm)
        self.right.setValue(page.right_cm)
        self._pick_margin_preset()
        self._busy = False
        self._update_preview()

    def _page(self) -> PageSetup:
        page = self._base.with_margins(self.top.value(), self.bottom.value(), self.left.value(), self.right.value())
        page.width_cm, page.height_cm = self.width_spin.value(), self.height_spin.value()
        return page

    def _update_preview(self) -> None:
        self.preview.set_page(self._page())

    def _pick_margin_preset(self) -> None:
        values = (self.top.value(), self.bottom.value(), self.left.value(), self.right.value())
        for i, preset in enumerate(MARGIN_PRESETS.values()):
            if all(abs(a - b) < 0.005 for a, b in zip(values, preset)):
                self.margin_combo.setCurrentIndex(i)
                return
        self.margin_combo.setCurrentIndex(self.margin_combo.count() - 1)

    # ---- reacciones ----
    def _on_size(self, index: int) -> None:
        name = self.size_combo.itemData(index)
        if self._busy or name == CUSTOM:
            return
        w, h = PAGE_SIZES[name]
        if self.landscape.isChecked():
            w, h = h, w
        self._busy = True
        self.width_spin.setValue(w)
        self.height_spin.setValue(h)
        self._busy = False
        self._update_preview()

    def _on_orientation(self, _checked: bool) -> None:
        if self._busy:
            return
        w, h = self.width_spin.value(), self.height_spin.value()
        if (w > h) != self.landscape.isChecked():
            self._busy = True
            self.width_spin.setValue(h)
            self.height_spin.setValue(w)
            self._busy = False
        self._update_preview()

    def _on_dims(self, _value: float) -> None:
        if self._busy:
            return
        page = self._page()
        self._busy = True
        index = self.size_combo.findData(page.size_name())
        self.size_combo.setCurrentIndex(index if index >= 0 else self.size_combo.count() - 1)
        (self.landscape if page.landscape else self.portrait).setChecked(True)
        self._busy = False
        self._update_preview()

    def _on_margin_preset(self, index: int) -> None:
        if self._busy or index >= len(MARGIN_PRESETS):
            return
        top, bottom, left, right = list(MARGIN_PRESETS.values())[index]
        self._busy = True
        self.top.setValue(top)
        self.bottom.setValue(bottom)
        self.left.setValue(left)
        self.right.setValue(right)
        self._busy = False
        self._update_preview()

    def _on_margin_spin(self, _value: float) -> None:
        if self._busy:
            return
        self._busy = True
        self._pick_margin_preset()
        self._busy = False
        self._update_preview()

    # ---- resultado ----
    def accept(self) -> None:
        wanted = self._page()
        fixed = wanted.sanitized()
        if fixed != wanted:
            QMessageBox.information(self, "Márgenes ajustados",
                                    "Los márgenes que pusiste dejaban muy poco espacio para escribir, "
                                    "así que los reduje un poco.")
        self._result = fixed
        super().accept()

    def result_page(self) -> PageSetup:
        return self._result

    def as_default(self) -> bool:
        return self.default_chk.isChecked()


class HeaderFooterDialog(QDialog):
    """Encabezado, pie de página y numeración."""

    def __init__(self, parent, page: PageSetup, focus_numbers: bool = False):
        super().__init__(parent)
        self.setWindowTitle("Encabezado y pie de página")
        self._base = PageSetup.from_dict(page.to_dict())

        def edits(values):
            fields = [QLineEdit(v) for v in values]
            for field, hint in zip(fields, ("Izquierda", "Centro", "Derecha")):
                field.setPlaceholderText(hint)
            return fields

        self.header = edits((page.header_left, page.header_center, page.header_right))
        self.footer = edits((page.footer_left, page.footer_center, page.footer_right))

        self.pos_combo = QComboBox()
        for key, label in NUMBER_POSITIONS.items():
            self.pos_combo.addItem(label, key)
        self.pos_combo.setCurrentIndex(max(self.pos_combo.findData(page.number_pos), 0))
        self.fmt_combo = QComboBox()
        for fmt, example in NUMBER_FORMATS.items():
            self.fmt_combo.addItem(example, fmt)
        self.fmt_combo.setCurrentIndex(max(self.fmt_combo.findData(page.number_fmt), 0))
        self.first_chk = QCheckBox("No mostrar nada en la primera hoja (por ejemplo, la portada)")
        self.first_chk.setChecked(page.first_page_different)
        self.pos_combo.currentIndexChanged.connect(self._toggle_format)
        self._toggle_format()

        def box(title, fields, tip):
            group = QGroupBox(title)
            grid = QGridLayout(group)
            for col, (name, field) in enumerate(zip(("Izquierda", "Centro", "Derecha"), fields)):
                grid.addWidget(QLabel(name), 0, col)
                grid.addWidget(field, 1, col)
            hint = QLabel(tip)
            hint.setStyleSheet(f"color: {PALETTE['muted']};")
            hint.setWordWrap(True)
            grid.addWidget(hint, 2, 0, 1, 3)
            return group

        numbers = QGroupBox("Números de página")
        form = QFormLayout(numbers)
        form.addRow("Dónde:", self.pos_combo)
        form.addRow("Cómo se escribe:", self.fmt_combo)

        note = QLabel("Truco: en cualquier cuadro puedes escribir {pagina} (número de la hoja) y {paginas} "
                      "(total de hojas). Por ejemplo:  Página {pagina} de {paginas}")
        note.setWordWrap(True)
        note.setStyleSheet(f"background:{PALETTE['accent_soft']}; border-radius:6px; padding:8px;")

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Aceptar")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.addButton(_help_button(self, "header_footer"), QDialogButtonBox.ButtonRole.HelpRole)

        layout = QVBoxLayout(self)
        layout.addWidget(box("Encabezado (arriba de cada hoja)", self.header, "Ejemplo: nombre del colegio a la izquierda, título del trabajo a la derecha."))
        layout.addWidget(box("Pie de página (abajo de cada hoja)", self.footer, "Ejemplo: tu nombre y curso."))
        layout.addWidget(numbers)
        layout.addWidget(self.first_chk)
        layout.addWidget(note)
        layout.addWidget(buttons)
        self.setMinimumWidth(520)
        if focus_numbers:
            QTimer.singleShot(0, self.pos_combo.setFocus)

    def _toggle_format(self) -> None:
        self.fmt_combo.setEnabled(self.pos_combo.currentData() != "none")

    def result_page(self) -> PageSetup:
        page = PageSetup.from_dict(self._base.to_dict())
        page.header_left, page.header_center, page.header_right = (f.text().strip() for f in self.header)
        page.footer_left, page.footer_center, page.footer_right = (f.text().strip() for f in self.footer)
        page.number_pos = self.pos_combo.currentData()
        page.number_fmt = self.fmt_combo.currentData()
        page.first_page_different = self.first_chk.isChecked()
        return page


class ParagraphDialog(QDialog):
    """Sangrías, espacios y interlineado con medidas exactas."""

    HINTS = {
        "none": "Todo el párrafo se acomoda igual.",
        "first": "Solo la primera línea entra hacia la derecha (típico de los textos escritos).",
        "hanging": "La primera línea queda pegada al margen y las demás entran. Así se arma la bibliografía (APA).",
    }

    def __init__(self, parent, values: dict):
        super().__init__(parent)
        self.setWindowTitle("Párrafo")
        self.left = _cm_spin(0, 20)
        self.left.setValue(values["left_cm"])
        self.special = QComboBox()
        for label, key in (("Ninguna", "none"), ("Primera línea", "first"), ("Francesa (bibliografía)", "hanging")):
            self.special.addItem(label, key)
        self.special.setCurrentIndex(max(self.special.findData(values["special"]), 0))
        self.special_cm = _cm_spin(0, 10)
        self.special_cm.setValue(values["special_cm"])
        self.before, self.after = QDoubleSpinBox(), QDoubleSpinBox()
        for spin, value in ((self.before, values["before_pt"]), (self.after, values["after_pt"])):
            spin.setRange(0, 200)
            spin.setDecimals(1)
            spin.setSuffix(" pt")
            spin.setValue(value)
        self.spacing = QDoubleSpinBox()
        self.spacing.setRange(0.5, 5.0)
        self.spacing.setDecimals(2)
        self.spacing.setSingleStep(0.05)
        self.spacing.setSuffix(" veces")
        self.spacing.setValue(values["spacing"])
        self.hint = QLabel()
        self.hint.setWordWrap(True)
        self.hint.setStyleSheet(f"color: {PALETTE['muted']};")
        self.special.currentIndexChanged.connect(self._on_special)
        self._on_special()

        form = QFormLayout()
        form.addRow("Sangría izquierda:", self.left)
        form.addRow("Sangría especial:", self.special)
        form.addRow("   Cuánto entra:", self.special_cm)
        form.addRow(self.hint)
        form.addRow("Espacio antes del párrafo:", self.before)
        form.addRow("Espacio después del párrafo:", self.after)
        form.addRow("Interlineado:", self.spacing)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Aceptar")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.addButton(_help_button(self, "paragraph"), QDialogButtonBox.ButtonRole.HelpRole)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setMinimumWidth(430)

    def _on_special(self) -> None:
        key = self.special.currentData()
        self.special_cm.setEnabled(key != "none")
        self.hint.setText(self.HINTS[key])

    def values(self) -> dict:
        return {"left_cm": self.left.value(), "special": self.special.currentData(),
                "special_cm": self.special_cm.value(), "before_pt": self.before.value(),
                "after_pt": self.after.value(), "spacing": self.spacing.value()}


class SymbolDialog(QDialog):
    """Tabla de símbolos: doble clic para insertar. Queda abierta para poner varios."""

    def __init__(self, parent, insert):
        super().__init__(parent)
        self.setWindowTitle("Símbolo")
        self._insert = insert
        self.group = QComboBox()
        self.group.addItems(list(SYMBOL_GROUPS))
        self.grid = QListWidget()
        self.grid.setViewMode(QListView.ViewMode.IconMode)
        self.grid.setResizeMode(QListView.ResizeMode.Adjust)
        self.grid.setMovement(QListView.Movement.Static)
        self.grid.setGridSize(QSize(44, 44))
        self.grid.setUniformItemSizes(True)
        font = QFont("Segoe UI Symbol")
        font.setPixelSize(22)
        self.grid.setFont(font)
        self.grid.itemDoubleClicked.connect(lambda item: self._insert(item.text()))
        self.group.currentTextChanged.connect(self._fill)
        self._fill(self.group.currentText())

        hint = QLabel("Haz doble clic en un símbolo para ponerlo en el documento. "
                      "Puedes poner varios seguidos; cierra la ventana cuando termines.")
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {PALETTE['muted']};")
        insert_btn, close_btn = QPushButton("Insertar"), QPushButton("Cerrar")
        insert_btn.setDefault(True)
        insert_btn.clicked.connect(self._insert_selected)
        close_btn.clicked.connect(self.close)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(insert_btn)
        row.addWidget(close_btn)
        layout = QVBoxLayout(self)
        layout.addWidget(self.group)
        layout.addWidget(self.grid, 1)
        layout.addWidget(hint)
        layout.addLayout(row)
        self.resize(460, 430)

    def _fill(self, name: str) -> None:
        self.grid.clear()
        for ch in symbols_of(name):
            item = QListWidgetItem(ch)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setToolTip(f"U+{ord(ch[0]):04X}")
            self.grid.addItem(item)

    def _insert_selected(self) -> None:
        item = self.grid.currentItem()
        if item is not None:
            self._insert(item.text())


class DateDialog(QDialog):
    """Elige cómo escribir la fecha o la hora de hoy."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Fecha y hora")
        self.list = QListWidget()
        self.list.addItems(date_options(datetime.now()))
        self.list.setCurrentRow(0)
        self.list.itemDoubleClicked.connect(lambda _item: self.accept())
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Insertar")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Elige cómo quieres escribirla (doble clic para insertar):"))
        layout.addWidget(self.list)
        layout.addWidget(buttons)
        self.setMinimumWidth(380)

    def chosen(self) -> str:
        item = self.list.currentItem()
        return item.text() if item is not None else ""


class ExpandableRow(QWidget):
    """Una fila de la guía: dibujo + explicación corta + botón «Más información» que despliega el detalle."""

    def __init__(self, pixmap, head_html: str, details_html: str,
                 open_text: str = "Más información", close_text: str = "Ocultar", parent=None):
        super().__init__(parent)
        self._open_text, self._close_text = open_text, close_text
        icon = QLabel()
        icon.setFixedWidth(36)
        if pixmap is not None:
            icon.setPixmap(pixmap)
        head = QLabel(head_html)
        head.setWordWrap(True)
        head.setTextFormat(Qt.TextFormat.RichText)
        self.button = QPushButton(f"{open_text} ▾")
        self.button.setFlat(True)
        self.button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.button.setStyleSheet(f"QPushButton {{ color: {PALETTE['accent_dark']}; border: none; padding: 2px 6px; "
                                  "text-decoration: underline; }}")
        self.button.clicked.connect(lambda: self.set_open(not self.details.isVisible()))
        self.details = QLabel(details_html)
        self.details.setWordWrap(True)
        self.details.setTextFormat(Qt.TextFormat.RichText)
        self.details.setStyleSheet(f"background: {PALETTE['accent_soft']}; border-radius: 6px; padding: 10px;")
        self.details.setVisible(False)

        top = QHBoxLayout()
        top.addWidget(icon, 0, Qt.AlignmentFlag.AlignTop)
        top.addWidget(head, 1)
        top.addWidget(self.button, 0, Qt.AlignmentFlag.AlignTop)
        indent = QHBoxLayout()
        indent.addSpacing(36)
        indent.addWidget(self.details, 1)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.addLayout(top)
        layout.addLayout(indent)

    def set_open(self, on: bool) -> None:
        self.details.setVisible(on)
        self.button.setText(f"{self._close_text if on else self._open_text} {'▴' if on else '▾'}")


def _hline() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet(f"color: {PALETTE['line']};")
    return line


def _rich(text: str) -> str:
    return _html.escape(text).replace("\n", "<br>")


class GuideDialog(QDialog):
    """La guía (F1): «Botones» (todo lo que hace el programa), «¿Cómo hago…?» (recetas) y «Atajos»."""

    def __init__(self, parent=None, tab: int = 0, tool_id: str | None = None):
        super().__init__(parent)
        self.setWindowTitle("Guía de IsaWard")
        self.resize(700, 720)
        muted = PALETTE["muted"]
        self._tool_rows: dict[str, ExpandableRow] = {}
        self._entries: list[tuple[QWidget, str]] = []       # (fila, texto donde se busca)
        self._groups: list[tuple[list[QWidget], list[QWidget]]] = []  # (cabeceras, filas) de cada grupo

        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar en la guía…  (por ejemplo: página, tabla, color, imprimir)")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._filter)
        self.empty = QLabel("No encontré nada con esa búsqueda. Prueba con otra palabra (por ejemplo: hoja, tabla, letra).")
        self.empty.setStyleSheet(f"color: {muted};")
        self.empty.setWordWrap(True)
        self.empty.setVisible(False)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._tools_tab(), "Botones")
        self.tabs.addTab(self._howto_tab(), "¿Cómo hago…?")
        self.tabs.addTab(self._keys_tab(), "Atajos")

        close = QPushButton("Cerrar")
        close.setDefault(True)
        close.clicked.connect(self.accept)
        layout = QVBoxLayout(self)
        layout.addWidget(self.search)
        layout.addWidget(self.empty)
        layout.addWidget(self.tabs, 1)
        layout.addWidget(close, 0, Qt.AlignmentFlag.AlignRight)

        self.tabs.setCurrentIndex(tab)
        if tool_id and tool_id in self._tool_rows:
            self.tabs.setCurrentIndex(0)
            row = self._tool_rows[tool_id]
            row.set_open(True)
            QTimer.singleShot(60, lambda: self._tools_scroll.ensureWidgetVisible(row, 0, 40))

    # ---- pestañas ----
    def _scroll(self, body: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(body)
        return scroll

    def _tools_tab(self) -> QWidget:
        muted = PALETTE["muted"]
        body = QWidget()
        col = QVBoxLayout(body)
        col.setSpacing(2)
        intro = QLabel("Cada botón del programa, con su dibujo, para qué sirve y dónde está. "
                       "Toca <b>Más información</b> para leer cómo se usa.")
        intro.setWordWrap(True)
        toggles = QHBoxLayout()
        open_all, close_all = QPushButton("Abrir todo"), QPushButton("Cerrar todo")
        open_all.clicked.connect(lambda: self._set_all(True))
        close_all.clicked.connect(lambda: self._set_all(False))
        toggles.addWidget(intro, 1)
        toggles.addWidget(open_all)
        toggles.addWidget(close_all)
        col.addLayout(toggles)
        for group in GROUP_ORDER:
            tools = [t for t in TOOLS if t.group == group]
            if not tools:
                continue
            head = QLabel(f"<b>{group}</b>")
            head.setStyleSheet("font-size: 11pt; padding-top: 10px;")
            line = _hline()
            col.addWidget(head)
            col.addWidget(line)
            rows = []
            for t in tools:
                shortcut = f" &nbsp;<span style='color:{muted}'>{_html.escape(shortcut_text(t.shortcut))}</span>" if t.shortcut else ""
                head_html = (f"<b>{_html.escape(t.label)}</b>{shortcut}<br>{_html.escape(t.help)}"
                             f"<br><span style='color:{muted}'><i>Dónde está:</i> {_html.escape(t.where)}</span>")
                pixmap = make_pixmap(icon_of(t), size=48).scaled(
                    28, 28, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                row = ExpandableRow(pixmap, head_html, _rich(t.more))
                col.addWidget(row)
                rows.append(row)
                self._tool_rows[t.id] = row
                self._entries.append((row, " ".join((t.label, t.help, t.where, t.more, t.group))))
            self._groups.append(([head, line], rows))
        col.addStretch(1)
        self._tools_scroll = self._scroll(body)
        return self._tools_scroll

    def _howto_tab(self) -> QWidget:
        muted = PALETTE["muted"]
        body = QWidget()
        col = QVBoxLayout(body)
        col.setSpacing(2)
        intro = QLabel("Pasos cortos para las cosas que más se hacen. Toca <b>Ver los pasos</b>.")
        intro.setWordWrap(True)
        col.addWidget(intro)
        rows = []
        for r in RECIPES:
            steps = "".join(f"<li>{_html.escape(s)}</li>" for s in r.steps)
            tip = f"<p style='color:{muted}'><i>Consejo:</i> {_html.escape(r.tip)}</p>" if r.tip else ""
            used = ", ".join(_html.escape(TOOL_BY_ID[t].label) for t in r.tools)
            details = f"<ol>{steps}</ol>{tip}<p style='color:{muted}'>Botones que usarás: {used}</p>"
            pixmap = make_pixmap(icon_of(TOOL_BY_ID[r.tools[0]]), size=48).scaled(
                28, 28, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            row = ExpandableRow(pixmap, f"<b>{_html.escape(r.title)}</b>", details, "Ver los pasos", "Ocultar")
            col.addWidget(row)
            col.addWidget(_hline())
            rows.append(row)
            self._entries.append((row, " ".join((r.title, r.keywords, " ".join(r.steps), r.tip))))
        self._groups.append(([], rows))
        col.addStretch(1)
        return self._scroll(body)

    def _keys_tab(self) -> QWidget:
        muted = PALETTE["muted"]
        rows = "".join(
            f"<tr><td style='padding:3px 14px 3px 0'><b>{_html.escape(shortcut_text(t.shortcut))}</b></td>"
            f"<td>{_html.escape(t.label)} <span style='color:{muted}'>— {_html.escape(t.help)}</span></td></tr>"
            for t in TOOLS if t.shortcut)
        extra = "".join(
            f"<tr><td style='padding:3px 14px 3px 0'><b>{_html.escape(k)}</b></td><td>{_html.escape(v)}</td></tr>"
            for k, v in EXTRA_SHORTCUTS)
        browser = QTextBrowser()
        browser.setHtml(f"<h3>Teclas para trabajar más rápido</h3><table>{rows}</table>"
                        f"<h3>Otros gestos</h3><table>{extra}</table>")
        return browser

    # ---- acciones ----
    def _set_all(self, on: bool) -> None:
        for row in self._tool_rows.values():
            if row.isVisible() or not on:
                row.set_open(on)

    def _filter(self, text: str) -> None:
        shown = 0
        visible_by_row = {id(row): (not text.strip()) or matches(text, key) for row, key in self._entries}
        for row, _key in self._entries:
            ok = visible_by_row[id(row)]
            row.setVisible(ok)
            shown += ok
        for headers, rows in self._groups:
            any_visible = any(visible_by_row.get(id(r), True) for r in rows)
            for widget in headers:
                widget.setVisible(any_visible)
        self.empty.setVisible(bool(text.strip()) and shown == 0)
