"""Fechas y horas en español para el botón «Fecha y hora» (sin Qt, con prueba)."""
from __future__ import annotations

from datetime import datetime

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre"]
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def date_options(now: datetime) -> list[str]:
    """Formas de escribir la fecha y la hora de `now`, de la más común a la menos."""
    mes, dia = MESES[now.month - 1], DIAS[now.weekday()]
    hour12 = now.hour % 12 or 12
    suffix = "a. m." if now.hour < 12 else "p. m."
    return [
        f"{now.day} de {mes} de {now.year}",
        f"{now.day:02d}/{now.month:02d}/{now.year}",
        f"{dia}, {now.day} de {mes} de {now.year}",
        f"{mes.capitalize()} {now.day}, {now.year}",
        f"{now.day:02d}-{now.month:02d}-{now.year}",
        f"{now.year}-{now.month:02d}-{now.day:02d}",
        f"{mes.capitalize()} de {now.year}",
        f"{now.hour:02d}:{now.minute:02d}",
        f"{hour12}:{now.minute:02d} {suffix}",
        f"{now.day} de {mes} de {now.year}, {now.hour:02d}:{now.minute:02d}",
    ]
