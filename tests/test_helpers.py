"""Pruebas de las listas auxiliares: símbolos y fechas en español."""
import os
import sys
import unittest
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from isaward.datefmt import DIAS, MESES, date_options  # noqa: E402
from isaward.symbols import SYMBOL_GROUPS, symbols_of  # noqa: E402
from isaward.tools import matches, search_key  # noqa: E402


class Symbols(unittest.TestCase):
    def test_groups_are_not_empty_and_have_no_repeats(self):
        for name, text in SYMBOL_GROUPS.items():
            items = symbols_of(name)
            self.assertGreater(len(items), 5, name)
            self.assertEqual(len(items), len(set(items)), f"símbolos repetidos en {name}")
            for ch in items:
                self.assertLessEqual(len(ch), 2, f"{name}: «{ch}» no es un solo símbolo")

    def test_what_students_need_is_there(self):
        every = "".join(SYMBOL_GROUPS.values())
        for ch in "°²³±×÷≤≥≠≈√π∞αβγΔΣΩ€£¿¡«»—…©®™ñÑáéíóúü":
            self.assertIn(ch, every, ch)


class Dates(unittest.TestCase):
    def test_spanish_formats(self):
        options = date_options(datetime(2026, 11, 22, 14, 5))  # domingo
        self.assertEqual(options[0], "22 de noviembre de 2026")
        self.assertIn("22/11/2026", options)
        self.assertIn("domingo, 22 de noviembre de 2026", options)
        self.assertIn("14:05", options)
        self.assertIn("2:05 p. m.", options)

    def test_twelve_hour_clock_edges(self):
        self.assertIn("12:00 a. m.", date_options(datetime(2026, 1, 1, 0, 0)))
        self.assertIn("12:30 p. m.", date_options(datetime(2026, 1, 1, 12, 30)))
        self.assertIn("11:59 p. m.", date_options(datetime(2026, 1, 1, 23, 59)))

    def test_names(self):
        self.assertEqual(len(MESES), 12)
        self.assertEqual(len(DIAS), 7)
        self.assertEqual(date_options(datetime(2026, 3, 2))[2].split(",")[0], "lunes")


class Search(unittest.TestCase):
    def test_accents_and_case_do_not_matter(self):
        self.assertEqual(search_key("Página ÑANDÚ"), "pagina nandu")
        self.assertTrue(matches("pagina", "Números de página"))
        self.assertTrue(matches("HOJA nueva", "Agregar una hoja nueva"))
        self.assertTrue(matches("", "lo que sea"))
        self.assertFalse(matches("tabla fila", "solo tabla"))


if __name__ == "__main__":
    unittest.main()
