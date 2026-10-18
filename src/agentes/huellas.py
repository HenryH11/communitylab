"""Utilidades para calcular huellas SHA-256 reproducibles."""

import hashlib
from pathlib import Path


def calcular_sha256_lf(ruta: str | Path) -> str:
    """Calcula SHA-256 normalizando los saltos CRLF a LF."""
    contenido = Path(ruta).read_bytes()
    contenido_lf = contenido.replace(b"\r\n", b"\n")

    return hashlib.sha256(contenido_lf).hexdigest()