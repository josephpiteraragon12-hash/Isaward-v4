"""RTF <-> HTML.  No usa Qt.

    html, imagenes = rtf_to_html("carta.rtf")
    html_to_rtf(html, imagenes, "carta.rtf")

Lector: texto con acentos y símbolos, fuente, tamaño, negrita, cursiva, subrayado, tachado, color,
resaltado, sub/superíndice, alineación, sangrías, espaciado, interlineado, títulos, listas con
viñetas o números, tablas (con celdas combinadas), imágenes PNG/JPEG, enlaces y saltos de página.
Escritor: lo mismo, salvo que las listas se escriben como texto ("•" y "1.") con sangría francesa.
"""
from __future__ import annotations

import re
import struct
from pathlib import Path

import re as _re

from ..pagesetup import PageSetup, cm_to_twips, split_slots, twips_to_cm
from .docx_io import (BreakSpec, ImgSpec, ParaSpec, RunSpec, TableSpec, _field_token, parse_html)
from .htmlout import ListStack, esc, para, span, wrap

# =============================================================================
#  LECTOR
# =============================================================================

_TOKEN = re.compile(r"\\([a-zA-Z]{1,32})(-?\d{1,10})? ?|\\'([0-9a-fA-F]{2})|\\([^a-zA-Z0-9])|([{}])|([^\\{}\r\n]+)|[\r\n]+")

_DEST = {"fonttbl", "colortbl", "stylesheet", "listtable", "listoverridetable", "fldinst", "pict", "pn"}
_STAR_OK = {"fldinst", "shppict", "listtable", "listoverridetable", "pn"}
_SKIP_DEST = {
    "info", "header", "headerl", "headerr", "headerf", "footer", "footerl", "footerr", "footerf", "footnote",
    "annotation", "object", "private", "themedata", "colorschememapping", "datastore", "latentstyles", "rsidtbl",
    "xmlnstbl", "generator", "listtext", "pntext", "pntxta", "pntxtb", "nonshppict", "shpinst", "shprslt",
    "bkmkstart", "bkmkend", "xe", "tc", "txe", "fchars", "lchars", "docvar", "userprops", "revtbl", "filetbl",
    "mmathpr", "wgrffmtfilter", "passwordhash", "ftnsep", "ftnsepc", "aftnsep", "aftnsepc", "ftncn", "aftncn",
    "background", "protusertbl", "operator", "title", "subject", "author", "keywords", "comment", "doccomm",
    "hlinkbase", "pgptbl", "listpicture", "stylesheet_skip",
}
_UNDERLINE = {"ul", "uld", "uldash", "uldashd", "uldashdd", "uldb", "ulhwave", "ulldash", "ulth", "ulthd",
              "ulthdash", "ulthdashd", "ulthdashdd", "ulthldash", "ululdbwave", "ulw", "ulwave"}
_SYMBOLS = {"par": "\n", "~": "\xa0", "_": "-", "-": "", "emdash": "—", "endash": "–", "bullet": "•",
            "lquote": "‘", "rquote": "’", "ldblquote": "“", "rdblquote": "”", "emspace": "\u2003",
            "enspace": "\u2002", "tab": "\t"}
_NFC_CSS = {0: "decimal", 1: "upper-roman", 2: "lower-roman", 3: "upper-alpha", 4: "lower-alpha"}
_CODEPAGES = {10000: "mac_roman", 437: "cp437", 850: "cp850", 65001: "utf-8"}


def _new_state(parent: dict | None = None) -> dict:
    if parent is not None:
        return dict(parent, star=False)
    return {"b": False, "i": False, "ul": False, "st": False, "sup": False, "sub": False, "font": None,
            "fs": None, "cf": None, "bg": None, "uc": 1, "dest": None, "star": False, "href": None,
            "field": False}


def read_rtf(path: str) -> tuple[str, dict[str, bytes], PageSetup]:
    """Lee un .rtf y devuelve (html, imagenes, configuración de la hoja)."""
    reader = _RtfReader()
    html, images = reader.parse(Path(path).read_bytes().decode("latin-1"))
    return html, images, reader.page_setup()


def rtf_to_html(path: str) -> tuple[str, dict[str, bytes]]:
    html, images, _ = read_rtf(path)
    return html, images


