"""Lector de .doc de Word 97-2003 (formato binario antiguo).  No usa Qt.

    html, imagenes = doc_to_html("carta.doc")

Solo recupera el TEXTO (párrafos, enlaces y tablas sencillas): el formato binario guarda el
estilo en estructuras aparte que todavía no se leen (ver ROADMAP.md).  Para conservar el formato,
abre el archivo en Word o LibreOffice y guárdalo como .docx.
"""
from __future__ import annotations

import re
import struct
from pathlib import Path

from .htmlout import esc, para, span, wrap
from .ole import OleError, OleFile


class DocError(Exception):
    pass


def doc_to_html(path: str) -> tuple[str, dict[str, bytes]]:
    try:
        text = extract_text(Path(path).read_bytes())
    except OleError as err:
        raise DocError(str(err)) from err
    if not text.strip("\r\x07\x0c \n"):
        raise DocError("No encontré texto en este documento.")
    return _text_to_html(text), {}


def extract_text(data: bytes) -> str:
    ole = OleFile(data)
    if "EncryptedPackage" in ole.names():
        raise DocError("El documento está protegido con contraseña. Quítale la contraseña en Word y vuelve a intentar.")
    word = ole.stream("WordDocument")
    if word is None or len(word) < 0x1A6 or word[:2] != b"\xec\xa5":
        raise DocError("Este archivo no parece ser un documento de Word.")
    n_fib = struct.unpack_from("<H", word, 2)[0]
    flags = struct.unpack_from("<H", word, 0x0A)[0]
    if flags & 0x0100:
        raise DocError("El documento está protegido con contraseña. Quítale la contraseña en Word y vuelve a intentar.")
    if n_fib < 0xC1:  # Word 6/95: el texto va seguido, sin tabla de piezas
        fc_min, fc_mac = struct.unpack_from("<II", word, 0x18)
        return word[fc_min:fc_mac].decode("cp1252", errors="replace")

    table = ole.stream("1Table" if flags & 0x0200 else "0Table")
    if table is None:
        raise DocError("El documento está dañado (falta la tabla de texto).")
    fc_clx, lcb_clx = struct.unpack_from("<II", word, 0x1A2)
    ccp_text = struct.unpack_from("<i", word, 0x4C)[0]
    clx = table[fc_clx:fc_clx + lcb_clx]

    i, plc = 0, b""
    while i < len(clx):
        kind = clx[i]
        if kind == 1:  # Prc: propiedades que no necesitamos
            i += 3 + struct.unpack_from("<H", clx, i + 1)[0]
        elif kind == 2:  # Pcdt: la tabla de piezas de texto
            size = struct.unpack_from("<I", clx, i + 1)[0]
            plc = clx[i + 5:i + 5 + size]
            break
        else:
            break
    if not plc:
        raise DocError("El documento está dañado (no se encontró el texto).")

    n = (len(plc) - 4) // 12
    cps = struct.unpack_from("<%dI" % (n + 1), plc, 0)
    pieces = []
    for k in range(n):
        fc = struct.unpack_from("<I", plc, (n + 1) * 4 + k * 8 + 2)[0]
        length = cps[k + 1] - cps[k]
        if fc & 0x40000000:  # texto comprimido: un byte por letra
            start = (fc & 0x3FFFFFFF) // 2
            pieces.append(word[start:start + length].decode("cp1252", errors="replace"))
        else:  # UTF-16
            pieces.append(word[fc:fc + length * 2].decode("utf-16-le", errors="replace"))
    return "".join(pieces)[:ccp_text if ccp_text > 0 else None]


_HYPERLINK = re.compile(r'HYPERLINK\s+(?!\\l)(?:"([^"]+)"|(\S+))')


def _clean(text: str) -> list[tuple[str, str | None]]:
    """Quita los campos de Word (se queda con su resultado) y devuelve [(carácter, enlace)]."""
    out: list[tuple[str, str | None]] = []
    stack: list[dict] = []
    for ch in text:
        if ch == "\x13":
            stack.append({"instr": [], "result": False, "href": None})
        elif ch == "\x14" and stack:
            top = stack[-1]
            m = _HYPERLINK.search("".join(top["instr"]))
            top["href"] = (m.group(1) or m.group(2)) if m else None
            top["result"] = True
        elif ch == "\x15":
            if stack:
                stack.pop()
        else:
            hidden = [f for f in stack if not f["result"]]
            if hidden:
                hidden[-1]["instr"].append(ch)
                continue
            href = next((f["href"] for f in reversed(stack) if f["href"]), None)
            out.append((ch, href))
    return out


def _segments_html(segs: list[tuple[str, str | None]]) -> str:
    parts, buf, cur = [], "", None
    for ch, href in segs + [("", object())]:
        if href != cur and buf:
            parts.append(span(esc(buf), {"href": cur} if cur else {}))
            buf = ""
        cur = href
        buf += ch
    return "".join(parts)


def _text_to_html(text: str) -> str:
    tokens, cur = [], []
    for ch, href in _clean(text):
        if ch == "\r":
            tokens.append(("p", cur)); cur = []
        elif ch == "\x07":
            tokens.append(("cell", cur)); cur = []
        elif ch == "\x0c":
            if cur:
                tokens.append(("p", cur)); cur = []
            tokens.append(("pb", None))
        elif ch == "\x0b":
            cur.append(("\n", href))
        elif ch == "\x1e":
            cur.append(("-", href))
        elif ch in "\t\xa0" or ch >= " ":
            cur.append((ch, href))
    if cur:
        tokens.append(("p", cur))

    html: list[str] = []
    table: list[list] | None = None
    row: list = []
    n_cols: int | None = None
    page_break = False

    def close_table():
        nonlocal table, row, n_cols
        if row and table is not None:
            table.append(row)
        if table:
            body = "".join("<tr>" + "".join(f"<td><p>{_segments_html(c)}</p></td>" for c in r) + "</tr>" for r in table)
            html.append(f'<table border="1" cellspacing="0" cellpadding="4" width="100%">{body}</table>')
        table, row, n_cols = None, [], None

    for kind, segs in tokens:
        if kind == "pb":
            page_break = True
        elif kind == "p":
            close_table()
            css = ["white-space:pre-wrap", "margin-top:0px", "margin-bottom:8px"]
            if page_break:
                css.append("page-break-before:always")
                page_break = False
            content = _segments_html(segs).replace("\n", "<br/>")
            html.append(para("p", content, css))
        else:  # fin de celda
            empty = not any(c.strip() for c, _ in segs)
            if table is None:
                if empty:
                    continue
                table, row = [], []
            if empty and row and (n_cols is None or len(row) >= n_cols):  # marca de fin de fila
                n_cols = n_cols or len(row)
                table.append(row)
                row = []
            else:
                row.append(segs)
    close_table()
    return wrap("".join(html))
