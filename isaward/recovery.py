"""Copia de seguridad automática para recuperar el trabajo si el programa se cierra mal.

La carpeta de recuperación guarda el HTML del documento, sus imágenes y un pequeño JSON con el nombre
original.  Se escribe en una carpeta temporal que luego reemplaza a la anterior, así nunca queda un
estado a medias.  Lógica pura (sin Qt) para poder probarla.
"""
from __future__ import annotations

import json
import os
import shutil
import time


def write_recovery(folder: str, html: str, images: dict[str, bytes], original: str | None, title: str,
                   page: dict | None = None) -> None:
    tmp = folder + ".tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(os.path.join(tmp, "images"))
    mapping: dict[str, str] = {}
    stored: dict[int, str] = {}
    for name, data in images.items():
        if id(data) not in stored:
            stored[id(data)] = f"images/{len(stored)}.bin"
            with open(os.path.join(tmp, stored[id(data)]), "wb") as fh:
                fh.write(data)
        mapping[name] = stored[id(data)]
    with open(os.path.join(tmp, "recovery.html"), "w", encoding="utf-8") as fh:
        fh.write(html)
    meta = {"original": original, "title": title, "saved": time.strftime("%H:%M"), "images": mapping,
            "page": page or {}}
    with open(os.path.join(tmp, "recovery.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False)
    shutil.rmtree(folder, ignore_errors=True)
    os.replace(tmp, folder)


def _valid_folder(folder: str) -> str | None:
    for candidate in (folder, folder + ".tmp"):  # .tmp: se cortó justo al cambiar de carpeta
        if os.path.isfile(os.path.join(candidate, "recovery.json")) and os.path.isfile(
                os.path.join(candidate, "recovery.html")):
            return candidate
    return None


def has_recovery(folder: str) -> bool:
    return _valid_folder(folder) is not None


def read_recovery(folder: str):
    """(html, imagenes, meta) o None si no hay nada que recuperar."""
    found = _valid_folder(folder)
    if found is None:
        return None
    try:
        with open(os.path.join(found, "recovery.json"), encoding="utf-8") as fh:
            meta = json.load(fh)
        with open(os.path.join(found, "recovery.html"), encoding="utf-8") as fh:
            html = fh.read()
        images = {}
        for name, rel in meta.get("images", {}).items():
            with open(os.path.join(found, rel), "rb") as fh:
                images[name] = fh.read()
    except (OSError, ValueError):
        return None
    return html, images, meta


def clear_recovery(folder: str) -> None:
    shutil.rmtree(folder, ignore_errors=True)
    shutil.rmtree(folder + ".tmp", ignore_errors=True)
