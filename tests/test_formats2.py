"""Pruebas de los formatos del segmento 2 (ODT, RTF, DOC, PDF) y de recuperación/recientes.

Usan los archivos de tests/data/, creados con LibreOffice por tools/make_fixtures.py.
"""
import base64
import importlib.util
import os
import shutil
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from isaward.formats.doc_io import DocError, doc_to_html  # noqa: E402
from isaward.formats.docx_io import docx_to_html, html_to_docx  # noqa: E402
from isaward.formats.odt_io import odt_to_html  # noqa: E402
from isaward.formats.ole import OleError, OleFile  # noqa: E402
from isaward.formats.pdf_io import PdfError, _pages_to_html, pdf_to_html  # noqa: E402
from isaward.formats.rtf_io import html_to_rtf, rtf_escape, rtf_to_html  # noqa: E402
from isaward.formats.sniff import looks_binary, sniff_format  # noqa: E402
from isaward.recent import add_recent, only_existing  # noqa: E402
from isaward.recovery import clear_recovery, has_recovery, read_recovery, write_recovery  # noqa: E402

DATA = os.path.join(os.path.dirname(__file__), "data")
PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")

try:
    import pypdf  # noqa: F401
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False


def sample(name):
    return os.path.join(DATA, name)


class SameContentInEveryFormat(unittest.TestCase):
    """El mismo documento, guardado por LibreOffice como docx/odt/rtf, debe leerse igual."""
    WORDS = ["Título de la muestra", "Canción: ñandú, café, €5", "“comillas”", "negrita", "un enlace",
             "viejo", "Celda doble", "Segunda página", "https://example.com"]

    def check(self, html):
        for word in self.WORDS:
            self.assertIn(word, html, word)
        self.assertIn("<h1", html)
        self.assertIn('colspan="2"', html)
        self.assertIn("<img", html)
        self.assertIn("page-break-before:always", html)
        self.assertIn("font-weight:700", html)
        self.assertIn("color:#ff0000", html)
        self.assertIn("background-color:#ffff00", html)
        self.assertIn("text-decoration:line-through", html)
        self.assertIn("vertical-align:super", html)
        self.assertIn("<ul", html)
        self.assertIn("<ol", html)

    def test_docx(self):
        html, images = docx_to_html(sample("muestra.docx"))
        self.check(html)
        self.assertEqual(len(images), 1)

    def test_odt(self):
        html, images = odt_to_html(sample("muestra.odt"))
        self.check(html)
        self.assertEqual(len(images), 1)
        self.assertTrue(list(images)[0].endswith(".png"))

    def test_rtf(self):
        html, images = rtf_to_html(sample("muestra.rtf"))
        self.check(html)
        self.assertEqual(len(images), 1)
        self.assertIn('width="90" height="45"', html)


class RtfReader(unittest.TestCase):
    def test_text_formats_unicode_and_hex(self):
        rtf = (r"{\rtf1\ansi\ansicpg1252\deff0{\fonttbl{\f0 Arial;}{\f1 Courier New;}}"
               r"{\colortbl;\red255\green0\blue0;}\pard Hola \b negrita\b0  y \cf1 rojo\cf0  \u8364\'80 \'e1\'f1"
               r"\f1  mono\par}")
        path = os.path.join(tempfile.mkdtemp(), "a.rtf")
        with open(path, "w", encoding="latin-1") as fh:
            fh.write(rtf)
        html, _ = rtf_to_html(path)
        self.assertIn("font-weight:700\">negrita", html)
        self.assertIn("color:#ff0000\">rojo", html)
        self.assertIn("€ áñ", html)  # \u8364 + su respaldo \'80 cuentan como UN solo carácter
        self.assertEqual(html.count("€"), 1)
        self.assertIn("font-family:'Courier New'", html)

    def _read(self, rtf):
        path = os.path.join(tempfile.mkdtemp(), "a.rtf")
        with open(path, "w", encoding="latin-1") as fh:
            fh.write(rtf)
        return rtf_to_html(path)

    def test_word_style_table_with_merged_cells(self):
        html, _ = self._read(
            r"{\rtf1\ansi\deff0{\fonttbl{\f0 Arial;}}"
            r"\trowd\clmgf\cellx2000\clmrg\cellx4000\pard\intbl A\cell\pard\intbl \cell\row"
            r"\trowd\cellx2000\cellx4000\pard\intbl B\cell\pard\intbl C\cell\row"
            r"\pard Despues\par}")
        self.assertEqual(html.count("<tr>"), 2)
        self.assertIn('colspan="2"', html)
        self.assertLess(html.index("</table>"), html.index("Despues"))

    def test_picture_and_hyperlink_and_ignored_groups(self):
        hexdata = PNG_1X1.hex()
        html, images = self._read(
            r"{\rtf1\ansi{\*\generator Algo;}{\header Cabecera}\pard "
            r"{\pict\pngblip\picwgoal300\pichgoal150 " + hexdata + r"}"
            r"{\field{\*\fldinst HYPERLINK \"http://a.b/\"}{\fldrslt enlace}}\par}".replace('\\"', '"'))
        self.assertEqual(list(images), ["rtf_img1.png"])
        self.assertEqual(images["rtf_img1.png"], PNG_1X1)
        self.assertIn('width="20" height="10"', html)
        self.assertIn('<a href="http://a.b/">', html)
        self.assertNotIn("Cabecera", html)
        self.assertNotIn("Algo", html)

    def test_heading_by_style_name_and_alignment(self):
        html, _ = self._read(
            r"{\rtf1\ansi{\fonttbl{\f0 Arial;}}{\stylesheet{\s0 Normal;}{\s1 heading 1;}}"
            r"\pard\s1\qc Titulo\par\pard\s0\qr Derecha\par}")
        self.assertIn("<h1", html)
        self.assertIn("text-align:center", html)
        self.assertIn("text-align:right", html)


