"""Conversión DOCX <-> HTML.

Este módulo NO depende de Qt, así que se puede probar sin abrir ninguna ventana
(ver tests/test_docx_io.py).  El editor usa HTML como formato "puente":

    abrir .docx  ->  docx_to_html()  ->  QTextDocument.setHtml()
    guardar .docx <- html_to_docx()  <-  QTextDocument.toHtml()

Qué se conserva: negrita, cursiva, subrayado, tachado, sub/superíndice, fuente,
tamaño, color, resaltado, alineación, interlineado, sangrías, títulos, listas
(con viñetas y numeradas, con niveles), tablas (con celdas combinadas),
imágenes, enlaces, líneas horizontales y saltos de página.

Qué NO se conserva todavía (ver ROADMAP.md): encabezados/pies de página,
notas al pie, cuadros de texto, formas, comentarios y control de cambios.
"""
from __future__ import annotations

import html as _html
import io
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Optional
from urllib.parse import unquote
import zipfile

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Emu, Pt, RGBColor
from docx.text.paragraph import Paragraph
from docx.text.run import Run

from ..pagesetup import PageSetup, split_slots
from .htmlout import esc, span as _span_html

# Ancho útil de una hoja A4 con márgenes de 2,54 cm, en píxeles a 96 ppp.
TEXT_WIDTH_PX = 602
EMU_PER_PX = 9525
QT_INDENT_PX = 40  # ancho de una sangría de Qt (QTextDocument.indentWidth)


def _w(tag: str) -> str:
    return qn("w:" + tag)


# =============================================================================
#  LECTOR:  DOCX -> HTML
# =============================================================================

_HIGHLIGHT_HEX = {
    "YELLOW": "ffff00", "BRIGHT_GREEN": "00ff00", "TURQUOISE": "00ffff",
    "PINK": "ff00ff", "BLUE": "0000ff", "RED": "ff0000", "DARK_BLUE": "000080",
    "TEAL": "008080", "GREEN": "008000", "VIOLET": "800080", "DARK_RED": "800000",
    "DARK_YELLOW": "808000", "GRAY_50": "808080", "GRAY_25": "c0c0c0",
    "BLACK": "000000", "WHITE": "ffffff",
}
_NUM_CSS = {
    "decimal": "decimal", "lowerLetter": "lower-alpha", "upperLetter": "upper-alpha",
    "lowerRoman": "lower-roman", "upperRoman": "upper-roman",
}
_ALIGN_CSS = {
    WD_ALIGN_PARAGRAPH.LEFT: "left", WD_ALIGN_PARAGRAPH.CENTER: "center",
    WD_ALIGN_PARAGRAPH.RIGHT: "right", WD_ALIGN_PARAGRAPH.JUSTIFY: "justify",
}


def _chain(style):
    """Un estilo y todos los estilos de los que hereda."""
    while style is not None:
        yield style
        style = style.base_style


_esc = esc


_MAIN_TYPES = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.template.main+xml",
    "application/vnd.ms-word.document.macroEnabled.main+xml",
    "application/vnd.ms-word.template.macroEnabledTemplate.main+xml",
)
_DOCX_MAIN = "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"


def _open_package(path: str):
    """Abre .docx y también plantillas (.dotx) y archivos con macros (.docm/.dotm)."""
    try:
        return Document(path)
    except Exception:
        with zipfile.ZipFile(path) as zf:
            types = zf.read("[Content_Types].xml").decode("utf-8")
            if not any(t in types for t in _MAIN_TYPES):
                raise
            for t in _MAIN_TYPES:
                types = types.replace(t, _DOCX_MAIN)
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as out:
                for item in zf.infolist():
                    data = types.encode("utf-8") if item.filename == "[Content_Types].xml" else zf.read(item.filename)
                    out.writestr(item, data)
        buf.seek(0)
        return Document(buf)


def read_docx(path: str) -> tuple[str, dict[str, bytes], PageSetup]:
    """Lee un .docx y devuelve (html, imagenes, configuración de la hoja)."""
    doc = _open_package(path)
    html, images = _DocxReader(doc).convert()
    return html, images, _read_page(doc)


def docx_to_html(path: str) -> tuple[str, dict[str, bytes]]:
    """Lee un .docx y devuelve (html, imagenes) donde imagenes = {nombre: bytes}."""
    html, images, _ = read_docx(path)
    return html, images


def _field_token(instr: str | None) -> str | None:
    words = (instr or "").strip().upper().split()
    return {"PAGE": "{pagina}", "NUMPAGES": "{paginas}"}.get(words[0]) if words else None


def _paragraph_tokens(p_el) -> str:
    """Texto de un párrafo de encabezado/pie; los campos PAGE y NUMPAGES pasan a {pagina} y {paginas}."""
    out: list[str] = []
    fields: list[dict] = []

    def walk(el):
        for ch in el:
            if ch.tag == _w("r"):
                for c in ch:
                    if c.tag == _w("fldChar"):
                        kind = c.get(_w("fldCharType"))
                        if kind == "begin":
                            fields.append({"instr": "", "phase": "instr", "tok": False})
                        elif kind == "separate" and fields:
                            fields[-1]["phase"] = "result"
                            token = _field_token(fields[-1]["instr"])
                            if token:
                                fields[-1]["tok"] = True
                                out.append(token)
                        elif kind == "end" and fields:
                            fields.pop()
                    elif c.tag == _w("instrText") and fields:
                        fields[-1]["instr"] += c.text or ""
                    elif c.tag in (_w("t"), _w("tab")):
                        if any(f["phase"] == "instr" or f["tok"] for f in fields):
                            continue
                        out.append(c.text or "" if c.tag == _w("t") else "\t")
            elif ch.tag == _w("fldSimple"):
                token = _field_token(ch.get(_w("instr")))
                if token:
                    out.append(token)
                else:
                    walk(ch)
            elif ch.tag in (_w("hyperlink"), _w("ins"), _w("smartTag"), _w("sdt"), _w("sdtContent")):
                walk(ch)

    walk(p_el)
    return "".join(out)