class _RtfReader:
    def __init__(self):
        self.st = _new_state()
        self.stack: list[dict] = []
        self.fonts: dict[int, str] = {}
        self.colors: list[str | None] = []  # el índice 0 (automático) lo crea el primer ";" de la tabla
        self.style_names: dict[int, str] = {}
        self.list_levels: dict[int, list] = {}   # listid -> [nfc por nivel]
        self.list_override: dict[int, int] = {}  # \ls -> listid
        self.deff, self.cp = 0, "cp1252"
        self.base_size: float | None = None
        self.images: dict[str, bytes] = {}
        self.out: list[str] = []
        self.lists = ListStack(self.out)
        self.runs: list[str] = []
        self.pending_bytes: list[int] = []
        self.skip = 0
        self.hi_surrogate = 0
        self.pending_href: str | None = None
        self.page_break_next = False
        # destinos con memoria
        self.font_idx, self.font_buf = 0, ""
        self.style_idx, self.style_buf = None, ""
        self.rgb = [None, None, None]
        self.cur_list: dict | None = None
        self.cur_override_listid: int | None = None
        self.fld_text = ""
        self.pict: dict = {}
        self.page_raw: dict = {}
        self.hf = {"header": "", "footer": ""}
        self.hf_align: dict = {"header": None, "footer": None}
        self.skip_result = False
        # párrafo y tabla
        self.p = self._new_para()
        self.table: dict | None = None
        self.row_def: list[dict] = []
        self.cell_def: dict = {}
        self.row_left = 0
        self.row_cells: list[dict] = []
        self.cell_paras: list[str] = []

    @staticmethod
    def _new_para() -> dict:
        return {"align": None, "li": 0, "fi": 0, "sb": None, "sa": None, "sl": None, "slmult": 0,
                "intbl": False, "ls": None, "ilvl": 0, "pagebb": False, "style": None, "outline": None,
                "legacy": None}

    # ---------------------------------------------------------------- bucle principal
    def parse(self, data: str):
        for m in _TOKEN.finditer(data):
            word, num, hexv, sym, brace, text = m.groups()
            if self.pending_bytes and hexv is None:
                self._flush_bytes()
            if brace == "{":
                self.stack.append(self.st)
                self.st = _new_state(self.st)
                self.skip = 0
            elif brace == "}":
                self._close_group()
            elif hexv is not None:
                if self.skip:
                    self.skip -= 1
                elif self.st["dest"] in (None, "hf_header", "hf_footer"):
                    self.pending_bytes.append(int(hexv, 16))
            elif sym is not None:
                self._symbol(sym)
            elif word is not None:
                self._word(word.lower(), int(num) if num is not None else None)
            elif text:
                self._text(text)
        self._flush_bytes()
        self._end_paragraph(force=bool(self.runs))
        self._flush_table()
        self.lists.close_all()
        return wrap("".join(self.out), self.fonts.get(self.deff), self.base_size), self.images

    # ---------------------------------------------------------------- grupos
    def _close_group(self):
        closing = self.st
        self.st = self.stack.pop() if self.stack else _new_state()
        self.skip = 0
        if closing["dest"] == "pict" and self.st["dest"] != "pict":
            self._finish_pict()
        elif closing["dest"] == "fldinst" and self.st["dest"] != "fldinst":
            m = re.search(r'HYPERLINK\s+(?!\\l)(?:"([^"]+)"|(\S+))', self.fld_text)
            self.pending_href = (m.group(1) or m.group(2)) if m else None
            if self.st["dest"] in ("hf_header", "hf_footer"):  # PAGE / NUMPAGES en encabezado o pie
                token = _field_token(self.fld_text)
                if token:
                    self.hf[self.st["dest"][3:]] += token
                    self.skip_result = True
            self.fld_text = ""
        elif closing["dest"] == "fonttbl" and self.st["dest"] == "fonttbl":
            self.font_buf = ""
        if closing["field"] and not self.st["field"]:
            self.pending_href = None
            self.skip_result = False

    # ---------------------------------------------------------------- símbolos y bytes
    def _flush_bytes(self):
        if self.pending_bytes:
            try:
                text = bytes(self.pending_bytes).decode(self.cp, errors="replace")
            except LookupError:
                text = bytes(self.pending_bytes).decode("cp1252", errors="replace")
            self.pending_bytes = []
            self._text(text, decoded=True)

    def _symbol(self, sym: str):
        if sym == "*":
            self.st["star"] = True
        elif self.st["dest"] is not None:
            return
        elif sym in "\\{}":
            self._text(sym, decoded=True)
        elif sym in _SYMBOLS:
            self._text(_SYMBOLS[sym], decoded=True)
        elif sym == "\n" or sym == "\r":
            self._end_paragraph(force=True)

    # ---------------------------------------------------------------- texto
    def _text(self, text: str, decoded: bool = False):
        st = self.st
        if self.skip and not decoded:
            n = min(self.skip, len(text))
            text, self.skip = text[n:], self.skip - n
        if not text:
            return
        dest = st["dest"]
        if dest in (None, "hf_header", "hf_footer") and not decoded and any(ord(c) > 127 for c in text):
            text = text.encode("latin-1", "replace").decode(self.cp, errors="replace")
        if dest is None:
            self._add_run(text)
        elif dest in ("hf_header", "hf_footer"):
            self.hf[dest[3:]] += text
        elif dest == "fonttbl":
            self.font_buf += text
            if ";" in self.font_buf:
                self.fonts[self.font_idx] = self.font_buf.split(";")[0].strip()
                self.font_buf = ""
        elif dest == "colortbl":
            for _ in range(text.count(";")):
                self.colors.append("%02x%02x%02x" % tuple(self.rgb) if None not in self.rgb else None)
                self.rgb = [None, None, None]
        elif dest == "stylesheet":
            self.style_buf += text
            if ";" in self.style_buf:
                if self.style_idx is not None:
                    self.style_names[self.style_idx] = self.style_buf.split(";")[0].strip().lower()
                self.style_buf, self.style_idx = "", None
        elif dest == "fldinst":
            self.fld_text += text
        elif dest == "pict":
            self.pict["hex"] = self.pict.get("hex", "") + re.sub(r"[^0-9a-fA-F]", "", text)

    def _fmt(self) -> dict:
        st = self.st
        f = {"bold": st["b"], "italic": st["i"], "underline": st["ul"], "strike": st["st"],
             "sup": st["sup"], "sub": st["sub"]}
        name = self.fonts.get(st["font"]) if st["font"] is not None else None
        if name and name != self.fonts.get(self.deff):
            f["font"] = name
        if st["fs"] and st["fs"] / 2 != self.base_size:
            f["size"] = st["fs"] / 2
        for key, idx in (("color", st["cf"]), ("bg", st["bg"])):
            if idx and idx < len(self.colors) and self.colors[idx]:
                f[key] = self.colors[idx]
        if st["href"]:
            f["href"] = st["href"]
        return f

    def _add_run(self, text: str):
        fmt = self._fmt()
        if self.runs and self.runs[-1][0] == "t" and self.runs[-1][2] == fmt:  # une trozos con el mismo formato
            self.runs[-1] = ("t", self.runs[-1][1] + text, fmt)
        else:
            self.runs.append(("t", text, fmt))

    def _take_runs(self) -> str:
        html = "".join(span(esc(r[1]), r[2]) if r[0] == "t" else r[1] for r in self.runs)
        self.runs = []
        return html

    # ---------------------------------------------------------------- palabras de control
    def _word(self, w: str, n):
        st = self.st
        if st["star"]:
            st["star"] = False
            if w not in _STAR_OK:
                st["dest"] = "skip"
                return
        if st["dest"] == "skip":
            return
        if w in ("header", "footer", "headerr", "footerr"):  # encabezado/pie de todas las hojas
            st["dest"] = "hf_header" if w.startswith("header") else "hf_footer"
            return
        if w in _SKIP_DEST:
            st["dest"] = "skip"
            return
        if w in _DEST:
            st["dest"] = w
            if w == "pict":
                self.pict = {}
            return
        dest = st["dest"]
        if dest in ("hf_header", "hf_footer"):
            self._hf_word(w, n, dest[3:])
            return
        if dest == "fonttbl":
            if w == "f" and n is not None:
                self.font_idx = n
            return
        if dest == "colortbl":
            if w in ("red", "green", "blue") and n is not None:
                self.rgb[("red", "green", "blue").index(w)] = max(0, min(255, n))
            return
        if dest == "stylesheet":
            if w == "s" and n is not None and self.style_idx is None:
                self.style_idx = n
            elif w == "fs" and n and self.style_idx == 0:
                self.base_size = n / 2
            return
        if dest == "listtable":
            self._listtable_word(w, n)
            return
        if dest == "listoverridetable":
            if w == "listid":
                self.cur_override_listid = n
            elif w == "ls" and self.cur_override_listid is not None:
                self.list_override[n] = self.cur_override_listid
            return
        if dest == "pn":
            if w == "pnlvlblt":
                self.p["legacy"] = "ul"
            elif w in ("pnlvlbody", "pndec", "pnlvlcont"):
                self.p["legacy"] = "ol"
            return
        if dest == "pict":
            self._pict_word(w, n)
            return
        if dest in ("fldinst",):
            return
        self._body_word(w, n)

    def _hf_word(self, w: str, n, kind: str):
        st, buf = self.st, self.hf
        if w == "tab":
            buf[kind] += "\t"
        elif w == "chpgn":
            buf[kind] += "{pagina}"
        elif w in ("par", "line"):
            if buf[kind] and not buf[kind].endswith(" "):
                buf[kind] += " "
        elif w == "field":
            st["field"] = True
        elif w == "u" and n is not None:
            self._unicode(n)
        elif w == "uc" and n is not None:
            st["uc"] = n
        elif w == "fldrslt" and self.skip_result:
            st["dest"] = "skip"
        elif w in ("qc", "qr", "ql"):
            self.hf_align[kind] = {"qc": "center", "qr": "right", "ql": None}[w]
        elif w in _SYMBOLS and w not in ("par", "tab"):
            buf[kind] += _SYMBOLS[w]

    def page_setup(self) -> PageSetup:
        r, ps = self.page_raw, PageSetup()
        w, h = r.get("pgwsxn", r.get("paperw")), r.get("pghsxn", r.get("paperh"))
        if w and h:
            ps.width_cm, ps.height_cm = twips_to_cm(w), twips_to_cm(h)
            if r.get("landscape") and ps.width_cm < ps.height_cm:
                ps.width_cm, ps.height_cm = ps.height_cm, ps.width_cm
        for key, attr in (("margt", "top_cm"), ("margb", "bottom_cm"), ("margl", "left_cm"), ("margr", "right_cm")):
            v = r.get(key + "sxn", r.get(key))
            if v is not None:
                setattr(ps, attr, twips_to_cm(v))
        ps.first_page_different = bool(r.get("titlepg"))
        ps.header_left, ps.header_center, ps.header_right = split_slots(self.hf["header"].strip(" \r\n"), self.hf_align["header"])
        ps.footer_left, ps.footer_center, ps.footer_right = split_slots(self.hf["footer"].strip(" \r\n"), self.hf_align["footer"])
        return ps.sanitized()

    def _listtable_word(self, w: str, n):
        if w == "list":
            self.cur_list = {"levels": []}
        elif w == "listlevel" and self.cur_list is not None:
            self.cur_list["levels"].append(0)
        elif w == "levelnfc" and self.cur_list and self.cur_list["levels"]:
            self.cur_list["levels"][-1] = n
        elif w == "listid" and self.cur_list is not None and n is not None:
            self.list_levels[n] = self.cur_list["levels"]

    def _pict_word(self, w: str, n):
        p = self.pict
        if w in ("pngblip", "jpegblip"):
            p["fmt"] = "png" if w == "pngblip" else "jpg"
        elif w in ("wmetafile", "emfblip", "dibitmap", "wbitmap", "macpict", "pmmetafile"):
            p["fmt"] = None
        elif w in ("picwgoal", "pichgoal", "picscalex", "picscaley") and n is not None:
            p[w] = n

    def _finish_pict(self):
        p = self.pict
        self.pict = {}
        if not p.get("fmt") or not p.get("hex"):
            return
        try:
            blob = bytes.fromhex(p["hex"] if len(p["hex"]) % 2 == 0 else p["hex"][:-1])
        except ValueError:
            return
        name = f"rtf_img{len(self.images) + 1}.{p['fmt']}"
        self.images[name] = blob
        size = ""
        if p.get("picwgoal") and p.get("pichgoal"):
            w = p["picwgoal"] / 15 * p.get("picscalex", 100) / 100
            h = p["pichgoal"] / 15 * p.get("picscaley", 100) / 100
            size = f' width="{w:.0f}" height="{h:.0f}"'
        self.runs.append(("h", f'<img src="{name}"{size}/>'))

    def _body_word(self, w: str, n):
        st, p = self.st, self.p
        on = n != 0  # \b = activado, \b0 = desactivado
        if w == "b":
            st["b"] = on
        elif w == "i":
            st["i"] = on
        elif w in _UNDERLINE:
            st["ul"] = on
        elif w == "ulnone":
            st["ul"] = False
        elif w in ("strike", "striked"):
            st["st"] = on
        elif w == "super":
            st["sup"], st["sub"] = True, False
        elif w == "sub":
            st["sup"], st["sub"] = False, True
        elif w == "nosupersub":
            st["sup"] = st["sub"] = False
        elif w == "f" and n is not None:
            st["font"] = n
        elif w == "fs" and n is not None:
            st["fs"] = n
        elif w == "cf" and n is not None:
            st["cf"] = n or None
        elif w in ("highlight", "chcbpat", "cb") and n is not None:
            st["bg"] = n or None
        elif w == "plain":
            st.update(b=False, i=False, ul=False, st=False, sup=False, sub=False, font=None, fs=None, cf=None, bg=None)
        elif w in ("paperw", "paperh", "margl", "margr", "margt", "margb", "pgwsxn", "pghsxn", "marglsxn",
                   "margrsxn", "margtsxn", "margbsxn") and n is not None:
            self.page_raw[w] = n
        elif w in ("landscape", "lndscpsxn"):
            self.page_raw["landscape"] = True
        elif w == "titlepg":
            self.page_raw["titlepg"] = True
        elif w == "uc" and n is not None:
            st["uc"] = n
        elif w == "u" and n is not None:
            self._unicode(n)
        elif w == "deff" and n is not None:
            self.deff = n
        elif w == "ansicpg" and n is not None:
            self.cp = _CODEPAGES.get(n, f"cp{n}")
        elif w == "mac":
            self.cp = "mac_roman"
        elif w == "fldrslt":
            st["href"] = self.pending_href
        elif w == "field":
            st["field"] = True
        elif w == "pard":
            self.p = self._new_para()
        elif w in ("ql", "qc", "qr", "qj"):
            p["align"] = {"ql": "left", "qc": "center", "qr": "right", "qj": "justify"}[w]
        elif w in ("li", "fi", "sb", "sa", "sl", "slmult") and n is not None:
            p[w] = n
        elif w == "pagebb":
            p["pagebb"] = True
        elif w == "page":
            self.page_break_next = True
        elif w == "ls" and n is not None:
            p["ls"] = n
        elif w == "ilvl" and n is not None:
            p["ilvl"] = n
        elif w == "s" and n is not None:
            p["style"] = n
        elif w == "outlinelevel" and n is not None:
            p["outline"] = n
        elif w == "intbl":
            p["intbl"] = True
        elif w == "par":
            self._end_paragraph(force=True)
        elif w == "line":
            self.runs.append(("h", "<br/>"))
        elif w in _SYMBOLS:
            self._text(_SYMBOLS[w], decoded=True)
        elif w == "trowd":
            self._start_row()
        elif w == "trleft" and n is not None:
            self.row_left = n
        elif w.startswith("clbrdr"):
            self.cell_def["border_pending"] = True
        elif w in ("brdrs", "brdrdb", "brdrth", "brdrdot", "brdrdash") and self.cell_def.get("border_pending"):
            self.cell_def["border"] = True
        elif w == "brdrnil":
            self.cell_def["border_pending"] = False
        elif w == "clvmgf":
            self.cell_def["vm"] = "start"
        elif w == "clvmrg":
            self.cell_def["vm"] = "cont"
        elif w == "clmgf":
            self.cell_def["hm"] = "start"
        elif w == "clmrg":
            self.cell_def["hm"] = "cont"
        elif w == "clcbpat" and n is not None:
            self.cell_def["bg"] = self.colors[n] if 0 < n < len(self.colors) else None
        elif w == "cellx" and n is not None:
            self.cell_def["right"] = n
            self.row_def.append(self.cell_def)
            self.cell_def = {}
        elif w == "cell":
            self._end_cell()
        elif w == "row":
            self._end_row()

    def _unicode(self, n: int):
        if n < 0:
            n += 65536
        if 0xD800 <= n <= 0xDBFF:
            self.hi_surrogate = n
        else:
            if 0xDC00 <= n <= 0xDFFF and self.hi_surrogate:
                n = 0x10000 + ((self.hi_surrogate - 0xD800) << 10) + (n - 0xDC00)
            self.hi_surrogate = 0
            if self.st["dest"] is None:
                self._add_run(chr(n))
            elif self.st["dest"] in ("hf_header", "hf_footer"):
                self.hf[self.st["dest"][3:]] += chr(n)
        self.skip = self.st["uc"]

    # ---------------------------------------------------------------- párrafos
    def _heading_level(self) -> int:
        name = self.style_names.get(self.p["style"], "")
        m = re.match(r"heading (\d)", name)
        if m:
            return min(int(m.group(1)), 6)
        if name == "title":
            return 1
        if self.p["outline"] is not None and 0 <= self.p["outline"] <= 5:
            return self.p["outline"] + 1
        return 0

    def _para_css(self, in_list: bool) -> list[str]:
        p = self.p
        css = ["white-space:pre-wrap", f"margin-top:{(p['sb'] or 0) / 15:.0f}px",
               f"margin-bottom:{(p['sa'] or 0) / 15:.0f}px"]
        if not in_list:
            if p["li"]:
                css.append(f"margin-left:{p['li'] / 15:.0f}px")
            if p["fi"]:
                css.append(f"text-indent:{p['fi'] / 15:.0f}px")
        if p["sl"] and p["slmult"] and p["sl"] > 0 and abs(p["sl"] - 240) > 4:
            css.append(f"line-height:{p['sl'] / 240 * 100:.0f}%")
        if p["align"]:
            css.append(f"text-align:{p['align']}")
        if p["pagebb"] or self.page_break_next:
            css.append("page-break-before:always")
            self.page_break_next = False
        return css

    def _list_info(self):
        p = self.p
        if p["ls"] is not None and p["ls"] in self.list_override:
            levels = self.list_levels.get(self.list_override[p["ls"]], [])
            nfc = levels[p["ilvl"]] if p["ilvl"] < len(levels) else (levels[-1] if levels else 23)
            return ("ul", None) if nfc in (23, 255) else ("ol", _NFC_CSS.get(nfc, "decimal"))
        if p["legacy"]:
            return (p["legacy"], None)
        return None

    def _end_paragraph(self, force: bool = False):
        if not force and not self.runs:
            return
        content = self._take_runs()
        p = self.p
        if p["intbl"]:
            self.cell_paras.append(para("p", content, self._para_css(False)))
            return
        self._flush_table()
        info = self._list_info()
        if info:
            kind, css_type = info
            self.lists.open_item(kind, css_type, p["ilvl"] + 1, p["ls"])
            self.out.append(content)
            return
        self.lists.close_all()
        level = self._heading_level()
        self.out.append(para(f"h{level}" if level else "p", content, self._para_css(False)))
        self.p = dict(self._new_para(), **{k: p[k] for k in ("align", "li", "fi", "sb", "sa", "sl", "slmult", "style")})
        self.p["pagebb"] = False

    # ---------------------------------------------------------------- tablas
    def _start_row(self):
        self._end_paragraph()
        self.lists.close_all()
        self.row_def, self.cell_def, self.row_left, self.row_cells = [], {}, 0, []

    def _end_cell(self):
        if self.runs:
            self.cell_paras.append(para("p", self._take_runs(), self._para_css(False)))
        self.row_cells.append("".join(self.cell_paras))
        self.cell_paras = []
        if self.table is None:
            self.table = {"rows": [], "border": False}

    def _end_row(self):
        if self.table is None:
            self.table = {"rows": [], "border": False}
        cells, left = [], self.row_left
        for i, html in enumerate(self.row_cells):
            d = self.row_def[i] if i < len(self.row_def) else {}
            right = d.get("right", left + 1000)
            cells.append({"html": html, "left": left, "right": right, "vm": d.get("vm"), "hm": d.get("hm"),
                          "bg": d.get("bg")})
            self.table["border"] = self.table["border"] or bool(d.get("border"))
            left = right
        merged = []  # celdas unidas en horizontal (Word: \clmgf + \clmrg)
        for c in cells:
            if c["hm"] == "cont" and merged:
                merged[-1]["right"] = c["right"]
            else:
                merged.append(c)
        self.table["rows"].append(merged)
        self.row_cells, self.row_def = [], []
        self.p["intbl"] = False

    def _flush_table(self):
        if self.table is None or not self.table["rows"]:
            self.table = None
            return
        rows = self.table["rows"]
        edges = sorted({e for r in rows for c in r for e in (c["left"], c["right"])})
        canon: list[int] = []
        for e in edges:  # bordes casi iguales (±30 twips) se consideran el mismo
            if not canon or e - canon[-1] > 30:
                canon.append(e)

        def snap(v):
            return min(canon, key=lambda c: abs(c - v))

        total = max(canon[-1] - canon[0], 1)
        html = [f'<table border="{1 if self.table["border"] else 0}" cellspacing="0" cellpadding="4" width="100%">']
        covered = set()
        for ri, row in enumerate(rows):
            html.append("<tr>")
            for ci, c in enumerate(row):
                if (ri, ci) in covered:
                    continue
                left, right = snap(c["left"]), snap(c["right"])
                colspan = max(1, sum(1 for e in canon if left < e <= right))
                rowspan = 1
                if c["vm"] == "start":
                    for rj in range(ri + 1, len(rows)):
                        match = [k for k, d in enumerate(rows[rj]) if snap(d["left"]) == left and d["vm"] == "cont"]
                        if not match:
                            break
                        covered.add((rj, match[0]))
                        rowspan += 1
                attrs = (f' colspan="{colspan}"' if colspan > 1 else "") + (f' rowspan="{rowspan}"' if rowspan > 1 else "")
                if c["bg"]:
                    attrs += f' bgcolor="#{c["bg"]}"'
                attrs += f' width="{(right - left) / total * 100:.0f}%"'
                html.append(f"<td{attrs}>{c['html']}</td>")
            html.append("</tr>")
        html.append("</table>")
        self.out.append("".join(html))
        self.table = None