class NestedLists(unittest.TestCase):
    def test_rtf_word_style_levels(self):
        rtf = (r"{\rtf1\ansi\deff0{\fonttbl{\f0 Arial;}}"
               r"{\*\listtable{\list\listtemplateid1{\listlevel\levelnfc23{\leveltext \'01\u8226 ?;}}"
               r"{\listlevel\levelnfc4{\leveltext \'02\'01.;}}\listid1}}"
               r"{\*\listoverridetable{\listoverride\listid1\listoverridecount0\ls1}}"
               r"\pard\ls1\ilvl0 {\listtext\u8226\tab}Uno\par\pard\ls1\ilvl1 {\listtext a.\tab}Sub\par"
               r"\pard\ls1\ilvl0 Dos\par\pard Fin\par}")
        path = os.path.join(tempfile.mkdtemp(), "n.rtf")
        with open(path, "w", encoding="latin-1") as fh:
            fh.write(rtf)
        html, _ = rtf_to_html(path)
        self.assertIn("<ul><li>Uno<ol", html)
        self.assertIn("lower-alpha", html)
        self.assertIn("</ol></li><li>Dos</li></ul>", html)

    @unittest.skipUnless(importlib.util.find_spec("odf"), "odfpy no está instalado")
    def test_odt_nested_list_and_missing_default_font(self):
        from odf.opendocument import OpenDocumentText
        from odf.text import List, ListItem, ListLevelStyleBullet, ListLevelStyleNumber, ListStyle, P
        doc = OpenDocumentText()
        style = ListStyle(name="L1")
        style.addElement(ListLevelStyleBullet(level=1, bulletchar="•"))
        style.addElement(ListLevelStyleNumber(level=2, numformat="a"))
        doc.automaticstyles.addElement(style)
        outer, item, inner, sub = List(stylename="L1"), ListItem(), List(), ListItem()
        item.addElement(P(text="Uno"))
        sub.addElement(P(text="Sub"))
        inner.addElement(sub)
        item.addElement(inner)
        outer.addElement(item)
        doc.text.addElement(outer)
        path = os.path.join(tempfile.mkdtemp(), "n.odt")
        doc.save(path)
        html, _ = odt_to_html(path)
        self.assertIn("<li>Uno<ol", html)
        self.assertIn("lower-alpha", html)


