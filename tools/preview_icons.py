"""Dibuja todos los iconos en una imagen para revisarlos sin abrir la app.

    python tools/preview_icons.py [salida.png]

También sirve para crear el icono del .exe:  python tools/preview_icons.py --ico assets/isaward.ico
Requiere Pillow (solo para desarrollo; la app no lo necesita).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from isaward.icon_defs import ICONS  # noqa: E402

INK = "#2B3A44"
FONT_DIR = "/usr/share/fonts/truetype/dejavu/"


def _font(size, style):
    name = ("DejaVuSerif" if "s" in style else "DejaVuSans")
    name += {"b": "-Bold", "i": "-Italic"}.get("b" if "b" in style else "i" if "i" in style else "", "")
    for path in (FONT_DIR + name + ".ttf", "C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/arial.ttf"):
        try:
            return ImageFont.truetype(path, int(size))
        except OSError:
            continue
    return ImageFont.load_default()


def render(name, size=96, color=INK, transparent=True):
    k = size / 24
    ss = 4  # supermuestreo para suavizar bordes
    img = Image.new("RGBA", (size * ss, size * ss), (0, 0, 0, 0) if transparent else (255, 255, 255, 255))
    d = ImageDraw.Draw(img)
    s = k * ss
    for op in ICONS[name]:
        kind, args = op[0], list(op[1:])
        col = color
        if args and isinstance(args[-1], str) and args[-1].startswith("#"):
            col = args.pop()
        w = max(1, round(1.8 * s))
        if kind == "l":
            x1, y1, x2, y2 = (v * s for v in args)
            d.line([(x1, y1), (x2, y2)], fill=col, width=w)
            for cx, cy in ((x1, y1), (x2, y2)):
                d.ellipse([cx - w / 2, cy - w / 2, cx + w / 2, cy + w / 2], fill=col)
        elif kind == "pl":
            pts = [(x * s, y * s) for x, y in args[0]]
            d.line(pts, fill=col, width=w, joint="curve")
            for cx, cy in pts:
                d.ellipse([cx - w / 2, cy - w / 2, cx + w / 2, cy + w / 2], fill=col)
        elif kind == "pg":
            d.polygon([(x * s, y * s) for x, y in args[0]], fill=col)
        elif kind in ("r", "rf"):
            x, y, rw, rh = (v * s for v in args)
            if kind == "rf":
                d.rounded_rectangle([x, y, x + rw, y + rh], radius=1.5 * s, fill=col)
            else:
                d.rounded_rectangle([x, y, x + rw, y + rh], radius=1.5 * s, outline=col, width=w)
        elif kind in ("e", "ef"):
            cx, cy, rx, ry = (v * s for v in args)
            box = [cx - rx, cy - ry, cx + rx, cy + ry]
            if kind == "ef":
                d.ellipse(box, fill=col)
            else:
                d.ellipse(box, outline=col, width=w)
        elif kind == "t":
            text, cx, cy, fs, style = args[:5]
            d.text((cx * s, cy * s), text, fill=col, font=_font(fs * s * 0.95, style), anchor="mm")
    return img.resize((size, size), Image.LANCZOS)


def sheet(path, cols=8, cell=96):
    names = list(ICONS)
    rows = -(-len(names) // cols)
    out = Image.new("RGB", (cols * (cell + 24), rows * (cell + 40)), "#F4F6F8")
    d = ImageDraw.Draw(out)
    for i, name in enumerate(names):
        x, y = (i % cols) * (cell + 24) + 12, (i // cols) * (cell + 40) + 8
        out.paste(render(name, cell), (x, y), render(name, cell))
        d.text((x + cell / 2, y + cell + 12), name, fill="#445", anchor="mm",
               font=_font(11, ""))
    out.save(path)


def make_ico(path):
    base = render("app", 256)
    base.save(path, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--ico":
        make_ico(sys.argv[2])
        print("Icono creado:", sys.argv[2])
    else:
        target = sys.argv[1] if len(sys.argv) > 1 else "iconos.png"
        sheet(target)
        print("Hoja de iconos creada:", target)
