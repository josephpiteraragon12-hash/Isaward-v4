"""Lector de ODT (OpenDocument Texto, de LibreOffice/OpenOffice) a HTML.  No usa Qt.

    html, imagenes = odt_to_html("carta.odt")

Se conserva: negrita, cursiva, subrayado, tachado, sub/superíndice, fuente, tamaño, color,
resaltado, alineación, sangrías, espaciado, títulos, listas (viñetas y numeradas), tablas con
celdas combinadas, imágenes, enlaces y saltos de página.
No se conserva todavía: encabezados/pies, notas al pie, cuadros de texto, formas.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
import zipfile

from ..pagesetup import PageSetup, split_slots
from .htmlout import esc, para, span, wrap

NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "draw": "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",
    "fo": "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0",
    "svg": "urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0",
    "xlink": "http://www.w3.org/1999/xlink",
}
_NUM_CSS = {"1": "decimal", "a": "lower-alpha", "A": "upper-alpha", "i": "lower-roman", "I": "upper-roman"}
_IMG_EXT = ("png", "jpg", "jpeg", "gif", "bmp")
_CONTAINERS = {"text:section", "text:index-body", "text:table-of-content", "text:alphabetical-index",
               "text:illustration-index", "text:table-index", "text:user-index", "text:bibliography"}
_SKIP_INLINE = {"text:note", "text:soft-page-break", "text:annotation", "office:annotation"}


def q(name: str) -> str:
    prefix, local = name.split(":")
    return "{%s}%s" % (NS[prefix], local)


def _px(value: str | None) -> float | None:
    m = re.fullmatch(r"\s*(-?[\d.]+)\s*(cm|mm|in|pt|px)?\s*", value or "")
    if not m:
        return None
    return float(m.group(1)) * {"cm": 37.7953, "mm": 3.77953, "in": 96, "pt": 4 / 3, "px": 1, None: 1}[m.group(2)]


def _text_props(el) -> dict:
    d: dict = {}
    if el is None:
        return d
    a = el.attrib
    fw = a.get(q("fo:font-weight"))
    if fw:
        d["bold"] = fw == "bold" or (fw.isdigit() and int(fw) >= 600)
    fs = a.get(q("fo:font-style"))
    if fs:
        d["italic"] = fs in ("italic", "oblique")
    us = a.get(q("style:text-underline-style"))
    if us:
        d["underline"] = us != "none"
    ls = a.get(q("style:text-line-through-style"))
    if ls:
        d["strike"] = ls != "none"
    pos = a.get(q("style:text-position"))
    if pos:
        first = pos.split()[0]
        if first == "super" or (first.endswith("%") and float(first[:-1]) > 0):
            d["sup"], d["sub"] = True, False
        elif first == "sub" or (first.endswith("%") and float(first[:-1]) < 0):
            d["sup"], d["sub"] = False, True
        else:
            d["sup"] = d["sub"] = False
    font = a.get(q("style:font-name")) or a.get(q("fo:font-family"))
    if font:
        d["font"] = font.strip("'\"")
    size = a.get(q("fo:font-size"))
    if size and not size.endswith("%"):
        px = _px(size)
        if px:
            d["size"] = round(px * 0.75, 1)
    color = a.get(q("fo:color"))
    if color and color.startswith("#"):
        d["color"] = color[1:].lower()
    bg = a.get(q("fo:background-color"))
    if bg:
        d["bg"] = bg[1:].lower() if bg.startswith("#") else None
    return d


def _para_props(el) -> dict:
    d: dict = {}
    if el is None:
        return d
    a = el.attrib
    align = a.get(q("fo:text-align"))
    if align:
        d["align"] = {"start": "left", "end": "right"}.get(align, align)
    for key, attr in (("left", "fo:margin-left"), ("indent", "fo:text-indent"),
                      ("before", "fo:margin-top"), ("after", "fo:margin-bottom")):
        if a.get(q(attr)) is not None:
            d[key] = _px(a.get(q(attr)))
    lh = a.get(q("fo:line-height"))
    if lh and lh.endswith("%"):
        d["line"] = float(lh[:-1])
    if a.get(q("fo:break-before")) == "page":
        d["break"] = True
    return d


def _cell_props(el) -> dict:
    d: dict = {}
    if el is None:
        return d
    bg = el.get(q("fo:background-color"))
    if bg and bg.startswith("#"):
        d["bg"] = bg[1:].lower()
    for key, value in el.attrib.items():
        if key.startswith("{%s}border" % NS["fo"]) and value.strip() != "none":
            d["border"] = True
    return d


class _Styles:
    def __init__(self):
        self.styles: dict[tuple, dict] = {}
        self.defaults: dict[str, dict] = {}
        self.lists: dict[str, dict] = {}

    def load(self, root) -> None:
        for el in root.iter(q("style:style")):
            self.styles[(el.get(q("style:family")), el.get(q("style:name")))] = {
                "parent": el.get(q("style:parent-style-name")),
                "text": _text_props(el.find(q("style:text-properties"))),
                "para": _para_props(el.find(q("style:paragraph-properties"))),
                "cell": _cell_props(el.find(q("style:table-cell-properties"))),
            }
        for el in root.iter(q("style:default-style")):
            self.defaults[el.get(q("style:family"))] = {
                "text": _text_props(el.find(q("style:text-properties"))),
                "para": _para_props(el.find(q("style:paragraph-properties"))),
            }
        for el in root.iter(q("text:list-style")):
            levels = {}
            for lv in el:
                local = lv.tag.rsplit("}", 1)[-1]
                level = int(lv.get(q("text:level"), "1"))
                if local == "list-level-style-number":
                    levels[level] = ("ol", _NUM_CSS.get(lv.get(q("style:num-format"), "1"), "decimal"))
                elif local in ("list-level-style-bullet", "list-level-style-image"):
                    levels[level] = ("ul", None)
            self.lists[el.get(q("style:name"))] = levels

    def props(self, family: str, name: str | None, kind: str) -> dict:
        """Propiedades de un estilo con las de sus estilos padre (el hijo manda)."""
        chain, seen = [], set()
        while name and (family, name) not in seen and (family, name) in self.styles:
            seen.add((family, name))
            chain.append(self.styles[(family, name)])
            name = self.styles[(family, name)]["parent"]
        merged = dict(self.defaults.get(family, {}).get(kind, {}))
        for st in reversed(chain):
            merged.update(st[kind])
        return merged

    def list_kind(self, name: str | None, depth: int) -> tuple[str, str | None]:
        levels = self.lists.get(name or "", {})
        return levels.get(depth) or levels.get(1) or ("ul", None)


def read_odt(path: str) -> tuple[str, dict[str, bytes], PageSetup]:
    """Lee un .odt y devuelve (html, imagenes, configuración de la hoja)."""
    with zipfile.ZipFile(path) as zf:
        reader = _OdtReader(zf)
        html, images = reader.convert()
        return html, images, reader.page_setup()


def odt_to_html(path: str) -> tuple[str, dict[str, bytes]]:
    html, images, _ = read_odt(path)
    return html, images


class _OdtReader:
    def __init__(self, zf: zipfile.ZipFile):
        self.zf = zf
        self.images: dict[str, bytes] = {}
        self._img_by_href: dict[str, str] = {}
        self.out: list[str] = []
        self.styles = _Styles()
        self.styles_xml = None
        if "styles.xml" in zf.namelist():
            self.styles_xml = ET.fromstring(zf.read("styles.xml"))
            self.styles.load(self.styles_xml)
        self.content = ET.fromstring(zf.read("content.xml"))
        self.styles.load(self.content)
        base = self.styles.defaults.get("paragraph", {}).get("text", {})
        self.base_font, self.base_size = base.get("font"), base.get("size")

    def convert(self):
        body = self.content.find(f"{q('office:body')}/{q('office:text')}")
        if body is not None:
            self._blocks(body)
        return wrap("".join(self.out), self.base_font, self.base_size), self.images

    # ---- hoja, encabezado y pie ----
    def _tokens(self, el) -> str:
        out = [el.text or ""]
        for ch in el:
            if ch.tag == q("text:page-number"):
                out.append("{pagina}")
            elif ch.tag == q("text:page-count"):
                out.append("{paginas}")
            elif ch.tag == q("text:tab"):
                out.append("\t")
            elif ch.tag == q("text:s"):
                out.append(" " * int(ch.get(q("text:c"), "1")))
            else:
                out.append(self._tokens(ch))
            out.append(ch.tail or "")
        return "".join(out)

    def _hf_slots(self, container) -> tuple[str, str, str]:
        if container is None:
            return "", "", ""
        for p in container.iter(q("text:p")):
            text = self._tokens(p)
            if text.strip():
                align = self.styles.props("paragraph", p.get(q("text:style-name")), "para").get("align")
                return split_slots(text, align if align in ("center", "right") else None)
        return "", "", ""

    def page_setup(self) -> PageSetup:
        ps, root = PageSetup(), self.styles_xml
        if root is None:
            return ps
        master = next(iter(root.iter(q("style:master-page"))), None)
        wanted = master.get(q("style:page-layout-name")) if master is not None else None
        layout = None
        for lay in root.iter(q("style:page-layout")):
            if layout is None or lay.get(q("style:name")) == wanted:
                layout = lay
        props = layout.find(q("style:page-layout-properties")) if layout is not None else None
        if props is not None:
            for attr, field in (("fo:page-width", "width_cm"), ("fo:page-height", "height_cm"),
                                ("fo:margin-top", "top_cm"), ("fo:margin-bottom", "bottom_cm"),
                                ("fo:margin-left", "left_cm"), ("fo:margin-right", "right_cm")):
                px = _px(props.get(q(attr)))
                if px is not None:
                    setattr(ps, field, round(px / 37.7953, 2))
        if master is not None and layout is not None:  # el margen real del texto incluye la altura del encabezado/pie
            for tag, style_tag, field in (("style:header", "style:header-style", "top_cm"),
                                          ("style:footer", "style:footer-style", "bottom_cm")):
                box = layout.find(q(style_tag))
                hf = box.find(q("style:header-footer-properties")) if box is not None else None
                if hf is not None and master.find(q(tag)) is not None:
                    attrs = ("fo:min-height",) if hf.get(q("style:dynamic-spacing")) == "true" \
                        else ("fo:min-height", "fo:margin-bottom", "fo:margin-top")  # con espaciado dinámico, la altura ya lo incluye
                    extra = sum((_px(hf.get(q(a))) or 0) for a in attrs)
                    setattr(ps, field, round(getattr(ps, field) + extra / 37.7953, 2))
        if master is not None:
            ps.header_left, ps.header_center, ps.header_right = self._hf_slots(master.find(q("style:header")))
            ps.footer_left, ps.footer_center, ps.footer_right = self._hf_slots(master.find(q("style:footer")))
            ps.first_page_different = (master.find(q("style:header-first")) is not None
                                       or master.find(q("style:footer-first")) is not None)
        return ps.sanitized()

    # ---- bloques ----
    def _blocks(self, parent) -> None:
        for el in parent:
            tag = el.tag
            if tag in (q("text:p"), q("text:h")):
                self.out.append(self._paragraph(el))
            elif tag == q("text:list"):
                self._list(el, None, 1)
            elif tag == q("table:table"):
                self._table(el)
            elif any(tag == q(name) for name in _CONTAINERS):
                self._blocks(el)

    def _paragraph_parts(self, el):
        style = el.get(q("text:style-name"))
        text = self.styles.props("paragraph", style, "text")
        pp = self.styles.props("paragraph", style, "para")
        heading = int(el.get(q("text:outline-level"), "1")) if el.tag == q("text:h") else 0
        return min(heading, 6), pp, self._inline(el, text)

    def _paragraph(self, el, in_list: bool = False) -> str:
        heading, pp, content = self._paragraph_parts(el)
        css = ["white-space:pre-wrap",
               f"margin-top:{pp.get('before') or 0:.0f}px", f"margin-bottom:{pp.get('after') or 0:.0f}px"]
        if not in_list:
            if pp.get("left"):
                css.append(f"margin-left:{pp['left']:.0f}px")
            if pp.get("indent"):
                css.append(f"text-indent:{pp['indent']:.0f}px")
        if pp.get("line") and abs(pp["line"] - 100) > 1:
            css.append(f"line-height:{pp['line']:.0f}%")
        if pp.get("align") in ("left", "center", "right", "justify"):
            css.append(f"text-align:{pp['align']}")
        if pp.get("break"):
            css.append("page-break-before:always")
        return para(f"h{heading}" if heading else "p", content, css)

    # ---- listas ----
    def _list(self, el, inherited: str | None, depth: int) -> None:
        name = el.get(q("text:style-name")) or inherited
        kind, css_type = self.styles.list_kind(name, depth)
        styles = []
        if depth == 1:
            styles.append("margin-top:0px; margin-bottom:8px;")
        if css_type:
            styles.append(f"list-style-type: {css_type}")
        style = f' style="{" ".join(styles)}"' if styles else ""
        self.out.append(f"<{kind}{style}>")
        for item in el:
            if item.tag not in (q("text:list-item"), q("text:list-header")):
                continue
            self.out.append("<li>")
            first = True
            for ch in item:
                if ch.tag in (q("text:p"), q("text:h")):
                    if first:
                        self.out.append(self._paragraph_parts(ch)[2])
                    else:
                        self.out.append(self._paragraph(ch, in_list=True))
                    first = False
                elif ch.tag == q("text:list"):
                    self._list(ch, name, depth + 1)
            self.out.append("</li>")
        self.out.append(f"</{kind}>")

    # ---- texto en línea ----
    def _fmt_for_output(self, fmt: dict) -> dict:
        f = {k: v for k, v in fmt.items() if v}
        if "font" in f and f["font"] == self.base_font:
            f.pop("font")
        if "size" in f and f["size"] == self.base_size:
            f.pop("size")
        return f

    def _text(self, text: str, fmt: dict) -> str:
        return span(esc(text), self._fmt_for_output(fmt)) if text else ""

    def _inline(self, el, fmt: dict) -> str:
        parts = [self._text(el.text or "", fmt)]
        for ch in el:
            tag = ch.tag
            if tag == q("text:span"):
                merged = dict(fmt, **self.styles.props("text", ch.get(q("text:style-name")), "text"))
                parts.append(self._inline(ch, merged))
            elif tag == q("text:a"):
                href = ch.get(q("xlink:href")) or ""
                merged = dict(fmt, href=href) if href and not href.startswith("#") else fmt
                parts.append(self._inline(ch, merged))
            elif tag == q("text:s"):
                parts.append(self._text(" " * int(ch.get(q("text:c"), "1")), fmt))
            elif tag == q("text:tab"):
                parts.append(self._text("\t", fmt))
            elif tag == q("text:line-break"):
                parts.append("<br/>")
            elif tag == q("draw:frame"):
                parts.append(self._image(ch))
            elif any(tag == q(name) for name in _SKIP_INLINE):
                pass
            else:
                parts.append(self._inline(ch, fmt))  # campos, marcadores con texto, etc.
            parts.append(self._text(ch.tail or "", fmt))
        return "".join(parts)

    def _image(self, frame) -> str:
        img = frame.find(q("draw:image"))
        href = img.get(q("xlink:href")) if img is not None else None
        if not href or href.startswith(("http:", "https:")) or href.rsplit(".", 1)[-1].lower() not in _IMG_EXT:
            return ""
        if href not in self._img_by_href:
            try:
                data = self.zf.read(href)
            except KeyError:
                return ""
            name = f"odt_img{len(self.images) + 1}.{href.rsplit('.', 1)[-1].lower()}"
            self.images[name] = data
            self._img_by_href[href] = name
        w, h = _px(frame.get(q("svg:width"))), _px(frame.get(q("svg:height")))
        size = f' width="{w:.0f}" height="{h:.0f}"' if w and h else ""
        return f'<img src="{self._img_by_href[href]}"{size}/>'

    # ---- tablas ----
    def _rows(self, el):
        for ch in el:
            if ch.tag == q("table:table-row"):
                for _ in range(min(int(ch.get(q("table:number-rows-repeated"), "1")), 50)):
                    yield ch
            elif ch.tag in (q("table:table-header-rows"), q("table:table-row-group"), q("table:table-rows")):
                yield from self._rows(ch)

    def _table(self, el) -> None:
        rows = list(self._rows(el))
        cells_html, bordered = [], False
        for tr in rows:
            row = ["<tr>"]
            for cell in tr:
                if cell.tag != q("table:table-cell"):
                    continue
                props = self.styles.styles.get(("table-cell", cell.get(q("table:style-name"))), {}).get("cell", {})
                bordered = bordered or bool(props.get("border"))
                attrs = ""
                for attr, name in (("table:number-columns-spanned", "colspan"), ("table:number-rows-spanned", "rowspan")):
                    n = int(cell.get(q(attr), "1"))
                    if n > 1:
                        attrs += f' {name}="{n}"'
                if props.get("bg"):
                    attrs += f' bgcolor="#{props["bg"]}"'
                inner_start = len(self.out)
                self._blocks(cell)
                inner = "".join(self.out[inner_start:])
                del self.out[inner_start:]
                for _ in range(min(int(cell.get(q("table:number-columns-repeated"), "1")), 30)):
                    row.append(f"<td{attrs}>{inner}</td>")
            row.append("</tr>")
            cells_html.append("".join(row))
        self.out.append(f'<table border="{1 if bordered else 0}" cellspacing="0" cellpadding="4" width="100%">'
                        + "".join(cells_html) + "</table>")
