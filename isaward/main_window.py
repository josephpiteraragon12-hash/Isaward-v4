"""Ventana principal de IsaWard."""
from __future__ import annotations

import json
import os
from pathlib import Path

from PySide6.QtCore import QSettings, QSize, QStandardPaths, Qt, QTimer
from PySide6.QtGui import (QAction, QActionGroup, QColor, QFont, QIcon, QKeySequence, QPixmap, QTextCharFormat,
                           QTextListFormat)
from PySide6.QtPrintSupport import QPrintDialog, QPrintPreviewDialog
from PySide6.QtWidgets import (QApplication, QColorDialog, QComboBox, QFileDialog, QFontComboBox, QHBoxLayout,
                               QInputDialog, QLabel, QMainWindow, QMenu, QMessageBox, QToolBar, QToolButton,
                               QWidget)

from . import __version__
from .config import AUTOSAVE_MS, DEFAULT_FONT, DEFAULT_SIZE, FONT_SIZES
from .dialogs import (DateDialog, FindReplaceDialog, GuideDialog, HeaderFooterDialog, PageSetupDialog,
                      ParagraphDialog, SymbolDialog, TableDialog)
from .editor import PARAGRAPH_STYLES, PageEditor
from .fileio import (OPEN_FILTER, SAVE_FILTERS, UserMessage, WRITE_EXTS, export_pdf, make_printer,
                     open_document, print_document, save_document)
from .icons import make_icon
from .pagesetup import PageSetup
from .recent import add_recent, only_existing
from .recovery import clear_recovery, read_recovery, write_recovery
from .tools import NATIVE_SHORTCUTS, TOOL_BY_ID, icon_of, shortcut_text

TEXT_COLORS = [("Negro", "#000000"), ("Gris", "#595959"), ("Rojo", "#D64545"), ("Naranja", "#E8833A"),
               ("Verde", "#2E8B57"), ("Azul", "#2F6FDE"), ("Morado", "#7B4FC9")]
HIGHLIGHT_COLORS = [("Amarillo", "#FFF176"), ("Verde", "#B9F6CA"), ("Celeste", "#B2EBF2"),
                    ("Rosa", "#F8BBD0"), ("Naranja", "#FFCC80"), ("Gris", "#E0E0E0")]
LINE_SPACINGS = [("Sencillo (1,0)", 100), ("1,15", 115), ("1,5", 150), ("Doble (2,0)", 200)]
LIST_STYLE = QTextListFormat.Style
# Texto corto de los botones de la fila 3 (los de esa fila muestran su nombre junto al dibujo)
SHORT_TEXT = {"table": "Tabla", "image": "Imagen", "link": "Enlace", "symbol": "Símbolo", "date": "Fecha",
              "hr": "Línea", "page_break": "Salto de página", "new_page": "Hoja en blanco",
              "page_setup": "Configurar página", "header_footer": "Encabezado y pie", "page_number": "N.º de página"}