def _hf_slots(part) -> tuple[str, str, str]:
    """(izquierda, centro, derecha) del encabezado o pie; Word los separa con tabuladores."""
    if part.is_linked_to_previous:
        return "", "", ""
    for par in part.paragraphs:
        text = _paragraph_tokens(par._p)
        if not text.strip():
            continue
        align = {WD_ALIGN_PARAGRAPH.CENTER: "center", WD_ALIGN_PARAGRAPH.RIGHT: "right"}.get(par.alignment)
        return split_slots(text, align)
    return "", "", ""


def _read_page(doc) -> PageSetup:
    ps = PageSetup()
    try:
        sec = doc.sections[0]

        def cm(value, default):
            return round(value.cm, 2) if value is not None else default

        ps.width_cm, ps.height_cm = cm(sec.page_width, ps.width_cm), cm(sec.page_height, ps.height_cm)
        ps.top_cm, ps.bottom_cm = cm(sec.top_margin, ps.top_cm), cm(sec.bottom_margin, ps.bottom_cm)
        ps.left_cm, ps.right_cm = cm(sec.left_margin, ps.left_cm), cm(sec.right_margin, ps.right_cm)
        ps.first_page_different = bool(sec.different_first_page_header_footer)
        ps.header_left, ps.header_center, ps.header_right = _hf_slots(sec.header)
        ps.footer_left, ps.footer_center, ps.footer_right = _hf_slots(sec.footer)
    except Exception:
        pass  # una hoja rara no debe impedir abrir el documento
    return ps.sanitized()