# =============================================================================
#  ESCRITOR
# =============================================================================

TEXT_WIDTH_TWIPS = 9026  # A4 con márgenes de 2,54 cm
_BULLETS = ["•", "–", "▪"]


def rtf_escape(text: str) -> str:
    out = []
    for ch in text:
        o = ord(ch)
        if ch in "\\{}":
            out.append("\\" + ch)
        elif ch == "\t":
            out.append("\\tab ")
        elif ch in "\n\r":
            out.append("\\line ")
        elif ch == "\xa0":
            out.append("\\~")
        elif o < 32:
            continue
        elif o < 128:
            out.append(ch)
        elif o > 0xFFFF:
            o -= 0x10000
            for unit in (0xD800 + (o >> 10), 0xDC00 + (o & 0x3FF)):
                out.append(f"\\u{unit - 65536}?")
        else:
            out.append(f"\\u{o if o <= 32767 else o - 65536}?")
    return "".join(out)


def _image_info(data: bytes):
    """(formato, ancho, alto) de un PNG o JPEG; None si no es ninguno de los dos."""
    if data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) >= 24:
        w, h = struct.unpack(">II", data[16:24])
        return "pngblip", w, h
    if data[:2] == b"\xff\xd8":
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                h, w = struct.unpack(">HH", data[i + 5:i + 9])
                return "jpegblip", w, h
            i += 2 + struct.unpack(">H", data[i + 2:i + 4])[0]
    return None


