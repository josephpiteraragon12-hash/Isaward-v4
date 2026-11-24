"""Revisa que el catálogo de herramientas, los iconos y la guía estén completos y coherentes (sin Qt).

Estas pruebas hacen cumplir la regla del proyecto: TODA función visible debe estar explicada en la guía (F1).
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from isaward.howto import RECIPES  # noqa: E402
from isaward.icon_defs import ICONS  # noqa: E402
from isaward.tools import EXTRA_SHORTCUTS, GROUP_ORDER, TOOL_BY_ID, TOOLS, icon_of  # noqa: E402

_ARGS = {"l": 4, "pl": 1, "pg": 1, "r": 4, "rf": 4, "e": 4, "ef": 4, "t": 5}
# Iconos que no son botones de la guía
NOT_TOOLS = {"app", "menu"}


class Catalog(unittest.TestCase):
    def test_every_tool_has_a_usable_icon(self):
        for t in TOOLS:
            self.assertIn(icon_of(t), ICONS, t.id)

    def test_every_icon_is_documented_in_the_guide(self):
        """Si alguien dibuja un icono nuevo, tiene que explicarlo en tools.py."""
        used = {icon_of(t) for t in TOOLS}
        missing = [name for name in ICONS if name not in used and name not in NOT_TOOLS]
        self.assertEqual(missing, [], "Iconos sin explicación en la guía: agrégalos a tools.py")

    def test_tool_ids_are_unique_and_complete(self):
        ids = [t.id for t in TOOLS]
        self.assertEqual(len(ids), len(set(ids)))
        for t in TOOLS:
            self.assertIn(t.group, GROUP_ORDER, t.id)
            self.assertTrue(t.label.strip(), t.id)
            self.assertTrue(t.help.strip().endswith((".", "…")), f"{t.id}: la ayuda corta debe ser una frase")
            self.assertGreaterEqual(len(t.help), 15, t.id)

    def test_every_tool_says_where_it_is_and_explains_itself(self):
        for t in TOOLS:
            self.assertTrue(any(w in t.where for w in ("Barra", "Menú")), f"{t.id}: falta «dónde está» (where)")
            self.assertGreaterEqual(len(t.more), 40, f"{t.id}: falta la explicación ampliada (more)")

    def test_shortcuts_are_unique(self):
        shortcuts = [t.shortcut for t in TOOLS if t.shortcut]
        self.assertEqual(len(shortcuts), len(set(shortcuts)), "dos herramientas comparten atajo")

    def test_every_group_has_tools(self):
        for group in GROUP_ORDER:
            self.assertTrue(any(t.group == group for t in TOOLS), group)

    def test_the_questions_people_ask_have_an_answer(self):
        """La guía debe responder: ¿dónde agrego otra hoja? ¿dónde cambio el tamaño de la hoja?"""
        self.assertIn("hoja", TOOL_BY_ID["new_page"].label.lower())
        self.assertIn("página", TOOL_BY_ID["page_break"].label.lower())
        self.assertIn("Hoja → Configurar página", TOOL_BY_ID["page_setup"].where)
        text = " ".join(f"{r.title} {r.keywords}".lower() for r in RECIPES)
        for word in ("hoja nueva", "tamaño", "márgenes", "números de página", "encabezado", "portada", "sangría",
                     "tabla", "pdf"):
            self.assertIn(word, text, word)

    def test_extra_shortcuts_are_wellformed(self):
        for key, what in EXTRA_SHORTCUTS:
            self.assertTrue(key and what)


class Recipes(unittest.TestCase):
    def test_recipes_are_wellformed(self):
        titles = [r.title for r in RECIPES]
        self.assertEqual(len(titles), len(set(titles)))
        for r in RECIPES:
            self.assertGreaterEqual(len(r.steps), 2, r.title)
            self.assertTrue(r.tools, r.title)
            for tool_id in r.tools:
                self.assertIn(tool_id, TOOL_BY_ID, f"{r.title}: herramienta inexistente «{tool_id}»")

    def test_every_important_tool_appears_in_some_recipe(self):
        important = {"page_break", "new_page", "page_setup", "header_footer", "page_number", "paragraph", "symbol",
                     "date", "table", "image", "bullets", "numbering", "find", "pdf", "save_as", "line_spacing"}
        used = {tid for r in RECIPES for tid in r.tools}
        self.assertEqual(important - used, set())

    def test_recipe_names_match_menu_names(self):
        """Los pasos deben nombrar los menús y botones tal como se llaman de verdad."""
        text = " ".join(" ".join(r.steps) for r in RECIPES)
        for name in ("Configurar página", "Encabezado y pie de página", "Números de página", "Salto de página",
                     "Hoja en blanco", "Exportar a PDF", "Vista previa de impresión", "Guardar como"):
            self.assertIn(name, text, name)


class Icons(unittest.TestCase):
    def test_icon_operations_are_well_formed(self):
        for name, ops in ICONS.items():
            for op in ops:
                self.assertIn(op[0], _ARGS, f"{name}: operación desconocida {op[0]}")
                args = list(op[1:])
                if isinstance(args[-1], str) and args[-1].startswith("#"):
                    args.pop()
                self.assertGreaterEqual(len(args), _ARGS[op[0]], f"{name}: {op}")
                if op[0] in ("pl", "pg"):
                    self.assertGreaterEqual(len(args[0]), 2, f"{name}: {op}")


if __name__ == "__main__":
    unittest.main()