class _DocxReader:
    def __init__(self, doc):
        self.doc = doc
        self.images: dict[str, bytes] = {}
        self._img_by_rid: dict[str, str] = {}
        self.out: list[str] = []
        self.lists: list[list] = []  # pila de [tipo, li_abierto, num_id]
        self.pending_page_break = False
        self._pcache: dict = {}   # estilos de párrafo ya resueltos (buscarlos cada vez es lentísimo)
        self._ccache: dict = {}   # estilos de carácter ya resueltos
        self._list_cache: dict = {}
        self.base_font, self.base_size, self.def_after, self.def_line = self._defaults()
        try:
            self.numbering = doc.part.numbering_part.element
        except Exception:
            self.numbering = None

    # ---- valores por defecto del documento --------------------------------
    def _defaults(self):
        font, size, after, line = None, None, 0.0, 1.0
        styles_el = self.doc.styles.element
        for rf in styles_el.xpath("w:docDefaults/w:rPrDefault/w:rPr/w:rFonts"):
            font = rf.get(_w("ascii")) or rf.get(_w("hAnsi")) or font
        for sz in styles_el.xpath("w:docDefaults/w:rPrDefault/w:rPr/w:sz"):
            size = int(sz.get(_w("val"))) / 2
        for sp in styles_el.xpath("w:docDefaults/w:pPrDefault/w:pPr/w:spacing"):
            if sp.get(_w("after")):
                after = int(sp.get(_w("after"))) / 20
            if sp.get(_w("line")) and sp.get(_w("lineRule")) in (None, "auto"):
                line = int(sp.get(_w("line"))) / 240
        try:
            normal = self.doc.styles["Normal"].font
            font = normal.name or font
            size = normal.size.pt if normal.size else size
        except KeyError:
            pass
        return font or "Calibri", size or 11.0, after, line

    # ---- recorrido de bloques --------------------------------------------
    def convert(self):
        self._blocks(self.doc.element.body)
        self._close_lists()
        body_style = f"font-family:'{self.base_font}'; font-size:{self.base_size:g}pt;"
        html = (f'<html><head><meta charset="utf-8"></head>'
                f'<body style="{body_style}">{"".join(self.out)}</body></html>')
        return html, self.images

    def _blocks(self, parent):
        for el in parent:
            if el.tag == _w("p"):
                self._paragraph(el)
            elif el.tag == _w("tbl"):
                self._close_lists()
                self._table(el)
            elif el.tag == _w("sdt"):
                for content in el.iterchildren(_w("sdtContent")):
                    self._blocks(content)

    # ---- listas -----------------------------------------------------------
    def _close_list(self):
        kind, li_open, _ = self.lists.pop()
        if li_open:
            self.out.append("</li>")
        self.out.append(f"</{kind}>")

    def _close_lists(self):
        while self.lists:
            self._close_list()

    def _open_item(self, kind, css, depth, num_id):
        while len(self.lists) > depth:
            self._close_list()
        if len(self.lists) == depth and (self.lists[-1][0] != kind or self.lists[-1][2] != num_id):
            self._close_list()
        if len(self.lists) == depth and self.lists[-1][1]:
            self.out.append("</li>")
            self.lists[-1][1] = False
        while len(self.lists) < depth:
            style = f' style="list-style-type: {css}"' if css and len(self.lists) == depth - 1 else ""
            self.out.append(f"<{kind}{style}>")
            self.lists.append([kind, False, num_id])
        self.out.append("<li>")
        self.lists[-1][1] = True

    def _num_info(self, par, pinfo):
        """(num_id, nivel) si el párrafo es de lista, si no None."""
        candidates = []
        ppr = par._p.pPr
        if ppr is not None and ppr.numPr is not None:
            candidates.append(ppr.numPr)
        candidates.extend(pinfo["numpr"])
        num_id, lvl = None, None
        for np_ in candidates:  # el valor directo manda sobre el del estilo
            if num_id is None and np_.numId is not None:
                num_id = np_.numId.val
            if lvl is None and np_.ilvl is not None:
                lvl = np_.ilvl.val
        if not num_id:
            return None
        return num_id, lvl or 0

    def _list_kind(self, num_id, lvl):
        key = (num_id, lvl)
        if key not in self._list_cache:
            try:
                absid = self.numbering.xpath(f'w:num[@w:numId="{num_id}"]/w:abstractNumId/@w:val')
                fmt = self.numbering.xpath(
                    f'w:abstractNum[@w:abstractNumId="{absid[0]}"]/w:lvl[@w:ilvl="{lvl}"]/w:numFmt/@w:val')
                fmt = fmt[0] if fmt else "bullet"
            except Exception:
                fmt = "bullet"
            self._list_cache[key] = ("ol", _NUM_CSS[fmt]) if fmt in _NUM_CSS else ("ul", None)
        return self._list_cache[key]

    # ---- propiedades heredadas (con caché por estilo) ----
    _FONT_ATTRS = ("bold", "italic", "underline", "strike", "superscript", "subscript", "name", "size")
    _PF_ATTRS = ("space_before", "space_after", "left_indent", "first_line_indent", "line_spacing",
                 "alignment", "page_break_before")

    @staticmethod
    def _color(font):
        c = font.color
        if c is not None and c.type is not None and c.rgb is not None:
            return str(c.rgb).lower()
        return None

    def _style_info(self, style) -> dict:
        """Propiedades de un estilo junto con las de los estilos de los que hereda (se calcula una vez)."""
        chain = list(_chain(style))
        font = {}
        for attr in self._FONT_ATTRS:
            font[attr] = next((v for st in chain if (v := getattr(st.font, attr)) is not None), None)
        font["color"] = next((c for st in chain if (c := self._color(st.font)) is not None), None)
        pf = {}
        for attr in self._PF_ATTRS:
            pf[attr] = next((v for st in chain
                             if (v := getattr(getattr(st, "paragraph_format", None), attr, None)) is not None), None)
        numpr = [st.element.pPr.numPr for st in chain
                 if getattr(st.element, "pPr", None) is not None and st.element.pPr.numPr is not None]
        return {"font": font, "pf": pf, "numpr": numpr,
                "name": ((style.name or "").lower() if style is not None else "")}

    def _pinfo(self, par) -> dict:
        sid = par._p.style
        info = self._pcache.get(sid)
        if info is None:
            info = self._pcache[sid] = self._style_info(par.style)
        return info

    def _cinfo(self, run) -> dict:
        sid = run._r.style
        info = self._ccache.get(sid)
        if info is None:
            try:
                info = self._style_info(run.style)
            except Exception:
                info = {"font": {}, "pf": {}, "numpr": [], "name": ""}
            self._ccache[sid] = info
        return info

    def _run_prop(self, run, cinfo, pinfo, attr):
        """Propiedad de fuente: directa, del estilo de carácter o del de párrafo."""
        v = self._color(run.font) if attr == "color" else getattr(run.font, attr)
        if v is None:
            v = cinfo["font"].get(attr)
        if v is None:
            v = pinfo["font"].get(attr)
        return v

    @staticmethod
    def _pf(par, pinfo, attr):
        v = getattr(par.paragraph_format, attr)
        return v if v is not None else pinfo["pf"].get(attr)

    # ---- párrafos -----------------------------------------------------------
    def _paragraph(self, p_el):
        par = Paragraph(p_el, self.doc)
        pinfo = self._pinfo(par)
        name = pinfo["name"]
        heading = 0
        m = re.match(r"heading (\d)", name)
        if m:
            heading = min(int(m.group(1)), 6)
        elif name == "title":
            heading = 1

        info = self._num_info(par, pinfo)
        if info:
            kind, css = self._list_kind(*info)
            self._open_item(kind, css, info[1] + 1, info[0])
            in_list = True
        else:
            self._close_lists()
            in_list = False

        css_p = ["white-space:pre-wrap"]
        before = self._pf(par, pinfo, "space_before")
        after = self._pf(par, pinfo, "space_after")
        css_p.append(f"margin-top:{(before.pt if before is not None else 0) * 4 / 3:.0f}px")
        css_p.append(f"margin-bottom:{(after.pt if after is not None else self.def_after) * 4 / 3:.0f}px")
        if not in_list:
            left, first = self._pf(par, pinfo, "left_indent"), self._pf(par, pinfo, "first_line_indent")
            if left is not None and left.pt:
                css_p.append(f"margin-left:{left.pt * 4 / 3:.0f}px")
            if first is not None and first.pt:
                css_p.append(f"text-indent:{first.pt * 4 / 3:.0f}px")
        line = self._pf(par, pinfo, "line_spacing")
        line = line if isinstance(line, float) else self.def_line
        if abs(line - 1.0) > 0.01:
            css_p.append(f"line-height:{line * 100:.0f}%")
        align = _ALIGN_CSS.get(self._pf(par, pinfo, "alignment"))
        if align:
            css_p.append(f"text-align:{align}")
        if self.pending_page_break or self._pf(par, pinfo, "page_break_before"):
            css_p.append("page-break-before:always")
            self.pending_page_break = False

        content = self._runs_html(par, p_el, pinfo)
        if in_list:
            if content:
                self.out.append(content)
            return
        tag = f"h{heading}" if heading else "p"
        self.out.append(f'<{tag} style="{"; ".join(css_p)}">{content or "<br/>"}</{tag}>')

    def _runs_html(self, par, p_el, pinfo) -> str:
        items = []  # ("t", texto, clave_formato) | ("html", fragmento)
        for r_el, href in self._iter_runs(p_el):
            run = Run(r_el, par)
            fmt = self._run_format(run, pinfo, href)
            key = tuple(sorted(fmt.items(), key=lambda kv: kv[0]))
            for ch in r_el:
                tag = ch.tag
                if tag == _w("t"):
                    self._add_text(items, ch.text or "", key)
                elif tag == _w("tab"):
                    self._add_text(items, "\t", key)
                elif tag in (_w("br"), _w("cr")):
                    if ch.get(_w("type")) == "page":
                        self.pending_page_break = True
                    else:
                        items.append(("html", "<br/>"))
                elif tag == _w("noBreakHyphen"):
                    self._add_text(items, "-", key)
                elif tag in (_w("drawing"), _w("pict")):
                    img = self._image_html(ch)
                    if img:
                        items.append(("html", img))
        out = []
        for it in items:
            if it[0] == "html":
                out.append(it[1])
            else:
                out.append(self._span(_esc(it[1]), dict(it[2])))
        return "".join(out)

    @staticmethod
    def _add_text(items, text, key):
        if items and items[-1][0] == "t" and items[-1][2] == key:
            items[-1] = ("t", items[-1][1] + text, key)
        else:
            items.append(("t", text, key))

    def _iter_runs(self, el, href=None):
        for ch in el:
            if ch.tag == _w("r"):
                yield ch, href
            elif ch.tag == _w("hyperlink"):
                rid, h = ch.get(qn("r:id")), None
                if rid:
                    try:
                        h = self.doc.part.rels[rid].target_ref
                    except KeyError:
                        h = None
                yield from self._iter_runs(ch, h)
            elif ch.tag in (_w("ins"), _w("smartTag"), _w("sdt"), _w("sdtContent"), _w("fldSimple")):
                yield from self._iter_runs(ch, href)

    def _run_format(self, run, pinfo, href):
        cinfo = self._cinfo(run)

        def prop(attr):
            return self._run_prop(run, cinfo, pinfo, attr)

        f = {}
        for attr in ("bold", "italic", "strike"):
            if prop(attr):
                f[attr] = True
        if prop("underline"):  # False, None y WD_UNDERLINE.NONE son "falsos"
            f["underline"] = True
        if prop("superscript"):
            f["sup"] = True
        if prop("subscript"):
            f["sub"] = True
        name = prop("name")
        if name and name != self.base_font:
            f["font"] = name
        size = prop("size")
        if size is not None:
            f["size"] = size.pt
        color = prop("color")
        if color and color != "000000":
            f["color"] = color
        hl = run.font.highlight_color
        if hl is not None:
            f["bg"] = _HIGHLIGHT_HEX.get(hl.name)
        else:  # resaltado hecho con sombreado de texto (así lo guarda IsaWard y también Word en algunos casos)
            rpr = run._r.rPr
            fill = rpr.xpath("w:shd/@w:fill") if rpr is not None else []
            if fill and fill[0].lower() != "auto":
                f["bg"] = fill[0].lower()
        if href:
            f["href"] = href
        return {k: v for k, v in f.items() if v is not None}

    _span = staticmethod(_span_html)

    # ---- imágenes ----------------------------------------------------------
    def _image_html(self, el) -> Optional[str]:
        blips = el.xpath(".//a:blip")
        if not blips:
            return None
        rid = blips[0].get(qn("r:embed"))
        if not rid:
            return None
        if rid not in self._img_by_rid:
            try:
                part = self.doc.part.related_parts[rid]
            except KeyError:
                return None
            ext = str(part.partname).rsplit(".", 1)[-1].lower()
            if ext not in ("png", "jpg", "jpeg", "gif", "bmp"):
                return None  # EMF/WMF/SVG: Qt no los dibuja
            name = f"docx_img{len(self.images) + 1}.{ext}"
            self.images[name] = part.blob
            self._img_by_rid[rid] = name
        size = ""
        ext_el = el.xpath(".//wp:extent")
        if ext_el:
            w, h = int(ext_el[0].get("cx")) / EMU_PER_PX, int(ext_el[0].get("cy")) / EMU_PER_PX
            size = f' width="{w:.0f}" height="{h:.0f}"'
        return f'<img src="{self._img_by_rid[rid]}"{size}/>'

    # ---- tablas ------------------------------------------------------------
    def _table(self, tbl_el):
        rows = []
        for tr in tbl_el.xpath("w:tr"):
            col, cells = 0, []
            for tc in tr.xpath("w:tc"):
                gs = tc.xpath("w:tcPr/w:gridSpan/@w:val")
                vm = tc.xpath("w:tcPr/w:vMerge")
                vmerge = None
                if vm:
                    vmerge = "restart" if vm[0].get(_w("val")) == "restart" else "continue"
                span = int(gs[0]) if gs else 1
                cells.append({"tc": tc, "col": col, "span": span, "vm": vmerge})
                col += span
            rows.append(cells)

        bordered = bool(tbl_el.xpath("w:tblPr/w:tblBorders"))
        style_id = tbl_el.xpath("w:tblPr/w:tblStyle/@w:val")
        if style_id and "grid" in style_id[0].lower():
            bordered = True
        self.out.append(f'<table border="{1 if bordered else 0}" cellspacing="0" cellpadding="4" width="100%">')
        for r, cells in enumerate(rows):
            self.out.append("<tr>")
            for c in cells:
                if c["vm"] == "continue":
                    continue
                rowspan = 1
                if c["vm"] == "restart":
                    for nxt in rows[r + 1:]:
                        match = [x for x in nxt if x["col"] == c["col"] and x["vm"] == "continue"]
                        if not match:
                            break
                        rowspan += 1
                attrs = ""
                if c["span"] > 1:
                    attrs += f' colspan="{c["span"]}"'
                if rowspan > 1:
                    attrs += f' rowspan="{rowspan}"'
                fill = c["tc"].xpath("w:tcPr/w:shd/@w:fill")
                if fill and fill[0] not in ("auto", "FFFFFF"):
                    attrs += f' bgcolor="#{fill[0]}"'
                self.out.append(f"<td{attrs}>")
                saved, self.lists = self.lists, []
                self._blocks(c["tc"])
                self._close_lists()
                self.lists = saved
                self.out.append("</td>")
            self.out.append("</tr>")
        self.out.append("</table>")


