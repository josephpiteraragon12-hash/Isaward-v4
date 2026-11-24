"""Lector mínimo de contenedores OLE2 (el formato de los .doc, .xls y .ppt antiguos).  No usa Qt.

Solo lectura y solo lo necesario: abrir un flujo (stream) por su nombre.
"""
from __future__ import annotations

import struct

MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
_SPECIAL = 0xFFFFFFFA  # a partir de aquí los números de sector son marcas (fin de cadena, libre, etc.)


class OleError(Exception):
    pass


class OleFile:
    def __init__(self, data: bytes):
        if data[:8] != MAGIC or len(data) < 512:
            raise OleError("No es un archivo de Office antiguo válido.")
        self.data = data
        self.sector_size = 1 << struct.unpack_from("<H", data, 0x1E)[0]
        self.mini_size = 1 << struct.unpack_from("<H", data, 0x20)[0]
        n_fat, dir_start, _, cutoff, minifat_start, n_minifat, difat_start, n_difat = struct.unpack_from(
            "<IIIIIIII", data, 0x2C)
        self.cutoff = cutoff
        per_sector = self.sector_size // 4

        difat = list(struct.unpack_from("<109I", data, 0x4C))
        sector = difat_start
        for _ in range(n_difat):
            if sector >= _SPECIAL:
                break
            values = struct.unpack("<%dI" % per_sector, self._sector(sector))
            difat.extend(values[:-1])
            sector = values[-1]
        self.fat: list[int] = []
        for sid in [s for s in difat if s < _SPECIAL][:n_fat]:
            self.fat.extend(struct.unpack("<%dI" % per_sector, self._sector(sid)))

        directory = self._chain(dir_start)
        self.entries: list[dict] = []
        for i in range(0, len(directory) - 127, 128):
            e = directory[i:i + 128]
            name_len = struct.unpack_from("<H", e, 64)[0]
            size = struct.unpack_from("<Q", e, 120)[0]
            if self.sector_size == 512:
                size &= 0xFFFFFFFF
            self.entries.append({"name": e[:max(name_len - 2, 0)].decode("utf-16-le", "replace"),
                                 "type": e[66], "start": struct.unpack_from("<I", e, 116)[0], "size": size})
        root = next((e for e in self.entries if e["type"] == 5), None)
        if root is None:
            raise OleError("El archivo está dañado (no tiene directorio).")
        self.mini_stream = self._chain(root["start"])[:root["size"]]
        mini_fat = self._chain(minifat_start) if minifat_start < _SPECIAL else b""
        self.mini_fat = list(struct.unpack("<%dI" % (len(mini_fat) // 4), mini_fat))

    def _sector(self, sid: int) -> bytes:
        offset = (sid + 1) * self.sector_size
        chunk = self.data[offset:offset + self.sector_size]
        if len(chunk) < self.sector_size:
            raise OleError("El archivo está incompleto o dañado.")
        return chunk

    def _chain(self, start: int) -> bytes:
        parts, seen = [], set()
        sid = start
        while sid < _SPECIAL and sid not in seen and sid < len(self.fat):
            seen.add(sid)
            parts.append(self._sector(sid))
            sid = self.fat[sid]
        return b"".join(parts)

    def _mini_chain(self, start: int) -> bytes:
        parts, seen = [], set()
        sid = start
        while sid < _SPECIAL and sid not in seen and sid < len(self.mini_fat):
            seen.add(sid)
            offset = sid * self.mini_size
            parts.append(self.mini_stream[offset:offset + self.mini_size])
            sid = self.mini_fat[sid]
        return b"".join(parts)

    def names(self) -> list[str]:
        return [e["name"] for e in self.entries if e["type"] == 2]

    def stream(self, name: str) -> bytes | None:
        for e in self.entries:
            if e["type"] == 2 and e["name"].lower() == name.lower():
                raw = self._mini_chain(e["start"]) if e["size"] < self.cutoff else self._chain(e["start"])
                return raw[:e["size"]]
        return None
