"""Abrir y guardar documentos en distintos formatos.

Para añadir un formato nuevo: registrar su extensión en READ_EXTS / WRITE_EXTS y
añadir una rama en open_document() / save_document().  Los formatos complejos
(como .docx) viven en isaward/formats/.
"""
from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QByteArray, QMarginsF, QRectF, QSizeF
from PySide6.QtGui import (QColor, QPageLayout, QPageSize, QPainter, QPalette, QTextDocument,
                           QTextDocumentWriter)
from PySide6.QtPrintSupport import QPrinter

from PySide6.QtGui import QAbstractTextDocumentLayout

from .formats.doc_io import DocError, doc_to_html
from .formats.docx_io import html_to_docx, read_docx
from .formats.odt_io import read_odt
from .formats.pdf_io import PdfError, read_pdf
from .formats.rtf_io import html_to_rtf, read_rtf
from .pagedraw import paint_header_footer
from .pagesetup import PageSetup
from .formats.sniff import looks_binary, sniff_format

TEXT_EXTS = {".txt", ".text", ".log", ".csv"}
MARKDOWN_EXTS = {".md", ".markdown"}
HTML_EXTS = {".html", ".htm"}
WORD_EXTS = {".docx", ".docm", ".dotx", ".dotm"}
READ_EXTS = WORD_EXTS | {".odt", ".ott", ".rtf", ".doc", ".pdf"} | TEXT_EXTS | MARKDOWN_EXTS | HTML_EXTS
WRITE_EXTS = {".docx", ".odt", ".rtf"} | TEXT_EXTS | MARKDOWN_EXTS | HTML_EXTS

OPEN_FILTER = (
    "Todos los documentos (*.docx *.docm *.dotx *.doc *.odt *.rtf *.pdf *.txt *.text *.log *.csv *.md *.markdown *.html *.htm);;"
    "Documentos de Word (*.docx *.docm *.dotx *.dotm *.doc);;"
    "OpenDocument (*.odt *.ott);;"
    "Texto enriquecido (*.rtf);;"
    "PDF, solo texto (*.pdf);;"
    "Texto sin formato (*.txt *.text *.log *.csv);;"
    "Markdown (*.md *.markdown);;"
    "Páginas web (*.html *.htm);;"
    "Todos los archivos (*)"
)
SAVE_FILTERS = {
    "Documento de Word (*.docx)": ".docx",
    "Texto enriquecido (*.rtf)": ".rtf",
    "OpenDocument (*.odt)": ".odt",
    "Texto sin formato (*.txt)": ".txt",
    "Página web (*.html)": ".html",
    "Markdown (*.md)": ".md",
}


class UserMessage(Exception):
    """Un problema explicado en lenguaje sencillo, listo para mostrarse al usuario."""


def read_text(path: str) -> str:
    raw = Path(path).read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16")
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1")


def open_document(editor, path: str) -> str | None:
    """Abre el archivo en el editor.  Devuelve un aviso si se perdió formato al abrirlo (o None)."""
    ext = Path(path).suffix.lower()
    kind = sniff_format(path)  # el contenido manda sobre la extensión
    try:
        if kind == "docx":
            html, images, page = read_docx(path)
            editor.load_html(html, images, page=page)
        elif kind == "odt":
            html, images, page = read_odt(path)
            editor.load_html(html, images, page=page)
        elif kind == "rtf":
            html, images, page = read_rtf(path)
            editor.load_html(html, images, page=page)
        elif kind == "doc":
            editor.load_html(*doc_to_html(path))
            return ("Este es un Word antiguo (.doc): se abrió solo el texto, sin formato.\n\n"
                    "Para conservar el formato, ábrelo en Word o LibreOffice y guárdalo como .docx.")
        elif kind == "pdf":
            html, images, page = read_pdf(path)
            editor.load_html(html, images, page=page)
            return ("Los PDF se abren solo como texto: no se recuperan las imágenes ni el diseño de la página, "
                    "y los párrafos se reconstruyen a partir de las líneas.\n\nRevisa el resultado antes de usarlo.")
        elif kind == "zip":
            raise UserMessage("Este archivo comprimido no es un documento que IsaWard sepa abrir.")
        elif looks_binary(path):
            raise UserMessage("Este archivo no parece un documento de texto, así que no lo puedo abrir.")
        elif ext in HTML_EXTS:
            editor.load_html(read_text(path), base_dir=os.path.dirname(os.path.abspath(path)))
        elif ext in MARKDOWN_EXTS:
            editor.load_markdown(read_text(path))
        else:
            editor.load_plain(read_text(path))  # .txt y cualquier otro archivo de texto
    except (DocError, PdfError) as err:
        raise UserMessage(str(err)) from err
    return None


