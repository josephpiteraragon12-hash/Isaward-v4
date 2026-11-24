"""Pruebas de la conversión DOCX <-> HTML.  Ejecutar:  python -m unittest discover tests"""
import base64
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from docx import Document  # noqa: E402

from isaward.formats.docx_io import docx_to_html, html_to_docx  # noqa: E402

PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")

QT_STYLE = ('margin-top:0px; margin-bottom:8px; margin-left:0px; margin-right:0px; '
            '-qt-block-indent:0; text-indent:0px;')

# HTML con la misma forma que produce QTextDocument.toHtml()
QT_HTML = f"""<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0//EN" "http://www.w3.org/TR/REC-html40/strict.dtd">
<html><head><meta name="qrichtext" content="1" /><meta charset="utf-8" /><style type="text/css">
p, li {{ white-space: pre-wrap; }}
hr {{ height: 1px; border-width: 0; }}
</style></head><body style=" font-family:'Calibri'; font-size:11pt; font-weight:400; font-style:normal;">
<h1 style=" margin-top:12px; margin-bottom:4px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-size:20pt; font-weight:700;">Título</span></h1>
<p align="center" style=" {QT_STYLE} line-height:115%;">Hola <span style=" font-weight:700;">negrita</span> <span style=" font-family:'Arial'; font-size:14pt; font-style:italic; text-decoration: underline; color:#ff0000; background-color:#ffff00;">otro</span> x<span style=" vertical-align:super;">2</span></p>
<ul style="margin-top: 0px; margin-bottom: 0px; margin-left: 0px; margin-right: 0px; -qt-list-indent: 1;"><li style=" margin-top:0px;" >Uno</li>
<li>Dos</li>
<ul style="margin-top: 0px; -qt-list-indent: 2;"><li>Sub</li></ul></ul>
<ol style="margin-top: 0px; -qt-list-indent: 1;"><li>Ana</li>
<li>Beto</li></ol>
<table border="1" style=" margin-top:0px;" cellspacing="0" cellpadding="4" width="100%">
<tr><td colspan="2" bgcolor="#dddddd"><p style=" {QT_STYLE}">Celda doble</p></td></tr>
<tr><td><p style=" {QT_STYLE}">a</p></td><td><p style=" {QT_STYLE}">b</p></td></tr></table>
<p style=" {QT_STYLE}"><a href="https://example.com"><span style=" text-decoration: underline; color:#0000ff;">enlace</span></a></p>
<hr />
<p style=" {QT_STYLE} page-break-before:always;">Otra página</p>
<p style=" {QT_STYLE}"><img src="img_test.png" width="100" height="50" /></p>
<p style=" {QT_STYLE}"><br /></p>
</body></html>"""


