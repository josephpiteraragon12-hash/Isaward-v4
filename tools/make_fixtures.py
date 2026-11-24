"""Crea los archivos de muestra de tests/data/ con LibreOffice (solo hace falta al desarrollar).

    python tools/make_fixtures.py

Parte de un .docx generado por IsaWard y lo convierte a .odt, .rtf, .doc y .pdf.
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)

from isaward.formats.docx_io import html_to_docx  # noqa: E402

DATA = os.path.join(ROOT, "tests", "data")
STYLE = "margin-top:0px; margin-bottom:8px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"

HTML = f"""<html><head><meta charset="utf-8"></head><body style=" font-family:'Calibri'; font-size:11pt;">
<h1 style=" margin-top:12px; margin-bottom:4px;"><span style=" font-size:20pt; font-weight:700;">Título de la muestra</span></h1>
<p align="center" style=" {STYLE} line-height:115%;">Canción: ñandú, café, €5 — “comillas” y <span style=" font-weight:700;">negrita</span> <span style=" font-family:'Arial'; font-size:14pt; font-style:italic; text-decoration: underline; color:#ff0000; background-color:#ffff00;">rojo subrayado</span> x<span style=" vertical-align:super;">2</span></p>
<p style=" {STYLE}">Párrafo normal con <a href="https://example.com"><span style=" text-decoration: underline; color:#0563c1;">un enlace</span></a> y texto tachado <span style=" text-decoration: line-through;">viejo</span>.</p>
<ul><li>Uno</li><li>Dos</li><ul><li>Sub</li></ul></ul>
<ol><li>Ana</li><li>Beto</li></ol>
<table border="1" cellspacing="0" cellpadding="4" width="100%">
<tr><td colspan="2" bgcolor="#dddddd"><p style=" {STYLE}">Celda doble</p></td></tr>
<tr><td><p style=" {STYLE}">a</p></td><td><p style=" {STYLE}">b</p></td></tr></table>
<p style=" {STYLE}"><img src="muestra.png" width="90" height="45" /></p>
<p style=" {STYLE} page-break-before:always;">Segunda página</p>
</body></html>"""


def make_page_fixtures(soffice):
    """hoja.docx/.odt/.rtf: Carta horizontal, márgenes propios, encabezado, pie con campos y portada distinta."""
    from isaward.pagesetup import PageSetup
    ps = PageSetup().with_size("Carta", True).with_margins(2.0, 2.0, 3.0, 1.5)
    ps.header_left, ps.header_right = "Colegio San Isa", "Informe de Biología"
    ps.footer_center, ps.first_page_different = "Página {pagina} de {paginas}", True
    para = '<p style="margin-bottom:8px">' + "Texto de prueba para ocupar varias hojas. " * 60 + "</p>"
    html = ("<html><body style=\"font-family:'Calibri'; font-size:11pt\"><h1>Portada</h1>" + para
            + '<p style="page-break-before:always">Segunda hoja</p>' + para * 2 + "</body></html>")
    html_to_docx(html, {}, os.path.join(DATA, "hoja.docx"), ps)
    for fmt in ("odt", "rtf"):
        subprocess.run([soffice, "--headless", "--convert-to", fmt, "--outdir", DATA,
                        os.path.join(DATA, "hoja.docx")], check=True, capture_output=True)
        print("creado", f"hoja.{fmt}")


def main():
    os.makedirs(DATA, exist_ok=True)
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (90, 45), "#0E7C86")
    ImageDraw.Draw(img).rectangle([10, 10, 50, 35], fill="#FFE45C")
    png = os.path.join(DATA, "muestra.png")
    img.save(png)
    with open(png, "rb") as fh:
        html_to_docx(HTML, {"muestra.png": fh.read()}, os.path.join(DATA, "muestra.docx"))
    os.remove(png)
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        sys.exit("Necesito LibreOffice (soffice) para convertir.")
    for fmt in ("odt", "rtf", "doc", "pdf"):
        subprocess.run([soffice, "--headless", "--convert-to", fmt, "--outdir", DATA,
                        os.path.join(DATA, "muestra.docx")], check=True, capture_output=True)
        print("creado", f"muestra.{fmt}")
    make_page_fixtures(soffice)


if __name__ == "__main__":
    main()
