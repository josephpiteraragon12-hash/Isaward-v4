"""Lector de PDF a HTML (solo texto).  No usa Qt; necesita la librería pypdf.

    html, imagenes = pdf_to_html("informe.pdf")

Un PDF es un "dibujo" de la página, no un documento editable, así que solo se recupera el texto:
se rearman los párrafos a partir de las líneas, se reconocen viñetas y listas numeradas, y se
descartan los números de página.  No se recuperan imágenes, columnas ni tablas con su diseño.
Los PDF escaneados (fotos de hojas) no tienen texto y no se pueden leer.
"""
from __future__ import annotations

import re

from ..pagesetup import PageSetup, from_points
from .htmlout import esc, para, wrap


class PdfError(Exception):
    pass


_BULLET = re.compile(r"^[\uf0b7\u2022\u00b7\u25cf\u25aa\u2013\-*]\s+")
_NUMBERED = re.compile(r"^\d{1,2}[.)]\s+")
_END_PUNCT = (".", "!", "?", ":", "…", "”", '"', "»")


def pdf_to_html(path: str) -> tuple[str, dict[str, bytes]]:
    html, images, _ = read_pdf(path)
    return html, images


def read_pdf(path: str) -> tuple[str, dict[str, bytes], PageSetup]:
    """Devuelve (html, imagenes, hoja): la hoja toma el tamaño de la primera página del PDF."""
    try:
        from pypdf import PdfReader
    except ImportError as err:
        raise PdfError("Falta la librería pypdf para leer PDF (pip install pypdf).") from err
    try:
        reader = PdfReader(path)
        if reader.is_encrypted and not reader.decrypt(""):
            raise PdfError("Este PDF está protegido con contraseña.")
        pages = [(page.extract_text() or "") for page in reader.pages]
        box = reader.pages[0].mediabox
        page_setup = from_points(float(box.width), float(box.height))
    except PdfError:
        raise
    except Exception as err:
        raise PdfError(f"No pude leer este PDF (puede estar dañado o protegido). Detalle: {err}") from err
    if sum(len(p.strip()) for p in pages) < 20:
        raise PdfError("Este PDF parece ser una imagen escaneada: no tiene texto que IsaWard pueda leer.")
    return wrap(_pages_to_html(pages)), {}, page_setup


def _clean_line(line: str) -> str:
    line = re.sub("[\uf000-\uf0ff]", lambda m: "•" if m.group() == "\uf0b7" else "", line)
    return line.replace("\u00ad", "").rstrip()


def _pages_to_html(pages: list[str]) -> str:
    lines: list[str] = []
    for text in pages:
        page_lines = [_clean_line(x) for x in text.splitlines()]
        page_lines = [x for x in page_lines if x.strip()]
        for idx in (-1, 0):  # números de página sueltos al principio o al final
            if page_lines and re.fullmatch(r"\s*(página\s*)?\d{1,4}(\s*de\s*\d{1,4})?\s*", page_lines[idx], re.I):
                page_lines.pop(idx)
        lines.extend(page_lines)
    if not lines:
        return ""
    lengths = sorted(len(x) for x in lines)
    full = lengths[int(len(lengths) * 0.9)] or 1  # largo "de línea completa" en este documento

    paragraphs: list[tuple[str, str]] = []  # (tipo, texto) con tipo p / ul / ol
    for line in lines:
        text = line.strip()
        kind = "p"
        if _BULLET.match(text) and len(text) > 2:
            kind, text = "ul", _BULLET.sub("", text, count=1)
        elif _NUMBERED.match(text):
            kind, text = "ol", _NUMBERED.sub("", text, count=1)
        if kind == "p" and paragraphs and paragraphs[-1][0] == "p" and _continues(paragraphs[-1][1], text, full):
            prev = paragraphs[-1][1]
            joiner = "" if prev.endswith("-") and len(prev) > 1 and prev[-2].isalpha() and text[:1].islower() else " "
            paragraphs[-1] = ("p", (prev[:-1] if joiner == "" else prev) + joiner + text)
        else:
            paragraphs.append((kind, text))

    html: list[str] = []
    open_list = None
    css = ["white-space:pre-wrap", "margin-top:0px", "margin-bottom:8px"]
    for kind, text in paragraphs:
        if kind == "p":
            if open_list:
                html.append(f"</{open_list}>")
                open_list = None
            html.append(para("p", esc(text), css))
        else:
            if open_list != kind:
                if open_list:
                    html.append(f"</{open_list}>")
                html.append(f"<{kind}>")
                open_list = kind
            html.append(f"<li>{esc(text)}</li>")
    if open_list:
        html.append(f"</{open_list}>")
    return "".join(html)


def _continues(prev: str, nxt: str, full: int) -> bool:
    """¿La línea siguiente sigue el mismo párrafo que la anterior?"""
    if len(prev) >= 0.6 * full and nxt[:1].islower():
        return True
    if len(prev) >= 0.95 * full and not prev.endswith(_END_PUNCT):
        return True
    return False