class HtmlToDocx(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.path = os.path.join(self.tmp, "a.docx")
        html_to_docx(QT_HTML, {"img_test.png": PNG_1X1}, self.path)
        self.doc = Document(self.path)

    def test_heading_and_alignment(self):
        p = self.doc.paragraphs
        self.assertEqual(p[0].style.name, "Heading 1")
        self.assertEqual(p[0].text, "Título")
        self.assertEqual(p[1].alignment, 1)  # centrado
        self.assertAlmostEqual(p[1].paragraph_format.line_spacing, 1.15)

    def test_run_formats(self):
        runs = {r.text: r for r in self.doc.paragraphs[1].runs}
        self.assertTrue(runs["negrita"].bold)
        otro = runs["otro"]
        self.assertTrue(otro.italic)
        self.assertTrue(otro.underline)
        self.assertEqual(str(otro.font.color.rgb), "FF0000")
        self.assertEqual(otro.font.name, "Arial")
        self.assertEqual(otro.font.size.pt, 14)
        self.assertTrue(runs["2"].font.superscript)
        self.assertIn('w:fill="FFFF00"', otro._r.xml)

    def test_lists(self):
        names = [p.style.name for p in self.doc.paragraphs if p.style.name.startswith("List")]
        self.assertEqual(names, ["List Bullet", "List Bullet", "List Bullet 2",
                                 "List Number", "List Number"])

    def test_table_merge(self):
        t = self.doc.tables[0]
        self.assertEqual((len(t.rows), len(t.columns)), (2, 2))
        self.assertIs(t.cell(0, 0)._tc, t.cell(0, 1)._tc)
        self.assertEqual(t.cell(0, 0).text, "Celda doble")
        self.assertEqual(t.cell(1, 1).text, "b")
        self.assertEqual(t.style.name, "Table Grid")
        self.assertIn('w:fill="DDDDDD"', t.cell(0, 0)._tc.xml)

    def test_link_hr_break_image(self):
        xml = self.doc.element.xml
        self.assertIn("<w:hyperlink", xml)
        self.assertTrue(any(r.target_ref == "https://example.com"
                            for r in self.doc.part.rels.values()))
        self.assertIn("<w:pBdr>", xml)
        self.assertTrue(any(p.paragraph_format.page_break_before for p in self.doc.paragraphs))
        self.assertEqual(len(self.doc.inline_shapes), 1)

    def test_empty_paragraph_has_no_line_break(self):
        self.assertNotIn("<w:br/>", self.doc.paragraphs[-1]._p.xml)

    def test_page_size_is_a4(self):
        self.assertAlmostEqual(self.doc.sections[0].page_width.cm, 21, places=1)


class DocxToHtml(unittest.TestCase):
    def test_reads_what_python_docx_writes(self):
        tmp = tempfile.mkdtemp()
        src = os.path.join(tmp, "src.docx")
        d = Document()
        d.add_heading("Mi título", level=1)
        p = d.add_paragraph("Texto ")
        p.add_run("fuerte").bold = True
        d.add_paragraph("Punto", style="List Bullet")
        d.add_paragraph("Primero", style="List Number")
        d.add_page_break()
        d.add_paragraph("Final").add_run().add_picture(os.path.join(tmp, "x.png")
                                                       if self._write(tmp, "x.png") else "")
        t = d.add_table(rows=2, cols=2)
        t.style = "Table Grid"
        t.cell(0, 0).merge(t.cell(0, 1)).text = "Unidas"
        t.cell(1, 0).text, t.cell(1, 1).text = "x", "y"
        d.save(src)

        html, images = docx_to_html(src)
        self.assertIn("<h1", html)
        self.assertIn("Mi título", html)
        self.assertIn("font-weight:700", html)
        self.assertIn("<ul>", html)
        self.assertIn("<ol", html)
        self.assertIn("page-break-before:always", html)
        self.assertIn('colspan="2"', html)
        self.assertIn('border="1"', html)
        self.assertEqual(list(images), ["docx_img1.png"])
        self.assertIn('src="docx_img1.png"', html)

    @staticmethod
    def _write(tmp, name):
        with open(os.path.join(tmp, name), "wb") as fh:
            fh.write(PNG_1X1)
        return True

    def test_round_trip_keeps_text(self):
        tmp = tempfile.mkdtemp()
        first = os.path.join(tmp, "1.docx")
        html_to_docx(QT_HTML, {"img_test.png": PNG_1X1}, first)
        html, images = docx_to_html(first)
        second = os.path.join(tmp, "2.docx")
        html_to_docx(html, images, second)
        before = [p.text for p in Document(first).paragraphs]
        after = [p.text for p in Document(second).paragraphs]
        self.assertEqual(before, after)
        for word in ("Título", "negrita", "Celda doble", "enlace", "Otra página"):
            self.assertIn(word, html)
        self.assertIn("https://example.com", html)


class Performance(unittest.TestCase):
    def test_large_document_reads_in_reasonable_time(self):
        """Regresión: leer estilos párrafo por párrafo llegó a tardar minutos (era lentísimo en PCs modestas)."""
        import time
        para = ('<p style="margin-top:0px; margin-bottom:8px">' + "Lorem ipsum <b>dolor</b> sit amet, consectetur. " * 6
                + "</p>")
        html = "<html><body style=\"font-family:'Calibri'; font-size:11pt\">" + para * 600 + "</body></html>"
        path = os.path.join(tempfile.mkdtemp(), "grande.docx")
        html_to_docx(html, {}, path)
        start = time.time()
        out, _ = docx_to_html(path)
        self.assertLess(time.time() - start, 8, "docx_to_html se volvió demasiado lento")
        self.assertEqual(out.count("<p "), 600)


if __name__ == "__main__":
    unittest.main()