class RtfWriter(unittest.TestCase):
    HTML = ('<html><body style="font-family:\'Calibri\'; font-size:11pt;">'
            '<h1><span style="font-size:20pt; font-weight:700;">Título {con} \\ llaves</span></h1>'
            '<p align="center">Ñandú €5 <b>negrita</b> <i>cursiva</i> <u>sub</u> '
            '<span style="color:#ff0000; background-color:#ffff00;">rojo</span> '
            '<a href="https://example.com">enlace</a></p>'
            '<ul><li>Uno</li><ul><li>Dos</li></ul></ul><ol><li>A</li><li>B</li></ol>'
            '<table border="1"><tr><td colspan="2" bgcolor="#dddddd">Doble</td></tr>'
            '<tr><td>a</td><td>b</td></tr></table>'
            '<p style="page-break-before:always">Otra</p><hr/>'
            '<p><img src="i.png" width="40" height="20"/></p></body></html>')

    def setUp(self):
        self.path = os.path.join(tempfile.mkdtemp(), "salida.rtf")
        html_to_rtf(self.HTML, {"i.png": PNG_1X1}, self.path)
        with open(self.path, "rb") as fh:
            self.raw = fh.read()

    def test_output_is_valid_ascii_with_balanced_braces(self):
        text = self.raw.decode("ascii")  # si hubiera algún carácter no ASCII, falla aquí
        depth = 0
        for i, ch in enumerate(text):
            if ch in "{}" and text[i - 1] != "\\":
                depth += 1 if ch == "{" else -1
                self.assertGreaterEqual(depth, 0)
        self.assertEqual(depth, 0)
        self.assertTrue(text.startswith("{\\rtf1"))

    def test_escaping(self):
        self.assertEqual(rtf_escape("a{b}c\\"), "a\\{b\\}c\\\\")
        self.assertEqual(rtf_escape("ñ€"), "\\u241?\\u8364?")
        self.assertEqual(rtf_escape("😀"), "\\u-10179?\\u-8704?")

    def test_reads_back_with_our_reader(self):
        html, images = rtf_to_html(self.path)
        for needle in ("Título {con} \\ llaves", "Ñandú €5", "negrita", "cursiva", "enlace", "Doble", "Otra",
                       "https://example.com", "#ff0000", "#ffff00", 'colspan="2"', "page-break-before", "<img"):
            self.assertIn(needle, html, needle)
        self.assertIn("•&emsp;Uno", html)  # las listas se guardan como texto con viñeta y tabulación
        self.assertIn("1.", html)
        self.assertEqual(list(images.values()), [PNG_1X1])

    def test_survives_docx_round_trip_text(self):
        html, images = rtf_to_html(self.path)
        out = os.path.join(tempfile.mkdtemp(), "x.docx")
        html_to_docx(html, images, out)
        from docx import Document
        text = "\n".join(p.text for p in Document(out).paragraphs)
        self.assertIn("Ñandú €5", text)


class OldWordDoc(unittest.TestCase):
    def test_extracts_text_links_and_table(self):
        html, images = doc_to_html(sample("muestra.doc"))
        for word in ("Título de la muestra", "Canción: ñandú, café, €5", "“comillas”", "Segunda página",
                     "Ana", "Beto"):
            self.assertIn(word, html)
        self.assertIn('<a href="https://example.com/">un enlace</a>', html)
        self.assertEqual(html.count("<tr>"), 2)
        self.assertIn("Celda doble", html)
        self.assertEqual(images, {})

    def test_rejects_things_that_are_not_word(self):
        path = os.path.join(tempfile.mkdtemp(), "malo.doc")
        with open(path, "wb") as fh:
            fh.write(b"esto no es un doc")
        with self.assertRaises(OleError):
            with open(path, "rb") as fh:
                OleFile(fh.read())
        with self.assertRaises(DocError):
            doc_to_html(path)

    def test_truncated_file_gives_a_friendly_error(self):
        with open(sample("muestra.doc"), "rb") as fh:
            data = fh.read()
        path = os.path.join(tempfile.mkdtemp(), "cortado.doc")
        with open(path, "wb") as fh:
            fh.write(data[:1500])
        with self.assertRaises(DocError):
            doc_to_html(path)

    def test_ole_streams(self):
        with open(sample("muestra.doc"), "rb") as fh:
            ole = OleFile(fh.read())
        self.assertIn("WordDocument", ole.names())
        self.assertTrue(ole.stream("WordDocument").startswith(b"\xec\xa5"))


@unittest.skipUnless(HAS_PYPDF, "pypdf no está instalado")
class PdfReader(unittest.TestCase):
    def test_reads_text_of_every_page(self):
        html, _ = pdf_to_html(sample("muestra.pdf"))
        for word in ("Título de la muestra", "Canción: ñandú, café, €5", "Celda doble", "Segunda página"):
            self.assertIn(word, html)
        self.assertIn("<ul>", html)
        self.assertIn("<ol>", html)
        self.assertNotIn("\uf0b7", html)

    def test_blank_pdf_is_reported_as_scanned(self):
        from pypdf import PdfWriter
        path = os.path.join(tempfile.mkdtemp(), "vacio.pdf")
        writer = PdfWriter()
        writer.add_blank_page(200, 200)
        with open(path, "wb") as fh:
            writer.write(fh)
        with self.assertRaises(PdfError) as ctx:
            pdf_to_html(path)
        self.assertIn("escaneada", str(ctx.exception))

    def test_paragraph_rebuilding_heuristics(self):
        lines = ["Esta es una frase larga que continúa en la siguiente línea porque el texto se envuelve y",
                 "sigue con minúscula hasta terminar el párrafo con una guion-",
                 "ado y un final de oración completo.",
                 "Nuevo párrafo corto.",
                 "• primer punto", "• segundo punto", "1. paso uno", "2. paso dos", "12"]
        html = _pages_to_html(["\n".join(lines)])
        self.assertEqual(html.count("<p "), 2)
        self.assertIn("guionado y un final", html)
        self.assertIn("<ul><li>primer punto</li><li>segundo punto</li></ul>", html)
        self.assertIn("<ol><li>paso uno</li><li>paso dos</li></ol>", html)
        self.assertNotIn(">12<", html)  # número de página descartado


