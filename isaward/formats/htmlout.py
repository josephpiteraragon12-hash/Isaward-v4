"""Piezas comunes para generar el HTML que lee Qt (QTextDocument.setHtml).

Todos los lectores de formatos (docx, odt, rtf, doc, pdf) producen el mismo estilo de HTML:
párrafos con estilos en línea, y un diccionario de formato por trozo de texto con estas claves:
    bold, italic, underline, strike, sup, sub  -> True/False
    font (str), size (puntos), color / bg ("rrggbb" sin #), href (str)
"""
from __future__ import annotations

import html as _html


def esc(text: str) -> str:
    return _html.escape(text, quote=False).replace("\t", "&emsp;")


def span(text_html: str, f: dict) -> str:
    """Envuelve texto ya escapado con el formato f (un <span> y, si hay enlace, un <a>)."""
    css = []
    if f.get("font"):
        css.append(f"font-family:'{f['font']}'")
    if f.get("size"):
        css.append(f"font-size:{f['size']:g}pt")
    if f.get("bold"):
        css.append("font-weight:700")
    if f.get("italic"):
        css.append("font-style:italic")
    deco = [d for k, d in (("underline", "underline"), ("strike", "line-through")) if f.get(k)]
    if deco:
        css.append("text-decoration:" + " ".join(deco))
    if f.get("sup"):
        css.append("vertical-align:super")
    if f.get("sub"):
        css.append("vertical-align:sub")
    if f.get("color"):
        css.append(f"color:#{f['color']}")
    if f.get("bg"):
        css.append(f"background-color:#{f['bg']}")
    out = f'<span style="{"; ".join(css)}">{text_html}</span>' if css else text_html
    if f.get("href"):
        out = f'<a href="{_html.escape(f["href"])}">{out}</a>'
    return out


def para(tag: str, content: str, css: list[str]) -> str:
    return f'<{tag} style="{"; ".join(css)}">{content or "<br/>"}</{tag}>'


def wrap(body: str, font: str | None = None, size: float | None = None) -> str:
    style = ""
    if font:
        style += f"font-family:'{font}'; "
    if size:
        style += f"font-size:{size:g}pt;"
    return f'<html><head><meta charset="utf-8"></head><body style="{style}">{body}</body></html>'


class ListStack:
    """Abre y cierra <ul>/<ol> anidados a medida que llegan elementos de lista planos."""

    def __init__(self, out: list[str]):
        self.out = out
        self.stack: list[list] = []  # [tipo, li_abierto, clave]

    def _close_one(self):
        kind, li_open, _ = self.stack.pop()
        if li_open:
            self.out.append("</li>")
        self.out.append(f"</{kind}>")

    def close_all(self):
        while self.stack:
            self._close_one()

    def open_item(self, kind: str, css_type: str | None, depth: int, key) -> None:
        while len(self.stack) > depth:
            self._close_one()
        if len(self.stack) == depth and (self.stack[-1][0] != kind or self.stack[-1][2] != key):
            self._close_one()
        if len(self.stack) == depth and self.stack[-1][1]:
            self.out.append("</li>")
            self.stack[-1][1] = False
        while len(self.stack) < depth:
            style = f' style="list-style-type: {css_type}"' if css_type and len(self.stack) == depth - 1 else ""
            self.out.append(f"<{kind}{style}>")
            self.stack.append([kind, False, key])
        self.out.append("<li>")
        self.stack[-1][1] = True