# =============================================================================
#  ESCRITOR:  HTML -> DOCX
# =============================================================================

@dataclass
class RunSpec:
    text: str
    fmt: dict = field(default_factory=dict)


@dataclass
class BreakSpec:
    pass


@dataclass
class ImgSpec:
    name: str
    w: Optional[float] = None
    h: Optional[float] = None


@dataclass
class ParaSpec:
    items: list = field(default_factory=list)
    align: Optional[str] = None
    heading: int = 0
    list_kind: Optional[str] = None
    list_level: int = 0
    left_px: float = 0
    first_px: float = 0
    before_px: Optional[float] = None
    after_px: Optional[float] = None
    line_pct: Optional[float] = None
    page_break: bool = False
    hr: bool = False


@dataclass
class CellSpec:
    blocks: list = field(default_factory=list)
    colspan: int = 1
    rowspan: int = 1
    bg: Optional[str] = None


@dataclass
class TableSpec:
    rows: list = field(default_factory=list)
    border: bool = False


@dataclass
class Model:
    blocks: list
    base_font: Optional[str] = None
    base_size: Optional[float] = None


_NAMED_COLORS = {"black": "000000", "white": "ffffff", "red": "ff0000", "green": "008000",
                 "blue": "0000ff", "yellow": "ffff00", "gray": "808080", "grey": "808080",
                 "orange": "ffa500", "purple": "800080"}