class MainWindow(QMainWindow):
    def __init__(self, open_path: str | None = None):
        super().__init__()
        self.path: str | None = None
        self.act: dict[str, QAction] = {}
        self.settings = QSettings("IsaWard", "IsaWard")
        self.find_dialog: FindReplaceDialog | None = None
        app_data = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation) \
            or str(Path.home() / ".isaward")
        self.recovery_dir = str(Path(app_data) / "recovery")

        self.editor = PageEditor()
        self.editor.default_page = self._default_page()
        self.editor.fresh_document()  # el primer documento nace con la hoja predeterminada
        self._build_central()
        self._build_actions()
        self._build_menus()
        self._build_toolbars()
        self._build_statusbar()
        self._connect_signals()

        self.setWindowIcon(make_icon("app"))
        self.setAcceptDrops(True)
        self.resize(1100, 760)
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        self._refresh_title()
        self._sync_state()
        self._update_counts()
        self.editor.setFocus()
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setInterval(AUTOSAVE_MS)
        self._autosave_timer.timeout.connect(self._autosave)
        self._autosave_timer.start()
        QTimer.singleShot(0, lambda: self._startup(open_path))

    # ================================================================== construcción
    def _build_central(self) -> None:
        holder = QWidget()
        holder.setObjectName("canvas")
        holder.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QHBoxLayout(holder)
        layout.setContentsMargins(0, 14, 0, 0)
        layout.addStretch(1)
        layout.addWidget(self.editor, 1000)
        layout.addStretch(1)
        self.setCentralWidget(holder)

    def _act(self, tid: str, slot, checkable: bool = False) -> QAction:
        tool = TOOL_BY_ID[tid]
        if icon_of(tool) == "menu":  # funciones que solo están en menús: sin dibujo
            action = QAction(tool.label, self)
        else:
            action = QAction(make_icon(icon_of(tool)), tool.label, self)
        action.setIconText(SHORT_TEXT.get(tid, tool.label))
        shortcut = f"  ({shortcut_text(tool.shortcut)})" if tool.shortcut else ""
        action.setToolTip(f"{tool.label}{shortcut}\n{tool.help}")
        action.setStatusTip(tool.help)
        if tool.shortcut and tid not in NATIVE_SHORTCUTS:
            action.setShortcut(QKeySequence(tool.shortcut))
        action.setCheckable(checkable)
        if checkable:
            action.triggered.connect(lambda checked=False, f=slot: f(checked))
        else:
            action.triggered.connect(lambda _=False, f=slot: f())
        self.act[tid] = action
        return action

    def _build_actions(self) -> None:
        e = self.editor
        # Archivo
        self._act("new", self.new_document)
        self._act("open", self.open_dialog)
        self._act("save", self.save)
        self._act("save_as", self.save_as)
        self._act("pdf", self.export_pdf)
        self._act("preview", self.print_preview)
        self._act("print", self.print_doc)
        # Edición
        self._act("undo", e.undo)
        self._act("redo", e.redo)
        self._act("cut", e.cut)
        self._act("copy", e.copy)
        self._act("paste", e.paste)
        self._act("find", self.show_find)
        self._act("replace", self.show_find)
        self._act("select_all", e.selectAll)
        self._act("quit", self.close)
        # Fuente
        self._act("bold", e.set_bold, True)
        self._act("italic", e.set_italic, True)
        self._act("underline", e.set_underline, True)
        self._act("strike", e.set_strike, True)
        self._act("sub", lambda on: e.set_script("sub" if on else None), True)
        self._act("sup", lambda on: e.set_script("sup" if on else None), True)
        self._act("clear_format", e.clear_formatting)
        # Párrafo
        group = QActionGroup(self)
        group.setExclusive(True)
        for kind in ("left", "center", "right", "justify"):
            action = self._act(f"align_{kind}", lambda _on, k=kind: e.set_align(k), True)
            group.addAction(action)
        self._act("bullets", lambda _on: e.toggle_list(LIST_STYLE.ListDisc), True)
        self._act("numbering", lambda _on: e.toggle_list(LIST_STYLE.ListDecimal), True)
        self._act("indent_less", lambda: e.change_indent(-1))
        self._act("indent_more", lambda: e.change_indent(1))
        self._act("paragraph", self.show_paragraph)
        # Insertar
        self._act("table", self.insert_table)
        self._act("image", self.insert_image)
        self._act("link", self.insert_link)
        self._act("symbol", self.show_symbols)
        self._act("date", self.show_date)
        self._act("hr", e.insert_rule)
        # Hoja y páginas
        self._act("page_break", e.insert_page_break)
        self._act("new_page", e.insert_blank_page)
        self._act("page_setup", self.show_page_setup)
        self._act("header_footer", lambda: self.show_header_footer(False))
        self._act("page_number", lambda: self.show_header_footer(True))
        # Tabla
        self._act("table_row_add", lambda: e.table_add_row(True))
        self._act("table_row_above", lambda: e.table_add_row(False))
        self._act("table_col_add", lambda: e.table_add_column(True))
        self._act("table_col_left", lambda: e.table_add_column(False))
        self._act("table_row_del", e.table_delete_row)
        self._act("table_col_del", e.table_delete_column)
        self._act("table_merge", e.table_merge_cells)
        self._act("table_del", e.table_delete)
        # Ayuda
        self._act("help", lambda: self.show_guide())
        self._act("about", self.show_about)

        self.table_actions = [self.act[t] for t in ("table_row_add", "table_row_above", "table_col_add",
                                                    "table_col_left", "table_row_del", "table_col_del",
                                                    "table_merge", "table_del")]

    def _color_menu(self, colors, apply, none_label: str) -> QMenu:
        menu = QMenu(self)
        for name, hex_value in colors:
            swatch = QPixmap(16, 16)
            swatch.fill(QColor(hex_value))
            action = menu.addAction(QIcon(swatch), name)
            action.triggered.connect(lambda _=False, h=hex_value: apply(QColor(h)))
        menu.addSeparator()
        menu.addAction("Más colores…").triggered.connect(lambda _=False: self._pick_color(apply))
        menu.addAction(none_label).triggered.connect(lambda _=False: apply(None))
        return menu

    def _pick_color(self, apply) -> None:
        color = QColorDialog.getColor(QColor("#000000"), self, "Elegir color")
        if color.isValid():
            apply(color)
            self.editor.setFocus()

    def _spacing_menu(self) -> QMenu:
        menu = QMenu(self)
        for name, percent in LINE_SPACINGS:
            menu.addAction(name).triggered.connect(lambda _=False, p=percent: self.editor.set_line_spacing(p))
        return menu

    def _menu_button(self, tid: str, menu: QMenu) -> QToolButton:
        tool = TOOL_BY_ID[tid]
        button = QToolButton(self)
        button.setIcon(make_icon(tid))
        shortcut = f"  ({shortcut_text(tool.shortcut)})" if tool.shortcut else ""
        button.setToolTip(f"{tool.label}{shortcut}\n{tool.help}")
        button.setStatusTip(tool.help)
        button.setMenu(menu)
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        return button

    def _build_menus(self) -> None:
        bar = self.menuBar()
        a = self.act

        m = bar.addMenu("&Archivo")
        m.addAction(a["new"])
        m.addAction(a["open"])
        self.recent_menu = m.addMenu("Abrir reciente")
        self.recent_menu.aboutToShow.connect(self._fill_recent_menu)
        m.addAction(a["save"])
        m.addAction(a["save_as"])
        m.addSeparator()
        for tid in ("pdf", "preview", "print"):
            m.addAction(a[tid])
        m.addSeparator()
        m.addAction(a["quit"])

        m = bar.addMenu("&Editar")
        for tid in ("undo", "redo"):
            m.addAction(a[tid])
        m.addSeparator()
        for tid in ("cut", "copy", "paste", "select_all"):
            m.addAction(a[tid])
        m.addSeparator()
        m.addAction(a["find"])
        m.addAction(a["replace"])

        m = bar.addMenu("&Insertar")
        for tid in ("table", "image", "link", "symbol", "date", "hr"):
            m.addAction(a[tid])
        m.addSeparator()
        for tid in ("page_break", "new_page"):
            m.addAction(a[tid])

        m = bar.addMenu("F&ormato")
        for tid in ("bold", "italic", "underline", "strike", "sub", "sup", "clear_format"):
            m.addAction(a[tid])
        m.addSeparator()
        for kind in ("left", "center", "right", "justify"):
            m.addAction(a[f"align_{kind}"])
        m.addSeparator()
        for tid in ("bullets", "numbering", "indent_less", "indent_more"):
            m.addAction(a[tid])
        spacing = m.addMenu(make_icon("line_spacing"), "Interlineado")
        for name, percent in LINE_SPACINGS:
            spacing.addAction(name).triggered.connect(lambda _=False, p=percent: self.editor.set_line_spacing(p))
        m.addAction(a["paragraph"])

        m = bar.addMenu("&Hoja")
        for tid in ("page_setup", "header_footer", "page_number"):
            m.addAction(a[tid])
        m.addSeparator()
        for tid in ("page_break", "new_page"):
            m.addAction(a[tid])

        self.table_menu = bar.addMenu("&Tabla")
        for action in self.table_actions:
            self.table_menu.addAction(action)

        m = bar.addMenu("A&yuda")
        m.addAction(a["help"])
        m.addAction("¿Cómo hago…?").triggered.connect(lambda _=False: self.show_guide(tab=1))
        m.addAction("Atajos de teclado").triggered.connect(lambda _=False: self.show_guide(tab=2))
        m.addSeparator()
        m.addAction(a["about"])

    def _build_toolbars(self) -> None:
        a, e = self.act, self.editor

        def toolbar(title: str) -> QToolBar:
            tb = QToolBar(title, self)
            tb.setMovable(False)
            tb.setFloatable(False)
            tb.setIconSize(QSize(22, 22))
            tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
            return tb

        # Fila 1: archivo y edición
        tb1 = toolbar("Archivo y edición")
        for tid in ("new", "open", "save", "pdf", "print"):
            tb1.addAction(a[tid])
        tb1.addSeparator()
        for tid in ("undo", "redo"):
            tb1.addAction(a[tid])
        tb1.addSeparator()
        for tid in ("cut", "copy", "paste"):
            tb1.addAction(a[tid])
        tb1.addSeparator()
        tb1.addAction(a["find"])
        tb1.addSeparator()
        tb1.addAction(a["help"])
        self.addToolBar(tb1)
        self.addToolBarBreak()

        # Fila 2: formato
        tb2 = toolbar("Formato")
        self.style_combo = QComboBox()
        self.style_combo.addItems([s[0] for s in PARAGRAPH_STYLES])
        self.style_combo.setFixedWidth(100)
        self.style_combo.setToolTip("Estilo del párrafo\nElige Normal o un nivel de título.\n(Más información: tecla F1)")
        self.style_combo.activated.connect(self._on_style)
        tb2.addWidget(self.style_combo)

        self.font_combo = QFontComboBox()
        self.font_combo.setFixedWidth(170)
        self.font_combo.setToolTip("Fuente\nCambia el tipo de letra.")
        self.font_combo.textActivated.connect(self._on_font)
        tb2.addWidget(self.font_combo)

        self.size_combo = QComboBox()
        self.size_combo.setEditable(True)
        self.size_combo.addItems([f"{s:g}" for s in FONT_SIZES])
        self.size_combo.setFixedWidth(64)
        self.size_combo.setToolTip("Tamaño de letra\nElige uno de la lista o escribe el que quieras.")
        self.size_combo.textActivated.connect(self._on_size)
        tb2.addWidget(self.size_combo)
        tb2.addSeparator()

        for tid in ("bold", "italic", "underline", "strike", "sub", "sup"):
            tb2.addAction(a[tid])
        tb2.addWidget(self._menu_button("font_color", self._color_menu(TEXT_COLORS, e.set_text_color, "Automático (negro)")))
        tb2.addWidget(self._menu_button("highlight", self._color_menu(HIGHLIGHT_COLORS, e.set_highlight, "Sin resaltado")))
        tb2.addAction(a["clear_format"])
        tb2.addSeparator()

        for tid in ("align_left", "align_center", "align_right", "align_justify"):
            tb2.addAction(a[tid])
        tb2.addSeparator()
        for tid in ("bullets", "numbering", "indent_less", "indent_more"):
            tb2.addAction(a[tid])
        tb2.addWidget(self._menu_button("line_spacing", self._spacing_menu()))
        tb2.addAction(a["paragraph"])
        self.addToolBar(tb2)
        self.addToolBarBreak()

        # Fila 3: insertar y hoja (con el nombre junto al dibujo, para que se entienda sin adivinar)
        tb3 = toolbar("Insertar y hoja")
        tb3.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        for tid in ("table", "image", "link", "symbol", "date", "hr"):
            tb3.addAction(a[tid])
        tb3.addSeparator()
        for tid in ("page_break", "new_page", "page_setup", "header_footer", "page_number"):
            tb3.addAction(a[tid])
        self.addToolBar(tb3)

    def _build_statusbar(self) -> None:
        self.page_label = QLabel("")
        self.count_label = QLabel("")
        self.statusBar().addPermanentWidget(self.page_label)
        self.statusBar().addPermanentWidget(self.count_label)
        self.statusBar().showMessage("Listo.", 3000)
        self._count_timer = QTimer(self)
        self._count_timer.setSingleShot(True)
        self._count_timer.setInterval(300)
        self._count_timer.timeout.connect(self._update_counts)

    def _connect_signals(self) -> None:
        e = self.editor
        e.modified_changed.connect(lambda _m: self._refresh_title())
        e.content_changed.connect(self._count_timer.start)
        e.currentCharFormatChanged.connect(lambda _f: self._sync_state())
        e.cursorPositionChanged.connect(self._sync_state)
        e.file_dropped.connect(self.open_path)
        e.page_count_changed.connect(lambda _n: self._update_page_label())

    # ================================================================== estado visible
    def _sync_state(self) -> None:
        e, a = self.editor, self.act
        fmt = e.currentCharFormat()
        a["bold"].setChecked(fmt.fontWeight() >= 600)
        a["italic"].setChecked(fmt.fontItalic())
        a["underline"].setChecked(fmt.fontUnderline())
        a["strike"].setChecked(fmt.fontStrikeOut())
        va = fmt.verticalAlignment()
        a["sub"].setChecked(va == QTextCharFormat.VerticalAlignment.AlignSubScript)
        a["sup"].setChecked(va == QTextCharFormat.VerticalAlignment.AlignSuperScript)

        families = fmt.fontFamilies()
        family = families[0] if isinstance(families, (list, tuple)) and families else None
        family = family or e.document().defaultFont().family() or DEFAULT_FONT
        size = fmt.fontPointSize() or e.document().defaultFont().pointSizeF() or DEFAULT_SIZE
        for widget in (self.font_combo, self.size_combo, self.style_combo):
            widget.blockSignals(True)
        self.font_combo.setCurrentFont(QFont(family))
        self.size_combo.setEditText(f"{size:g}")
        cursor = e.textCursor()
        level = cursor.blockFormat().headingLevel()
        self.style_combo.setCurrentIndex(level if 0 <= level < len(PARAGRAPH_STYLES) else 0)
        for widget in (self.font_combo, self.size_combo, self.style_combo):
            widget.blockSignals(False)

        flags = e.alignment()
        if flags & Qt.AlignmentFlag.AlignHCenter:
            align = "center"
        elif flags & Qt.AlignmentFlag.AlignRight:
            align = "right"
        elif flags & Qt.AlignmentFlag.AlignJustify:
            align = "justify"
        else:
            align = "left"
        a[f"align_{align}"].setChecked(True)

        current_list = cursor.currentList()
        style = current_list.format().style() if current_list is not None else None
        a["bullets"].setChecked(style == LIST_STYLE.ListDisc)
        a["numbering"].setChecked(style == LIST_STYLE.ListDecimal)

        in_table = cursor.currentTable() is not None
        for action in self.table_actions:
            action.setEnabled(in_table)
        self._update_page_label()

    def _update_page_label(self) -> None:
        e, ps = self.editor, self.editor.page_setup
        orientation = "horizontal" if ps.landscape else "vertical"
        self.page_label.setText(f"Página {e.current_page()} de {e.page_count()}   ·   Hoja {ps.size_name()} {orientation}    ")

    def _update_counts(self) -> None:
        text = self.editor.toPlainText()
        words = len(text.split())
        chars = len(text.replace("\n", ""))
        self.count_label.setText(f"Palabras: {words}    Caracteres: {chars}  ")

    def _refresh_title(self) -> None:
        name = Path(self.path).name if self.path else "Documento sin título"
        star = "*" if self.editor.document().isModified() else ""
        self.setWindowTitle(f"{star}{name} — IsaWard")

    # ================================================================== combos
    def _on_style(self, index: int) -> None:
        self.editor.apply_paragraph_style(index)
        self.editor.setFocus()

    def _on_font(self, family: str) -> None:
        self.editor.set_font_family(family)
        self.editor.setFocus()

    def _on_size(self, text: str) -> None:
        try:
            self.editor.set_font_size(float(text.replace(",", ".")))
        except ValueError:
            pass
        self.editor.setFocus()

    # ================================================================== archivo
    def _last_dir(self) -> str:
        return self.settings.value("last_dir", str(Path.home()))

    def _remember_dir(self, path: str) -> None:
        self.settings.setValue("last_dir", os.path.dirname(path))

    def _ask_save_changes(self) -> bool:
        """True si se puede continuar (se guardó, se descartó o no había cambios)."""
        if not self.editor.document().isModified():
            return True
        name = Path(self.path).name if self.path else "Documento sin título"
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowTitle("IsaWard")
        box.setText(f"¿Quieres guardar los cambios de «{name}»?")
        box.setInformativeText("Si no los guardas, se perderán.")
        b_save = box.addButton("Guardar", QMessageBox.ButtonRole.AcceptRole)
        b_discard = box.addButton("No guardar", QMessageBox.ButtonRole.DestructiveRole)
        box.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(b_save)
        box.exec()
        clicked = box.clickedButton()
        if clicked is b_save:
            return self.save()
        return clicked is b_discard

    def new_document(self) -> None:
        if self._ask_save_changes():
            self.editor.fresh_document()
            self.path = None
            clear_recovery(self.recovery_dir)
            self._refresh_title()
            self._count_timer.start()
            self.editor.setFocus()

    def open_dialog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Abrir documento", self._last_dir(), OPEN_FILTER)
        if path:
            self.open_path(path)

    def open_path(self, path: str) -> None:
        if not self._ask_save_changes():
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            notice = open_document(self.editor, path)
        except UserMessage as err:
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self, "No se pudo abrir el archivo", str(err))
            return
        except Exception as err:  # archivo dañado, sin permiso, etc.
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "No se pudo abrir el archivo",
                                 f"No pude abrir «{Path(path).name}».\n\nDetalle: {err}")
            return
        QApplication.restoreOverrideCursor()
        ext = Path(path).suffix.lower()
        self.path = path if ext in WRITE_EXTS else None  # si no se puede guardar igual, se pedirá otro nombre
        if self.path is None:
            self.editor.document().setModified(True)
        clear_recovery(self.recovery_dir)
        self._remember_dir(path)
        self._remember_recent(path)
        self._refresh_title()
        self._sync_state()
        self._count_timer.start()
        self.statusBar().showMessage(f"Abierto: {path}", 4000)
        if notice:
            QMessageBox.information(self, "Documento abierto con cambios", notice)

    def save(self) -> bool:
        if not self.path or Path(self.path).suffix.lower() not in WRITE_EXTS:
            return self.save_as()
        return self._write(self.path)

    def save_as(self) -> bool:
        suggested = self.path or str(Path(self._last_dir()) / "Documento.docx")
        filters = ";;".join(SAVE_FILTERS)
        current_ext = Path(suggested).suffix.lower()
        selected = next((f for f, ext in SAVE_FILTERS.items() if ext == current_ext), list(SAVE_FILTERS)[0])
        path, chosen = QFileDialog.getSaveFileName(self, "Guardar como", suggested, filters, selected)
        if not path:
            return False
        if not Path(path).suffix:
            path += SAVE_FILTERS.get(chosen, ".docx")
        ext = Path(path).suffix.lower()
        if ext == ".txt" and not self._confirm_plain_text():
            return False
        return self._write(path)

    def _confirm_plain_text(self) -> bool:
        answer = QMessageBox.question(
            self, "Guardar como texto", "El formato de texto sin formato no guarda negritas, colores, "
            "imágenes ni tablas.\n\n¿Guardar de todos modos?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        return answer == QMessageBox.StandardButton.Yes

    def _write(self, path: str) -> bool:
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            save_document(self.editor, path)
        except Exception as err:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "No se pudo guardar",
                                 f"No pude guardar «{Path(path).name}».\n\nDetalle: {err}\n\n"
                                 "Revisa que el archivo no esté abierto en otro programa y que tengas permiso en esa carpeta.")
            return False
        QApplication.restoreOverrideCursor()
        self.path = path
        self.editor.document().setModified(False)
        clear_recovery(self.recovery_dir)
        self._remember_dir(path)
        self._remember_recent(path)
        self._refresh_title()
        self.statusBar().showMessage(f"Guardado: {path}", 4000)
        return True

    def export_pdf(self) -> None:
        base = Path(self.path).with_suffix(".pdf").name if self.path else "Documento.pdf"
        path, _ = QFileDialog.getSaveFileName(self, "Exportar a PDF", str(Path(self._last_dir()) / base), "PDF (*.pdf)")
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        try:
            export_pdf(self.editor, path)
        except Exception as err:
            QMessageBox.critical(self, "No se pudo exportar", f"Detalle: {err}")
            return
        self.statusBar().showMessage(f"PDF creado: {path}", 4000)

    def print_doc(self) -> None:
        printer = make_printer(self.editor.page_setup)
        dialog = QPrintDialog(printer, self)
        if dialog.exec():
            print_document(self.editor, printer)

    def print_preview(self) -> None:
        printer = make_printer(self.editor.page_setup)
        dialog = QPrintPreviewDialog(printer, self)
        dialog.paintRequested.connect(lambda p: print_document(self.editor, p))
        dialog.resize(900, 700)
        dialog.exec()

    # ================================================================== recientes
    def _recent_list(self) -> list[str]:
        value = self.settings.value("recent", [])
        if isinstance(value, str):
            value = [value]
        return [str(v) for v in (value or [])]

    def _remember_recent(self, path: str) -> None:
        self.settings.setValue("recent", add_recent(self._recent_list(), path))

    def _fill_recent_menu(self) -> None:
        menu = self.recent_menu
        menu.clear()
        items = only_existing(self._recent_list())
        if not items:
            menu.addAction("(todavía no hay archivos)").setEnabled(False)
            return
        for path in items:
            action = menu.addAction(Path(path).name)
            action.setStatusTip(path)
            action.triggered.connect(lambda _=False, p=path: self.open_path(p))
        menu.addSeparator()
        menu.addAction("Borrar la lista").triggered.connect(lambda _=False: self.settings.setValue("recent", []))

    # ================================================================== copia automática y recuperación
    def _autosave(self) -> None:
        if not self.editor.document().isModified():
            return
        try:
            name = Path(self.path).name if self.path else "Documento sin título"
            html, images = self.editor.html_and_images()
            write_recovery(self.recovery_dir, html, images, self.path, name, self.editor.page_setup.to_dict())
        except Exception:
            pass  # la copia automática nunca debe molestar ni cerrar el programa

    def _startup(self, open_path: str | None) -> None:
        self._offer_recovery()
        if open_path:
            self.open_path(open_path)

    def _offer_recovery(self) -> None:
        data = read_recovery(self.recovery_dir)
        if data is None:
            return
        html, images, meta = data
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowTitle("IsaWard")
        box.setText(f"IsaWard se cerró sin guardar «{meta.get('title') or 'Documento sin título'}».")
        box.setInformativeText(f"Encontré una copia automática de las {meta.get('saved', '')}. ¿Quieres recuperarla?")
        b_recover = box.addButton("Recuperar", QMessageBox.ButtonRole.AcceptRole)
        box.addButton("Descartar", QMessageBox.ButtonRole.DestructiveRole)
        box.setDefaultButton(b_recover)
        box.exec()
        if box.clickedButton() is not b_recover:
            clear_recovery(self.recovery_dir)
            return
        self.editor.load_html(html, images, page=PageSetup.from_dict(meta.get("page")))
        self.editor.document().setModified(True)
        original = meta.get("original")
        self.path = original if original and Path(original).suffix.lower() in WRITE_EXTS else None
        self._refresh_title()
        self._sync_state()
        self._count_timer.start()
        self.statusBar().showMessage("Documento recuperado. Guárdalo para no perderlo otra vez.", 6000)

    # ================================================================== insertar y otros diálogos
    def insert_table(self) -> None:
        dialog = TableDialog(self)
        if dialog.exec():
            self.editor.insert_table(dialog.rows.value(), dialog.cols.value())

    def insert_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Insertar imagen", self._last_dir(),
                                              "Imágenes (*.png *.jpg *.jpeg *.bmp *.gif);;Todos los archivos (*)")
        if path and not self.editor.insert_image_file(path):
            QMessageBox.warning(self, "Imagen no válida", "No pude leer esa imagen. Prueba con un archivo PNG o JPG.")

    def insert_link(self) -> None:
        url, ok = QInputDialog.getText(self, "Insertar enlace", "Dirección web:", text="https://")
        if ok and url.strip() and url.strip() != "https://":
            self.editor.insert_link(url.strip())

    def show_find(self) -> None:
        if self.find_dialog is None:
            self.find_dialog = FindReplaceDialog(self.editor, self)
        self.find_dialog.open_for_selection()

    def show_guide(self, tab: int = 0, tool_id: str | None = None) -> None:
        GuideDialog(self, tab=tab, tool_id=tool_id).exec()

    def show_page_setup(self) -> None:
        dialog = PageSetupDialog(self, self.editor.page_setup)
        if not dialog.exec():
            return
        page = dialog.result_page()
        if dialog.as_default():
            self.settings.setValue("default_page", json.dumps(page.to_dict()))
            self.editor.default_page = page
        self.editor.set_page_setup(page)
        self._update_page_label()
        self.statusBar().showMessage("La hoja se actualizó.", 4000)

    def show_header_footer(self, numbers: bool = False) -> None:
        dialog = HeaderFooterDialog(self, self.editor.page_setup, focus_numbers=numbers)
        if dialog.exec():
            self.editor.set_page_setup(dialog.result_page())
            self.statusBar().showMessage("Encabezado y pie actualizados.", 4000)

    def show_paragraph(self) -> None:
        dialog = ParagraphDialog(self, self.editor.paragraph_values())
        if dialog.exec():
            self.editor.apply_paragraph_values(**dialog.values())
        self.editor.setFocus()

    def show_symbols(self) -> None:
        if getattr(self, "_symbol_dialog", None) is None:
            self._symbol_dialog = SymbolDialog(self, self.editor.insert_text)
        self._symbol_dialog.show()
        self._symbol_dialog.raise_()

    def show_date(self) -> None:
        dialog = DateDialog(self)
        if dialog.exec() and dialog.chosen():
            self.editor.insert_text(dialog.chosen())
        self.editor.setFocus()

    def _default_page(self) -> PageSetup:
        """Hoja de los documentos nuevos (la que guardó el usuario o A4)."""
        try:
            return PageSetup.from_dict(json.loads(self.settings.value("default_page", "") or "{}"))
        except (TypeError, ValueError):
            return PageSetup()

    def show_about(self) -> None:
        QMessageBox.about(
            self, "Acerca de IsaWard",
            f"<b>IsaWard {__version__}</b><br>Un procesador de texto sencillo y ligero, "
            "hecho para PCs de pocos recursos.<br><br>Código abierto (licencia MIT).")

    # ================================================================== eventos de la ventana
    def closeEvent(self, event) -> None:
        if self._ask_save_changes():
            self.settings.setValue("geometry", self.saveGeometry())
            clear_recovery(self.recovery_dir)
            event.accept()
        else:
            event.ignore()

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        for url in event.mimeData().urls():
            if url.isLocalFile():
                self.open_path(url.toLocalFile())
                break