class FormatDetection(unittest.TestCase):
    def test_sniff_by_content(self):
        expected = {"muestra.docx": "docx", "muestra.odt": "odt", "muestra.rtf": "rtf", "muestra.doc": "doc",
                    "muestra.pdf": "pdf"}
        for name, kind in expected.items():
            self.assertEqual(sniff_format(sample(name)), kind, name)

    def test_extension_does_not_fool_it(self):
        tmp = tempfile.mkdtemp()
        disguised = os.path.join(tmp, "carta.txt")
        shutil.copy(sample("muestra.rtf"), disguised)
        self.assertEqual(sniff_format(disguised), "rtf")
        plain = os.path.join(tmp, "nota.md")
        with open(plain, "w", encoding="utf-8") as fh:
            fh.write("# Hola\n")
        self.assertEqual(sniff_format(plain), "other")
        self.assertFalse(looks_binary(plain))
        blob = os.path.join(tmp, "programa.exe")
        with open(blob, "wb") as fh:
            fh.write(b"MZ\x90\x00\x03\x00\x00\x00" + b"\x00" * 100)
        self.assertTrue(looks_binary(blob))

    def test_dotx_and_docm_templates_open(self):
        tmp = tempfile.mkdtemp()
        main = "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
        for ext, ctype in ((".dotx", "application/vnd.openxmlformats-officedocument.wordprocessingml.template.main+xml"),
                           (".docm", "application/vnd.ms-word.document.macroEnabled.main+xml")):
            out = os.path.join(tmp, "plantilla" + ext)
            with zipfile.ZipFile(sample("muestra.docx")) as zin, zipfile.ZipFile(out, "w") as zout:
                for item in zin.infolist():
                    data = zin.read(item.filename)
                    if item.filename == "[Content_Types].xml":
                        data = data.decode("utf-8").replace(main, ctype).encode("utf-8")
                    zout.writestr(item, data)
            html, _ = docx_to_html(out)
            self.assertIn("Título de la muestra", html, ext)


class RecoveryAndRecent(unittest.TestCase):
    def test_recovery_round_trip(self):
        folder = os.path.join(tempfile.mkdtemp(), "recovery")
        self.assertFalse(has_recovery(folder))
        shared = b"imagen"
        write_recovery(folder, "<p>Hola ñ</p>", {"a.png": shared, "a&amp;.png": shared}, "C:/x/carta.docx", "carta.docx")
        self.assertTrue(has_recovery(folder))
        html, images, meta = read_recovery(folder)
        self.assertEqual(html, "<p>Hola ñ</p>")
        self.assertEqual(images, {"a.png": shared, "a&amp;.png": shared})
        self.assertEqual((meta["original"], meta["title"]), ("C:/x/carta.docx", "carta.docx"))
        write_recovery(folder, "<p>Nuevo</p>", {}, None, "Documento sin título")  # sobrescribe
        self.assertEqual(read_recovery(folder)[0], "<p>Nuevo</p>")
        clear_recovery(folder)
        self.assertIsNone(read_recovery(folder))

    def test_recovery_survives_interrupted_swap(self):
        folder = os.path.join(tempfile.mkdtemp(), "recovery")
        write_recovery(folder, "<p>Completo</p>", {}, None, "x")
        os.rename(folder, folder + ".tmp")  # se cortó justo entre borrar y renombrar
        self.assertEqual(read_recovery(folder)[0], "<p>Completo</p>")

    def test_recent_list(self):
        tmp = tempfile.mkdtemp()
        files = []
        for name in "abc":
            path = os.path.join(tmp, name + ".docx")
            open(path, "w").close()
            files.append(path)
        items = []
        for path in files:
            items = add_recent(items, path)
        items = add_recent(items, files[0])  # vuelve a abrir el primero: sube al principio, sin repetirse
        self.assertEqual([os.path.basename(p) for p in items], ["a.docx", "c.docx", "b.docx"])
        self.assertEqual(len(add_recent(items, os.path.join(tmp, "z.docx"), limit=2)), 2)
        os.remove(files[1])
        self.assertEqual(len(only_existing(items)), 2)


if __name__ == "__main__":
    unittest.main()