def _roman(n: int) -> str:
    vals = [(10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")]
    out = ""
    for v, s in vals:
        while n >= v:
            out, n = out + s, n - v
    return out


class _RtfWriter:
    def __init__(self, model, images: dict[str, bytes], page: PageSetup | None = None):
        self.model, self.images = model, images
        self.page = page or PageSetup()
        self.base_font = model.base_font or "Calibri"
        self.base_size = model.base_size or 11.0
        self.fonts = [self.base_font]
        self.colors: list[str] = []
        self.counters: list[int] = []
        self._collect(model.blocks)

    def _collect(self, blocks):
        for b in blocks:
            if isinstance(b, TableSpec):
                for row in b.rows:
                    for cell in row:
                        self._collect(cell.blocks)
                        self._color(cell.bg)
            elif isinstance(b, ParaSpec):
                for it in b.items:
                    if isinstance(it, RunSpec):
                        f = it.fmt
                        if f.get("font") and f["font"] not in self.fonts:
                            self.fonts.append(f["font"])
                        self._color(f.get("color"))
                        self._color(f.get("bg"))
                        if f.get("href"):
                            self._color("0563c1")

    def _color(self, c):
        if c and c.lower() not in self.colors:
            self.colors.append(c.lower())

    def _cidx(self, c) -> int:
        return self.colors.index(c.lower()) + 1

    def build(self) -> str:
        head = ["{\\rtf1\\ansi\\ansicpg1252\\deff0\\nouicompat\\deflang3082",
                "{\\fonttbl" + "".join(f"{{\\f{i}\\fnil\\fcharset0 {rtf_escape(n)};}}" for i, n in enumerate(self.fonts)) + "}",
                "{\\colortbl ;" + "".join(
                    f"\\red{int(c[0:2], 16)}\\green{int(c[2:4], 16)}\\blue{int(c[4:6], 16)};" for c in self.colors) + "}",
                f"\\paperw{cm_to_twips(self.page.width_cm)}\\paperh{cm_to_twips(self.page.height_cm)}"
                + ("\\landscape" if self.page.landscape else "")
                + f"\\margl{cm_to_twips(self.page.left_cm)}\\margr{cm_to_twips(self.page.right_cm)}"
                f"\\margt{cm_to_twips(self.page.top_cm)}\\margb{cm_to_twips(self.page.bottom_cm)}\\viewkind4\\uc1",
                self._section()]
        body = []
        blocks = self.model.blocks
        for b in blocks:
            if isinstance(b, TableSpec):
                body.append(self._table(b))
                self.counters = []
            else:
                body.append(self._paragraph(b) + "\\par\n")
        if blocks and isinstance(blocks[-1], TableSpec):
            body.append("\\pard\\par\n")
        return "\n".join(head) + "\n" + "".join(body) + "}"

    # ---- encabezado y pie ----
    def _section(self) -> str:
        if not self.page.has_decorations():
            return ""
        out = "\\sectd" + ("\\titlepg" if self.page.first_page_different else "")
        slots = self.page.composed()
        for key in ("header", "footer"):
            if any(slots[key]):
                out += self._hf_group(key, slots[key])
        return out

    def _hf_group(self, key: str, slots) -> str:
        left, center, right = slots
        text = left + (("\t" + center) if (center or right) else "") + (("\t" + right) if right else "")
        width = cm_to_twips(self.page.text_width_cm())
        tabs = f"\\tqc\\tx{width // 2}\\tqr\\tx{width}" if (center or right) else ""
        body = ""
        for piece in _re.split(r"(\{pagina\}|\{paginas\})", text):
            if piece in ("{pagina}", "{paginas}"):
                instr = "PAGE" if piece == "{pagina}" else "NUMPAGES"
                body += f"{{\\field{{\\*\\fldinst {instr}}}{{\\fldrslt 1}}}}"
            else:
                body += rtf_escape(piece)
        return f"{{\\{key}\\pard\\plain{tabs}\\f0\\fs18 {body}\\par}}"

    # ---- párrafos ----
    def _para_ctrl(self, spec: ParaSpec, in_table: bool = False) -> str:
        c = ["\\pard"]
        if in_table:
            c.append("\\intbl")
        c.append(f"\\plain\\f0\\fs{round(self.base_size * 2)}")
        if spec.align:
            c.append({"left": "\\ql", "center": "\\qc", "right": "\\qr", "justify": "\\qj"}[spec.align])
        level = max(spec.list_level, 1) if spec.list_kind else 0
        if level:
            c.append(f"\\li{level * 720}\\fi-360")
        else:
            if spec.left_px:
                c.append(f"\\li{round(spec.left_px * 15)}")
            if spec.first_px:
                c.append(f"\\fi{round(spec.first_px * 15)}")
        if spec.before_px is not None:
            c.append(f"\\sb{round(spec.before_px * 15)}")
        if spec.after_px is not None:
            c.append(f"\\sa{round(spec.after_px * 15)}")
        if spec.line_pct and abs(spec.line_pct - 100) > 1:
            c.append(f"\\sl{round(spec.line_pct / 100 * 240)}\\slmult1")
        if spec.page_break:
            c.append("\\pagebb")
        if spec.heading:
            c.append(f"\\outlinelevel{spec.heading - 1}")
        return "".join(c)

    def _paragraph(self, spec: ParaSpec, in_table: bool = False) -> str:
        if spec.hr:
            return "\\pard\\plain\\brdrb\\brdrs\\brdrw10\\brsp20 "
        text = self._para_ctrl(spec, in_table) + " "
        if spec.list_kind:
            text += "{" + rtf_escape(self._label(spec)) + "\\tab}"
        else:
            self.counters = []
        for it in spec.items:
            if isinstance(it, RunSpec):
                text += self._run(it)
            elif isinstance(it, BreakSpec):
                text += "\\line "
            elif isinstance(it, ImgSpec):
                text += self._image(it)
        return text

    def _label(self, spec: ParaSpec) -> str:
        depth = min(max(spec.list_level, 1), 3)
        if spec.list_kind == "ul":
            self.counters = []
            return _BULLETS[depth - 1]
        self.counters = (self.counters + [0] * depth)[:depth]
        self.counters[-1] += 1
        n = self.counters[-1]
        return {1: f"{n}.", 2: f"{chr(96 + (n - 1) % 26 + 1)}.", 3: f"{_roman(n)}."}[depth]

    def _run(self, rs: RunSpec) -> str:
        f = rs.fmt
        ctrl = []
        if f.get("font"):
            ctrl.append(f"\\f{self.fonts.index(f['font'])}")
        if f.get("size"):
            ctrl.append(f"\\fs{round(f['size'] * 2)}")
        for key, word in (("bold", "\\b"), ("italic", "\\i"), ("underline", "\\ul"), ("strike", "\\strike"),
                          ("sup", "\\super"), ("sub", "\\sub")):
            if f.get(key):
                ctrl.append(word)
        color = f.get("color") or ("0563c1" if f.get("href") else None)
        if color:
            ctrl.append(f"\\cf{self._cidx(color)}")
        if f.get("bg"):
            ctrl.append(f"\\chshdng0\\chcbpat{self._cidx(f['bg'])}")
        if f.get("href") and not f.get("underline"):
            ctrl.append("\\ul")
        group = "{" + "".join(ctrl) + (" " if ctrl else "") + rtf_escape(rs.text) + "}"
        if f.get("href"):
            url = f["href"].replace("\\", "/").replace('"', "%22")
            return f'{{\\field{{\\*\\fldinst HYPERLINK "{url}"}}{{\\fldrslt {group}}}}}'
        return group

    def _image(self, it: ImgSpec) -> str:
        data = self.images.get(it.name)
        info = _image_info(data) if data else None
        if not info:
            return ""
        kind, w, h = info
        wp, hp = it.w or w, it.h or (it.w * h / w if it.w else h)
        max_w = self.page.text_width_cm() * 96 / 2.54
        if wp > max_w:
            hp, wp = hp * max_w / wp, max_w
        return (f"{{\\pict\\{kind}\\picw{round(w * 26.4583)}\\pich{round(h * 26.4583)}\\picwgoal{round(wp * 15)}\\pichgoal{round(hp * 15)}\n"
                + data.hex() + "}")

    # ---- tablas ----
    def _table(self, spec: TableSpec) -> str:
        nrows = len(spec.rows)
        occupied, grid, ncols = {}, {}, 0
        for r, row in enumerate(spec.rows):
            c = 0
            for cell in row:
                while (r, c) in occupied:
                    c += 1
                rs, cs = min(cell.rowspan, nrows - r), cell.colspan
                for dr in range(rs):
                    for dc in range(cs):
                        occupied[(r + dr, c + dc)] = True
                        grid[(r + dr, c + dc)] = (cell, r, c, rs, cs)
                c += cs
            ncols = max(ncols, c)
        if not nrows or not ncols:
            return ""
        width = TEXT_WIDTH_TWIPS // ncols
        out = []
        for r in range(nrows):
            out.append("\\trowd\\trgaph108\\trleft0\n")
            for c in range(ncols):
                cell, r0, c0, rs, cs = grid.get((r, c), (None, r, c, 1, 1))
                flags = ""
                if spec.border:
                    flags += "".join(f"\\clbrdr{s}\\brdrs\\brdrw10" for s in "tlbr")
                if rs > 1:
                    flags += "\\clvmgf" if r == r0 else "\\clvmrg"
                if cs > 1:
                    flags += "\\clmgf" if c == c0 else "\\clmrg"
                if cell is not None and cell.bg and r == r0 and c == c0:
                    flags += f"\\clcbpat{self._cidx(cell.bg)}"
                out.append(f"{flags}\\cellx{width * (c + 1)}\n")
            for c in range(ncols):
                cell, r0, c0, _, _ = grid.get((r, c), (None, r, c, 1, 1))
                if cell is None or (r, c) != (r0, c0) or not cell.blocks:
                    out.append("\\pard\\intbl\\cell\n")
                    continue
                paras = [self._paragraph(b, True) if isinstance(b, ParaSpec) else "" for b in cell.blocks]
                out.append("\\par\n".join(paras) + "\\cell\n")
            out.append("\\row\n")
        return "".join(out)


def html_to_rtf(html_text: str, images: dict[str, bytes], path: str, page: PageSetup | None = None) -> None:
    """Escribe un .rtf a partir del HTML del editor, sus imágenes {nombre: bytes} y la configuración de la hoja."""
    data = _RtfWriter(parse_html(html_text), images, page).build()
    Path(path).write_bytes(data.encode("ascii", "replace"))
