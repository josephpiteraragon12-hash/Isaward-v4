"""Configuración de la hoja: tamaño, orientación, márgenes, encabezado, pie y números de página.

Lógica pura (sin Qt) para poder probarla.  Un `PageSetup` viaja con el documento: se lee y se escribe
en .docx/.rtf/.odt, se guarda en la copia de seguridad y lo usa el editor para dibujar las hojas.

Los textos de encabezado y pie pueden llevar estas marcas, que se reemplazan en cada hoja:
    {pagina}   número de la hoja        {paginas}   total de hojas
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, fields

CM_TO_PX = 96 / 2.54  # el editor trabaja a 96 puntos por pulgada

# nombre -> (ancho, alto) en centímetros, con la hoja en vertical
PAGE_SIZES: dict[str, tuple[float, float]] = {
    "A4": (21.0, 29.7),
    "Carta": (21.59, 27.94),
    "Oficio": (21.59, 33.02),
    "Legal": (21.59, 35.56),
    "A5": (14.8, 21.0),
    "A3": (29.7, 42.0),
}
SIZE_LABELS = {
    "A4": "A4  (21 × 29,7 cm)",
    "Carta": "Carta / Letter  (21,6 × 27,9 cm)",
    "Oficio": "Oficio  (21,6 × 33 cm)",
    "Legal": "Legal  (21,6 × 35,6 cm)",
    "A5": "A5  (14,8 × 21 cm)",
    "A3": "A3  (29,7 × 42 cm)",
}
CUSTOM = "Personalizado"

# nombre -> (arriba, abajo, izquierda, derecha) en cm
MARGIN_PRESETS: dict[str, tuple[float, float, float, float]] = {
    "Normal  (2,54 cm por todos lados)": (2.54, 2.54, 2.54, 2.54),
    "Estrecho  (1,27 cm)": (1.27, 1.27, 1.27, 1.27),
    "Moderado  (2,54 arriba y abajo, 1,91 a los lados)": (2.54, 2.54, 1.91, 1.91),
    "Ancho  (2,54 arriba y abajo, 5,08 a los lados)": (2.54, 2.54, 5.08, 5.08),
}

NUMBER_POSITIONS = {
    "none": "Sin números de página",
    "footer_center": "Abajo, al centro",
    "footer_right": "Abajo, a la derecha",
    "footer_left": "Abajo, a la izquierda",
    "header_right": "Arriba, a la derecha",
    "header_center": "Arriba, al centro",
    "header_left": "Arriba, a la izquierda",
}
NUMBER_FORMATS = {
    "{pagina}": "1",
    "Página {pagina}": "Página 1",
    "Página {pagina} de {paginas}": "Página 1 de 5",
    "- {pagina} -": "- 1 -",
}

_TOKEN = re.compile(r"\{(pagina|paginas)\}")


@dataclass
class PageSetup:
    width_cm: float = 21.0       # medidas de la hoja tal como se ve (ya con la orientación aplicada)
    height_cm: float = 29.7
    top_cm: float = 2.54
    bottom_cm: float = 2.54
    left_cm: float = 2.54
    right_cm: float = 2.54
    header_left: str = ""
    header_center: str = ""
    header_right: str = ""
    footer_left: str = ""
    footer_center: str = ""
    footer_right: str = ""
    number_pos: str = "none"
    number_fmt: str = "{pagina}"
    first_page_different: bool = False   # la primera hoja (portada) va sin encabezado ni pie

    # ---------------------------------------------------------------- medidas
    @property
    def landscape(self) -> bool:
        return self.width_cm > self.height_cm

    def size_name(self) -> str:
        """Nombre del tamaño estándar que coincide (en cualquier orientación) o 'Personalizado'."""
        short, long_ = sorted((self.width_cm, self.height_cm))
        for name, (w, h) in PAGE_SIZES.items():
            if abs(short - w) < 0.15 and abs(long_ - h) < 0.15:
                return name
        return CUSTOM

    def with_size(self, name: str, landscape: bool) -> "PageSetup":
        w, h = PAGE_SIZES[name]
        out = PageSetup(**asdict(self))
        out.width_cm, out.height_cm = (h, w) if landscape else (w, h)
        return out

    def with_margins(self, top: float, bottom: float, left: float, right: float) -> "PageSetup":
        out = PageSetup(**asdict(self))
        out.top_cm, out.bottom_cm, out.left_cm, out.right_cm = top, bottom, left, right
        return out

    def page_px(self) -> tuple[float, float]:
        return round(self.width_cm * CM_TO_PX, 1), round(self.height_cm * CM_TO_PX, 1)

    def margins_px(self) -> tuple[float, float, float, float]:
        """(izquierda, arriba, derecha, abajo) en píxeles."""
        return (round(self.left_cm * CM_TO_PX, 1), round(self.top_cm * CM_TO_PX, 1),
                round(self.right_cm * CM_TO_PX, 1), round(self.bottom_cm * CM_TO_PX, 1))

    def text_width_cm(self) -> float:
        return self.width_cm - self.left_cm - self.right_cm

    # ---------------------------------------------------------------- encabezado y pie
    def composed(self) -> dict[str, tuple[str, str, str]]:
        """Encabezado y pie finales (izquierda, centro, derecha), ya con el número de página incluido."""
        slots = {"header": [self.header_left, self.header_center, self.header_right],
                 "footer": [self.footer_left, self.footer_center, self.footer_right]}
        if self.number_pos in NUMBER_POSITIONS and self.number_pos != "none":
            part, side = self.number_pos.split("_")
            idx = {"left": 0, "center": 1, "right": 2}[side]
            number = self.number_fmt or "{pagina}"
            slots[part][idx] = f"{slots[part][idx]}  {number}".strip() if slots[part][idx] else number
        return {k: tuple(v) for k, v in slots.items()}  # type: ignore[misc]

    def has_decorations(self) -> bool:
        return any(any(s) for s in self.composed().values())

    # ---------------------------------------------------------------- guardar / leer
    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict | None) -> "PageSetup":
        """Construye desde un diccionario ignorando datos inválidos (nunca falla)."""
        base = cls()
        if not isinstance(data, dict):
            return base
        for f in fields(cls):
            if f.name not in data:
                continue
            value, default = data[f.name], getattr(base, f.name)
            try:
                if isinstance(default, bool):
                    setattr(base, f.name, bool(value))
                elif isinstance(default, float):
                    setattr(base, f.name, float(value))
                else:
                    setattr(base, f.name, str(value))
            except (TypeError, ValueError):
                pass
        return base.sanitized()

    def sanitized(self) -> "PageSetup":
        """Corrige valores imposibles (hojas diminutas, márgenes que no dejan espacio para escribir)."""
        out = PageSetup(**asdict(self))
        out.width_cm = min(max(out.width_cm, 5.0), 100.0)
        out.height_cm = min(max(out.height_cm, 5.0), 150.0)
        for name in ("top_cm", "bottom_cm", "left_cm", "right_cm"):
            setattr(out, name, min(max(getattr(out, name), 0.0), 15.0))
        if out.left_cm + out.right_cm > out.width_cm - 2.0:   # que quede al menos 2 cm para escribir
            scale = max(out.width_cm - 2.0, 0.0) / max(out.left_cm + out.right_cm, 0.01)
            out.left_cm, out.right_cm = out.left_cm * scale, out.right_cm * scale
        if out.top_cm + out.bottom_cm > out.height_cm - 2.0:
            scale = max(out.height_cm - 2.0, 0.0) / max(out.top_cm + out.bottom_cm, 0.01)
            out.top_cm, out.bottom_cm = out.top_cm * scale, out.bottom_cm * scale
        if out.number_pos not in NUMBER_POSITIONS:
            out.number_pos = "none"
        return out


def expand_tokens(text: str, page: int, pages: int) -> str:
    """Reemplaza {pagina} y {paginas} en un texto de encabezado o pie."""
    return _TOKEN.sub(lambda m: str(page if m.group(1) == "pagina" else pages), text)


def split_slots(text: str, align: str | None = None) -> tuple[str, str, str]:
    """Reparte el texto de un encabezado/pie en (izquierda, centro, derecha).

    Word y LibreOffice separan las tres zonas con tabuladores ("izq<TAB>centro<TAB>der").
    Sin tabuladores se usa la alineación del párrafo ('center', 'right' o None = izquierda).
    """
    parts = [x.strip() for x in text.split("\t")]
    if len(parts) == 1:
        return ("", parts[0], "") if align == "center" else (("", "", parts[0]) if align == "right" else (parts[0], "", ""))
    if len(parts) == 2:
        return parts[0], parts[1], ""
    return parts[0], parts[1], " ".join(x for x in parts[2:] if x)


def from_points(width_pt: float, height_pt: float) -> PageSetup:
    """Hoja con el tamaño de un PDF (que se mide en puntos de 1/72 de pulgada)."""
    return PageSetup(width_cm=round(width_pt / 72 * 2.54, 2), height_cm=round(height_pt / 72 * 2.54, 2)).sanitized()


def twips_to_cm(twips: float) -> float:
    return twips / 567.0


def cm_to_twips(cm: float) -> int:
    return round(cm * 567)
