"""Constantes compartidas por la interfaz."""

DEFAULT_FONT = "Calibri"
DEFAULT_SIZE = 11            # puntos
PAGE_WIDTH_PX = 794          # A4 a 96 ppp
PAGE_MARGIN_PX = 96          # 2,54 cm
TEXT_WIDTH_PX = PAGE_WIDTH_PX - 2 * PAGE_MARGIN_PX   # 602 px: ancho útil de la hoja
MAX_EMBED_IMAGE_PX = 1600    # las imágenes más anchas se reducen al insertarlas (ahorra memoria)
FONT_SIZES = [8, 9, 10, 10.5, 11, 12, 14, 16, 18, 20, 24, 28, 32, 36, 48, 72]
AUTOSAVE_MS = 120_000       # copia automática de seguridad cada 2 minutos (solo si hay cambios)

# Interruptor de emergencia de las hojas: True = el texto se reparte en hojas con separación visible.
# Si en algún equipo las hojas se vieran mal, ponerlo en False vuelve a la hoja continua de la versión 0.2.
PAGINATE = True
