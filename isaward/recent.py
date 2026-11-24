"""Lista de archivos recientes (lógica pura, sin Qt)."""
from __future__ import annotations

import os

MAX_RECENT = 8


def add_recent(items: list[str], path: str, limit: int = MAX_RECENT) -> list[str]:
    """Pone `path` primero, sin repetirlo, y recorta la lista."""
    norm = os.path.abspath(path)
    rest = [p for p in items if os.path.normcase(os.path.abspath(p)) != os.path.normcase(norm)]
    return ([norm] + rest)[:limit]


def only_existing(items: list[str]) -> list[str]:
    return [p for p in items if os.path.isfile(p)]