def save_document(editor, path: str) -> None:
    ext = Path(path).suffix.lower()
    doc = editor.document()
    if ext == ".docx":
        html, images = editor.html_and_images()
        html_to_docx(html, images, path, editor.page_setup)
    elif ext in HTML_EXTS:
        Path(path).write_text(editor.clean_html(), encoding="utf-8")
    elif ext in MARKDOWN_EXTS:
        Path(path).write_text(doc.toMarkdown(), encoding="utf-8")
    elif ext == ".rtf":
        html, images = editor.html_and_images()
        html_to_rtf(html, images, path, editor.page_setup)
    elif ext == ".odt":
        writer = QTextDocumentWriter(path, QByteArray(b"odf"))
        if not writer.write(doc):
            raise OSError("No se pudo escribir el archivo .odt")
    elif ext in TEXT_EXTS or ext == "":
        Path(path).write_text(doc.toPlainText(), encoding="utf-8")
    else:
        raise UserMessage(f"No se puede guardar en formato «{ext}».")


# ---------------------------------------------------------------- imprimir / PDF
def make_printer(page: PageSetup, pdf_path: str | None = None) -> QPrinter:
    """Impresora (o PDF) con el tamaño y la orientación de la hoja del documento, sin márgenes propios:
    los márgenes ya son parte de la hoja del documento."""
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    short, long_ = sorted((page.width_cm * 10, page.height_cm * 10))  # en milímetros, siempre "en vertical"
    printer.setPageSize(QPageSize(QSizeF(short, long_), QPageSize.Unit.Millimeter))
    printer.setPageOrientation(QPageLayout.Orientation.Landscape if page.landscape
                               else QPageLayout.Orientation.Portrait)
    printer.setPageMargins(QMarginsF(0, 0, 0, 0), QPageLayout.Unit.Millimeter)
    if pdf_path:
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(pdf_path)
    return printer


def print_document(editor, printer: QPrinter) -> None:
    """Imprime el documento tal como se ve: una hoja del editor = una hoja de papel."""
    doc, page = editor.document(), editor.page_setup
    if page.has_decorations():
        _print_with_header_footer(doc, printer, page)
    else:
        doc.print_(printer)  # el documento ya está dividido en hojas: Qt lo imprime tal cual


def _print_with_header_footer(doc: QTextDocument, printer: QPrinter, page: PageSetup) -> None:
    """Igual que QTextDocument.print_, pero dibujando además el encabezado, el pie y los números."""
    layout = doc.documentLayout()
    pages = max(1, layout.pageCount())
    w, h = page.page_px()
    painter = QPainter(printer)
    if not painter.isActive():
        raise OSError("No se pudo iniciar la impresión.")
    try:
        painter.scale(printer.width() / w, printer.height() / h)  # una hoja del documento = una hoja de papel
        for k in range(pages):
            if k:
                printer.newPage()
            painter.save()
            painter.translate(0, -k * h)
            view = QRectF(0, k * h, w, h)
            painter.setClipRect(view)
            context = QAbstractTextDocumentLayout.PaintContext()
            context.clip = view
            palette = context.palette
            palette.setColor(QPalette.ColorRole.Text, QColor("black"))
            context.palette = palette
            layout.draw(painter, context)
            painter.restore()
            paint_header_footer(painter, page, k, pages, 0.0)
    finally:
        painter.end()


def export_pdf(editor, path: str) -> None:
    print_document(editor, make_printer(editor.page_setup, path))
