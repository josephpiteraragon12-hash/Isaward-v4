"""Detecta el formato REAL de un archivo mirando su contenido (no solo su extensión).  No usa Qt.

Sirve porque a veces un .doc es en realidad un RTF, o un .txt es un .docx renombrado.
"""
from __future__ import annotations

import zipfile


def sniff_format(path: str) -> str:
    """Devuelve: 'docx', 'odt', 'rtf', 'doc', 'pdf', 'zip' u 'other' (texto, html, markdown...)."""
    with open(path, "rb") as fh:
        head = fh.read(8)
    if head.startswith(b"\xef\xbb\xbf"):
        head = head[3:]
    if head.startswith(b"{\\rtf"):
        return "rtf"
    if head.startswith(b"%PDF"):
        return "pdf"
    if head.startswith(b"\xd0\xcf\x11\xe0"):
        return "doc"
    if head.startswith(b"PK"):
        try:
            with zipfile.ZipFile(path) as zf:
                names = set(zf.namelist())
                if "word/document.xml" in names:
                    return "docx"
                if "mimetype" in names and zf.read("mimetype").startswith(b"application/vnd.oasis.opendocument.text"):
                    return "odt"
        except zipfile.BadZipFile:
            pass
        return "zip"
    return "other"


def looks_binary(path: str) -> bool:
    """True si el archivo tiene bytes nulos al inicio (no es texto)."""
    with open(path, "rb") as fh:
        chunk = fh.read(4096)
    return b"\x00" in chunk and not chunk.startswith((b"\xff\xfe", b"\xfe\xff"))
