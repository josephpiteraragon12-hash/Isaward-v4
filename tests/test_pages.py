"""Pruebas de la configuración de hoja (tamaño, márgenes, encabezado, pie, números) y su lectura/escritura."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from docx import Document  # noqa: E402

from isaward.formats.docx_io import html_to_docx, read_docx  # noqa: E402
from isaward.formats.odt_io import read_odt  # noqa: E402
from isaward.formats.rtf_io import html_to_rtf, read_rtf  # noqa: E402
from isaward.pagesetup import (CM_TO_PX, MARGIN_PRESETS, NUMBER_FORMATS, NUMBER_POSITIONS, PAGE_SIZES,  # noqa: E402
                               PageSetup, expand_tokens, split_slots)

DATA = os.path.join(os.path.dirname(__file__), "data")
LONG = "<html><body><p>" + "Texto de prueba. " * 400 + '</p><p style="page-break-before:always">Otra hoja</p></body></html>'


def school_page() -> PageSetup:
    ps = PageSetup().with_size("Carta", True).with_margins(2.0, 2.0, 3.0, 1.5)
    ps.header_left, ps.header_right = "Colegio San Isa", "Informe de Biología"
    ps.footer_center, ps.first_page_different = "Página {pagina} de {paginas}", True
    return ps


class PageSetupModel(unittest.TestCase):
    def test_default_is_a4_portrait(self):
        ps = PageSetup()
        self.assertEqual((ps.size_name(), ps.landscape), ("A4", False))
        w, h = ps.page_px()
        self.assertAlmostEqual(w, 793.7, delta=0.2)
        self.assertAlmostEqual(h, 1122.5, delta=0.2)
        self.assertAlmostEqual(ps.margins_px()[0], 2.54 * CM_TO_PX, delta=0.1)

    def test_every_size_and_orientation(self):
        for name in PAGE_SIZES:
            for landscape in (False, True):
                ps = PageSetup().with_size(name, landscape)
                self.assertEqual((ps.size_name(), ps.landscape), (name, landscape), name)

    def test_custom_size_is_named_custom(self):
        ps = PageSetup(width_cm=18.0, height_cm=25.0)
        self.assertEqual(ps.size_name(), "Personalizado")

    def test_margin_presets_are_valid(self):
        for name, (t, b, l, r) in MARGIN_PRESETS.items():
            ps = PageSetup().with_margins(t, b, l, r)
            self.assertEqual(ps.sanitized().left_cm, l, name)

    def test_sanitize_fixes_impossible_values(self):
        ps = PageSetup(left_cm=15.0, right_cm=15.0, top_cm=-3.0, width_cm=2.0, number_pos="loquesea").sanitized()
        self.assertGreaterEqual(ps.width_cm, 5.0)
        self.assertGreaterEqual(ps.text_width_cm(), 2.0 - 1e-6)
        self.assertEqual((ps.top_cm, ps.number_pos), (0.0, "none"))

    def test_from_dict_never_fails(self):
        self.assertEqual(PageSetup.from_dict(None), PageSetup())
        self.assertEqual(PageSetup.from_dict({"width_cm": "basura", "top_cm": "3"}).top_cm, 3.0)
        ps = school_page()
        self.assertEqual(PageSetup.from_dict(ps.to_dict()), ps)

    def test_page_numbers_are_composed_into_the_right_place(self):
        for pos in NUMBER_POSITIONS:
            if pos == "none":
                continue
            ps = PageSetup(number_pos=pos, number_fmt="Pág. {pagina}")
            part, side = pos.split("_")
            idx = {"left": 0, "center": 1, "right": 2}[side]
            slots = ps.composed()[part]
            self.assertEqual(slots[idx], "Pág. {pagina}")
            self.assertEqual([s for i, s in enumerate(slots) if i != idx], ["", ""])
        merged = PageSetup(footer_right="Informe", number_pos="footer_right").composed()["footer"][2]
        self.assertEqual(merged, "Informe  {pagina}")
        self.assertFalse(PageSetup().has_decorations())
        self.assertTrue(PageSetup(number_pos="footer_center").has_decorations())

    def test_tokens(self):
        self.assertEqual(expand_tokens("Página {pagina} de {paginas}", 2, 7), "Página 2 de 7")
        for fmt in NUMBER_FORMATS:
            self.assertIn("{pagina}", fmt)

    def test_split_slots(self):
        self.assertEqual(split_slots("a\tb\tc"), ("a", "b", "c"))
        self.assertEqual(split_slots("\tcentro"), ("", "centro", ""))
        self.assertEqual(split_slots("\t\tder"), ("", "", "der"))
        self.assertEqual(split_slots("solo", "center"), ("", "solo", ""))
        self.assertEqual(split_slots("solo", "right"), ("", "", "solo"))
        self.assertEqual(split_slots("solo"), ("solo", "", ""))


class PageInDocx(unittest.TestCase):
    def test_round_trip_keeps_everything(self):
        ps = school_page()
        path = os.path.join(tempfile.mkdtemp(), "h.docx")
        html_to_docx(LONG, {}, path, ps)
        back = read_docx(path)[2]
        self.assertEqual(back, ps.sanitized())

    def test_orientation_and_size_in_the_file(self):
        path = os.path.join(tempfile.mkdtemp(), "h.docx")
        html_to_docx(LONG, {}, path, school_page())
        sec = Document(path).sections[0]
        self.assertEqual(int(sec.orientation), 1)  # horizontal
        self.assertAlmostEqual(sec.page_width.cm, 27.94, places=1)
        self.assertAlmostEqual(sec.left_margin.cm, 3.0, places=1)

    def test_page_number_is_a_real_word_field(self):
        path = os.path.join(tempfile.mkdtemp(), "h.docx")
        html_to_docx(LONG, {}, path, school_page())
        footer = Document(path).sections[0].footer._element.xml
        self.assertIn("PAGE", footer)
        self.assertIn("NUMPAGES", footer)
        self.assertIn('w:fldCharType="begin"', footer)

    def test_no_header_when_not_requested(self):
        path = os.path.join(tempfile.mkdtemp(), "plain.docx")
        html_to_docx(LONG, {}, path)
        sec = Document(path).sections[0]
        self.assertTrue(sec.header.is_linked_to_previous)
        self.assertFalse(read_docx(path)[2].has_decorations())

    def test_word_style_header_with_tabs_and_fields(self):
        """Un encabezado como el que arma Word: izquierda<TAB>centro<TAB>derecha, con campo PAGE."""
        ps = PageSetup(header_left="Izq", header_center="Centro", header_right="Der", footer_right="{pagina}")
        path = os.path.join(tempfile.mkdtemp(), "t.docx")
        html_to_docx(LONG, {}, path, ps)
        back = read_docx(path)[2]
        self.assertEqual((back.header_left, back.header_center, back.header_right), ("Izq", "Centro", "Der"))
        self.assertEqual(back.footer_right, "{pagina}")

    def test_real_libreoffice_style_file(self):
        ps = read_docx(os.path.join(DATA, "hoja.docx"))[2]
        self.assertEqual((ps.size_name(), ps.landscape), ("Carta", True))
        self.assertTrue(ps.first_page_different)


class PageInOtherFormats(unittest.TestCase):
    def check_school(self, ps, places=1):
        self.assertEqual((ps.size_name(), ps.landscape), ("Carta", True))
        for got, want in ((ps.top_cm, 2.0), (ps.bottom_cm, 2.0), (ps.left_cm, 3.0), (ps.right_cm, 1.5)):
            self.assertAlmostEqual(got, want, places=places)
        self.assertEqual((ps.header_left, ps.header_center, ps.header_right), ("Colegio San Isa", "", "Informe de Biología"))
        self.assertEqual(ps.footer_center, "Página {pagina} de {paginas}")
        self.assertTrue(ps.first_page_different)

    def test_odt_from_libreoffice(self):
        self.check_school(read_odt(os.path.join(DATA, "hoja.odt"))[2])

    def test_rtf_from_libreoffice(self):
        self.check_school(read_rtf(os.path.join(DATA, "hoja.rtf"))[2])

    def test_rtf_written_by_isaward_reads_back(self):
        path = os.path.join(tempfile.mkdtemp(), "h.rtf")
        ps = school_page()
        ps.header_center = "Título ñ €"
        html_to_rtf(LONG, {}, path, ps)
        back = read_rtf(path)[2]
        self.assertEqual((back.size_name(), back.landscape), ("Carta", True))
        self.assertEqual(back.header_center, "Título ñ €")
        self.assertEqual(back.footer_center, "Página {pagina} de {paginas}")
        self.assertTrue(back.first_page_different)
        self.assertAlmostEqual(back.left_cm, 3.0, places=1)

    def test_rtf_header_does_not_leak_into_the_body(self):
        path = os.path.join(tempfile.mkdtemp(), "h.rtf")
        html_to_rtf(LONG, {}, path, school_page())
        html = read_rtf(path)[0]
        self.assertNotIn("Colegio San Isa", html)
        self.assertIn("Otra hoja", html)

    def test_files_without_page_info_give_defaults(self):
        self.assertEqual(read_odt(os.path.join(DATA, "muestra.odt"))[2].size_name(), "A4")


if __name__ == "__main__":
    unittest.main()