_FONT_KEYWORDS = {"xx-small": 7, "x-small": 7.5, "small": 10, "medium": 12,
                  "large": 13.5, "x-large": 18, "xx-large": 24}
_GENERIC_FAMILIES = {"serif", "sans-serif", "monospace", "cursive", "fantasy", "system-ui"}
_UNIT_PX = {"px": 1, "pt": 4 / 3, "cm": 37.7953, "mm": 3.77953, "in": 96, None: 1}


def _parse_color(v: str) -> Optional[str]:
    v = (v or "").strip().lower()
    m = re.fullmatch(r"#([0-9a-f]{6})", v)
    if m:
        return m.group(1)
    m = re.fullmatch(r"#([0-9a-f])([0-9a-f])([0-9a-f])", v)
    if m:
        return "".join(c * 2 for c in m.groups())
    m = re.fullmatch(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*[,)].*", v)
    if m:
        return "%02x%02x%02x" % tuple(min(255, int(x)) for x in m.groups())
    return _NAMED_COLORS.get(v)


def _parse_size_pt(v: str) -> Optional[float]:
    v = v.strip().lower()
    if v in _FONT_KEYWORDS:
        return _FONT_KEYWORDS[v]
    m = re.fullmatch(r"([\d.]+)\s*(pt|px)?", v)
    if m:
        n = float(m.group(1))
        return n * 0.75 if m.group(2) == "px" else n
    return None


def _parse_px(v: str) -> Optional[float]:
    m = re.fullmatch(r"(-?[\d.]+)\s*(px|pt|cm|mm|in)?", (v or "").strip().lower())
    return float(m.group(1)) * _UNIT_PX[m.group(2)] if m else None


def _css(style: Optional[str]) -> dict:
    out = {}
    for part in (style or "").split(";"):
        if ":" in part:
            k, v = part.split(":", 1)
            out[k.strip().lower()] = v.strip()
    return out


def _inline_from_css(css: dict) -> dict:
    d = {}
    fw = css.get("font-weight")
    if fw:
        d["bold"] = fw in ("bold", "bolder") or (fw.isdigit() and int(fw) >= 600)
    fs = css.get("font-style")
    if fs:
        d["italic"] = fs in ("italic", "oblique")
    td = css.get("text-decoration") or css.get("text-decoration-line")
    if td:
        toks = td.lower().split()
        d["underline"] = "underline" in toks
        d["strike"] = "line-through" in toks
    va = css.get("vertical-align")
    if va in ("super", "sub", "baseline"):
        d["sup"], d["sub"] = va == "super", va == "sub"
    ff = css.get("font-family")
    if ff:
        first = ff.split(",")[0].strip().strip("'\"")
        if first and first.lower() not in _GENERIC_FAMILIES:
            d["font"] = first
    if "font-size" in css:
        sz = _parse_size_pt(css["font-size"])
        if sz:
            d["size"] = sz
    if "color" in css:
        c = _parse_color(css["color"])
        if c:
            d["color"] = c
    bg = _parse_color(css.get("background-color") or css.get("background") or "")
    if bg:
        d["bg"] = bg
    return d


_TAG_STYLE = {
    "b": {"bold": True}, "strong": {"bold": True},
    "i": {"italic": True}, "em": {"italic": True}, "cite": {"italic": True},
    "u": {"underline": True}, "ins": {"underline": True},
    "s": {"strike": True}, "strike": {"strike": True}, "del": {"strike": True},
    "sub": {"sub": True, "sup": False}, "sup": {"sup": True, "sub": False},
    "code": {"font": "Courier New"}, "tt": {"font": "Courier New"},
}
_VOID = {"br", "img", "hr", "meta", "link", "input", "col", "area", "base", "wbr"}
_SKIP = {"style", "script", "title"}
_PARA_TAGS = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "pre", "blockquote"}


class _HtmlToModel(HTMLParser):
    """Lee el HTML que genera Qt (y HTML sencillo de otras fuentes)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.model = Model(blocks=[])
        self.blocks = self.model.blocks
        self.para: Optional[ParaSpec] = None
        self.cur: dict = {}
        self.stack: list = []  # (tag, estilo_anterior)
        self.lists: list = []
        self.skip = 0
        self.pre = 0
        self.table_depth = 0
        self.table: Optional[TableSpec] = None
        self.row: Optional[list] = None
        self.block_stack: list = []

    # -- estilos en línea --
    def _push(self, tag, attrs):
        self.stack.append((tag, self.cur))
        new = dict(self.cur)
        new.update(_TAG_STYLE.get(tag, {}))
        if tag == "a" and attrs.get("href"):
            new["href"] = attrs["href"]
        if tag == "font":
            if attrs.get("face"):
                new["font"] = attrs["face"]
            c = _parse_color(attrs.get("color", ""))
            if c:
                new["color"] = c
        new.update(_inline_from_css(_css(attrs.get("style"))))
        self.cur = new

    def _pop(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                self.cur = self.stack[i][1]
                del self.stack[i:]
                return

    # -- párrafos --
    def _open_para(self, tag, attrs):
        if tag == "p" and self.para is not None and not self.para.items and self.para.list_kind:
            return  # <li><p>..</p></li>: se reutiliza el párrafo del <li>
        self._close_para()
        css = _css(attrs.get("style"))
        p = ParaSpec()
        if len(tag) == 2 and tag[0] == "h" and tag[1].isdigit():
            p.heading = int(tag[1])
        if tag == "li":
            p.list_kind = self.lists[-1] if self.lists else "ul"
            p.list_level = max(1, len(self.lists))
        align = attrs.get("align") or css.get("text-align")
        if align in ("left", "center", "right", "justify"):
            p.align = align
        if p.list_kind is None:
            p.left_px = _parse_px(css.get("margin-left", "")) or 0
            p.first_px = _parse_px(css.get("text-indent", "")) or 0
            m = re.search(r"-qt-block-indent\s*:\s*(\d+)", attrs.get("style") or "")
            if m:
                p.left_px += int(m.group(1)) * QT_INDENT_PX
        p.before_px = _parse_px(css.get("margin-top", ""))
        p.after_px = _parse_px(css.get("margin-bottom", ""))
        lh = css.get("line-height", "")
        if lh.endswith("%"):
            try:
                p.line_pct = float(lh[:-1])
            except ValueError:
                pass
        if css.get("page-break-before") == "always":
            p.page_break = True
        self.para = p
        self.blocks.append(p)

    def _close_para(self):
        p = self.para
        if p is not None:
            # Qt escribe <br/> para un párrafo vacío: no es un salto de línea real.
            if len(p.items) == 1 and isinstance(p.items[0], BreakSpec):
                p.items.clear()
            self.para = None

    def _ensure_para(self) -> ParaSpec:
        if self.para is None:
            self._open_para("p", {})
        return self.para

    # -- eventos del parser --
    def handle_starttag(self, tag, attrs):
        attrs = {k: (v or "") for k, v in attrs}
        if tag in _SKIP:
            self.skip += 1
            return
        if tag == "body":
            d = _inline_from_css(_css(attrs.get("style")))
            self.model.base_font, self.model.base_size = d.get("font"), d.get("size")
            return
        if tag in _VOID:
            self._void(tag, attrs)
            return
        if tag in ("ul", "ol"):
            self._close_para()
            self.lists.append(tag)
            return
        if tag == "table":
            self._close_para()
            self.table_depth += 1
            if self.table_depth == 1:
                try:
                    border = int(attrs.get("border", "0") or 0) > 0
                except ValueError:
                    border = False
                self.table = TableSpec(border=border)
                self.blocks.append(self.table)
            return
        if tag == "tr":
            if self.table_depth == 1:
                self.row = []
                self.table.rows.append(self.row)
            return
        if tag in ("td", "th"):
            if self.table_depth == 1 and self.row is not None:
                self._close_para()
                bg = _parse_color(attrs.get("bgcolor", "")) or _parse_color(
                    _css(attrs.get("style")).get("background-color", ""))
                cell = CellSpec(bg=bg)
                for key in ("colspan", "rowspan"):
                    try:
                        setattr(cell, key, max(1, int(attrs.get(key, "1"))))
                    except ValueError:
                        pass
                self.row.append(cell)
                self.block_stack.append(self.blocks)
                self.blocks = cell.blocks
                self._push(tag, {"style": ""})
            return
        self._push(tag, attrs)
        if tag in _PARA_TAGS:
            self._open_para(tag, attrs)
            if tag == "pre":
                self.pre += 1
                self.cur = {**self.cur, "font": "Courier New"}

    def _void(self, tag, attrs):
        if tag == "br":
            self._ensure_para().items.append(BreakSpec())
        elif tag == "img" and attrs.get("src"):
            css = _css(attrs.get("style"))
            w = _parse_px(attrs.get("width") or css.get("width", ""))
            h = _parse_px(attrs.get("height") or css.get("height", ""))
            self._ensure_para().items.append(ImgSpec(attrs["src"], w, h))
        elif tag == "hr":
            self._close_para()
            self.blocks.append(ParaSpec(hr=True, before_px=0, after_px=0))

    def handle_endtag(self, tag):
        if tag in _SKIP:
            self.skip = max(0, self.skip - 1)
            return
        if tag in _VOID or tag == "body":
            return
        if tag in ("ul", "ol"):
            self._close_para()
            if self.lists:
                self.lists.pop()
            return
        if tag == "table":
            self.table_depth = max(0, self.table_depth - 1)
            if self.table_depth == 0:
                self.table = None
            return
        if tag == "tr":
            return
        if tag in ("td", "th"):
            if self.table_depth == 1 and self.block_stack:
                self._close_para()
                self.blocks = self.block_stack.pop()
                self._pop(tag)
            return
        if tag in _PARA_TAGS:
            self._close_para()
            if tag == "pre":
                self.pre = max(0, self.pre - 1)
        self._pop(tag)

    def handle_data(self, data):
        if self.skip:
            return
        if self.pre:
            parts = data.replace("\r", "").split("\n")
        else:
            parts = [data.replace("\r", "").replace("\n", " ")]
        for i, part in enumerate(parts):
            if i:
                self._ensure_para().items.append(BreakSpec())
            if not part:
                continue
            if self.para is None and not part.strip():
                continue  # espacios entre etiquetas
            self._ensure_para().items.append(RunSpec(part, dict(self.cur)))


def parse_html(html_text: str) -> Model:
    parser = _HtmlToModel()
    parser.feed(html_text)
    parser.close()
    return parser.model


# ---- renderizado a python-docx ---------------------------------------------

_ALIGN_DOCX = {"left": WD_ALIGN_PARAGRAPH.LEFT, "center": WD_ALIGN_PARAGRAPH.CENTER,
               "right": WD_ALIGN_PARAGRAPH.RIGHT, "justify": WD_ALIGN_PARAGRAPH.JUSTIFY}
_LINK_BLUE = "0563C1"


class _DocxWriter:
    def __init__(self, model: Model, images: dict[str, bytes], page: PageSetup | None = None):
        self.model = model
        self.images = images
        self.page = page or PageSetup()
        self.doc = Document()
        self.base_font = model.base_font or "Calibri"
        self.base_size = model.base_size or 11.0
        self._setup()

    def _setup(self):
        sec = self.doc.sections[0]
        pg = self.page
        sec.page_width, sec.page_height = Cm(pg.width_cm), Cm(pg.height_cm)
        sec.orientation = WD_ORIENT.LANDSCAPE if pg.landscape else WD_ORIENT.PORTRAIT
        sec.left_margin, sec.right_margin = Cm(pg.left_cm), Cm(pg.right_cm)
        sec.top_margin, sec.bottom_margin = Cm(pg.top_cm), Cm(pg.bottom_cm)
        self._header_footer(sec)
        normal = self.doc.styles["Normal"]
        normal.font.name = self.base_font
        normal.font.size = Pt(self.base_size)

    # ---- encabezado y pie ----
    def _header_footer(self, sec):
        if not self.page.has_decorations():
            return
        slots = self.page.composed()
        sec.different_first_page_header_footer = self.page.first_page_different
        for part, key in ((sec.header, "header"), (sec.footer, "footer")):
            if any(slots[key]):
                part.is_linked_to_previous = False
                self._fill_hf(part, slots[key])

    @staticmethod
    def _small(run):
        run.font.size = Pt(9)
        run.font.color.rgb = RGBColor(0x59, 0x59, 0x59)

    def _field(self, p, instr: str):
        def mark(kind):
            r = p.add_run()
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), kind)
            r._r.append(el)
            return r
        runs = [mark("begin")]
        r = p.add_run()
        it = OxmlElement("w:instrText")
        it.set(qn("xml:space"), "preserve")
        it.text = f" {instr} "
        r._r.append(it)
        runs += [r, mark("separate"), p.add_run("1"), mark("end")]
        for run in runs:
            self._small(run)

    def _fill_hf(self, part, slots):
        left, center, right = slots
        p = part.paragraphs[0] if part.paragraphs else part.add_paragraph()
        for r in list(p.runs):
            r._r.getparent().remove(r._r)
        p.style = self.doc.styles["Normal"]  # el estilo "Encabezado" de Word trae tabuladores propios que estorban
        text = left + (("\t" + center) if (center or right) else "") + (("\t" + right) if right else "")
        if center or right:
            width = self.page.text_width_cm()
            p.paragraph_format.tab_stops.add_tab_stop(Cm(width / 2), WD_TAB_ALIGNMENT.CENTER)
            p.paragraph_format.tab_stops.add_tab_stop(Cm(width), WD_TAB_ALIGNMENT.RIGHT)
        for piece in re.split(r"(\{pagina\}|\{paginas\})", text):
            if piece == "{pagina}":
                self._field(p, "PAGE")
            elif piece == "{paginas}":
                self._field(p, "NUMPAGES")
            elif piece:
                self._small(p.add_run(piece))

    def write(self, path):
        self._blocks(self.doc, self.model.blocks)
        if self.model.blocks and isinstance(self.model.blocks[-1], TableSpec):
            self.doc.add_paragraph()  # Word espera un párrafo tras una tabla final
        self.doc.save(path)

    def _blocks(self, container, blocks, reuse_first=None):
        first = reuse_first
        for b in blocks:
            if isinstance(b, TableSpec):
                self._table(container, b)
            else:
                self._paragraph(container, b, first)
            first = None

    # ---- párrafos ----
    def _paragraph(self, container, spec: ParaSpec, reuse=None):
        p = reuse if reuse is not None else container.add_paragraph()
        if spec.heading:
            p.style = f"Heading {min(spec.heading, 6)}"
        elif spec.list_kind:
            base = "List Bullet" if spec.list_kind == "ul" else "List Number"
            lvl = min(max(spec.list_level, 1), 3)
            p.style = base if lvl == 1 else f"{base} {lvl}"
        if spec.hr:  # la línea va primero para respetar el orden de pPr
            pbdr = OxmlElement("w:pBdr")
            bottom = OxmlElement("w:bottom")
            for k, v in (("val", "single"), ("sz", "8"), ("space", "1"), ("color", "808080")):
                bottom.set(qn("w:" + k), v)
            pbdr.append(bottom)
            p._p.get_or_add_pPr().append(pbdr)
        pf = p.paragraph_format
        if spec.align:
            p.alignment = _ALIGN_DOCX[spec.align]
        if spec.before_px is not None:
            pf.space_before = Pt(round(spec.before_px * 0.75, 1))
        if spec.after_px is not None:
            pf.space_after = Pt(round(spec.after_px * 0.75, 1))
        if spec.left_px:
            pf.left_indent = Pt(round(spec.left_px * 0.75, 1))
        if spec.first_px:
            pf.first_line_indent = Pt(round(spec.first_px * 0.75, 1))
        if spec.line_pct and abs(spec.line_pct - 100) > 1:
            pf.line_spacing = round(spec.line_pct / 100, 2)
        if spec.page_break:
            pf.page_break_before = True
        for it in spec.items:
            if isinstance(it, RunSpec):
                self._run(p, it, bool(spec.heading))
            elif isinstance(it, BreakSpec):
                p.add_run().add_break()
            elif isinstance(it, ImgSpec):
                self._image(p, it)
        return p

    def _run(self, p, rs: RunSpec, heading: bool):
        f = rs.fmt
        r = p.add_run(rs.text)
        if f.get("bg"):  # el sombreado va primero para respetar el orden de rPr
            shd = OxmlElement("w:shd")
            for k, v in (("val", "clear"), ("color", "auto"), ("fill", f["bg"].upper())):
                shd.set(qn("w:" + k), v)
            r._r.get_or_add_rPr().append(shd)
        if f.get("bold") is not None:
            r.bold = f["bold"]
        if f.get("italic") is not None:
            r.italic = f["italic"]
        if f.get("underline"):
            r.underline = True
        if f.get("strike"):
            r.font.strike = True
        if f.get("sup"):
            r.font.superscript = True
        if f.get("sub"):
            r.font.subscript = True
        font = f.get("font") or (self.base_font if heading else None)
        if font:
            r.font.name = font
        if f.get("size"):
            r.font.size = Pt(f["size"])
        color = f.get("color")
        if f.get("href"):
            color = color or _LINK_BLUE
            r.underline = True
        elif heading and not color:
            color = "000000"  # el estilo de Word pone títulos azules; el editor los muestra negros
        if color:
            r.font.color.rgb = RGBColor.from_string(color.upper())
        if f.get("href"):
            rid = p.part.relate_to(f["href"], RT.HYPERLINK, is_external=True)
            link = OxmlElement("w:hyperlink")
            link.set(qn("r:id"), rid)
            link.set(qn("w:history"), "1")
            r._r.addprevious(link)
            link.append(r._r)

    def _image(self, p, it: ImgSpec):
        data = self.images.get(it.name) or self.images.get(unquote(it.name))
        if not data:
            return
        w, h = it.w, it.h
        limit = self.page.text_width_cm() * 96 / 2.54  # ancho útil de la hoja elegida, en píxeles
        if w and w > limit:
            h = h * limit / w if h else None
            w = limit
        kwargs = {}
        if w:
            kwargs["width"] = Emu(int(w * EMU_PER_PX))
            if h:
                kwargs["height"] = Emu(int(h * EMU_PER_PX))
        try:
            p.add_run().add_picture(io.BytesIO(data), **kwargs)
        except Exception:
            pass  # formato de imagen no soportado: se omite sin romper el guardado

    # ---- tablas ----
    def _table(self, container, spec: TableSpec):
        occupied, placements, ncols = set(), [], 0
        nrows = len(spec.rows)
        for r, row in enumerate(spec.rows):
            c = 0
            for cell in row:
                while (r, c) in occupied:
                    c += 1
                cell.rowspan = min(cell.rowspan, nrows - r)
                placements.append((r, c, cell))
                for dr in range(cell.rowspan):
                    for dc in range(cell.colspan):
                        occupied.add((r + dr, c + dc))
                c += cell.colspan
            ncols = max(ncols, c)
        if not nrows or not ncols:
            return
        table = container.add_table(rows=nrows, cols=ncols)
        if spec.border:
            table.style = "Table Grid"
        for r, c, cell in placements:  # primero se combinan las celdas...
            if cell.colspan > 1 or cell.rowspan > 1:
                table.cell(r, c).merge(table.cell(r + cell.rowspan - 1, c + cell.colspan - 1))
        for r, c, cell in placements:  # ...y luego se rellenan
            tcell = table.cell(r, c)
            if cell.bg:
                shd = OxmlElement("w:shd")
                for k, v in (("val", "clear"), ("color", "auto"), ("fill", cell.bg.upper())):
                    shd.set(qn("w:" + k), v)
                tcell._tc.get_or_add_tcPr().append(shd)
            if cell.blocks:
                first = tcell.paragraphs[0] if isinstance(cell.blocks[0], ParaSpec) else None
                self._blocks(tcell, cell.blocks, reuse_first=first)


def html_to_docx(html_text: str, images: dict[str, bytes], path: str, page: PageSetup | None = None) -> None:
    """Escribe un .docx a partir del HTML del editor, sus imágenes {nombre: bytes} y la configuración de la hoja."""
    _DocxWriter(parse_html(html_text), images, page).write(path)
