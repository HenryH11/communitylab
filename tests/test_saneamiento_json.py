"""Saneamiento de la Semana 5: los JSON versionados están en UTF-8 limpio. Sin IA ni red."""

import json
import re
import unittest
from pathlib import Path

from src.datos.limpieza import detectar_mojibake

RAIZ = Path(__file__).resolve().parents[1]
CARPETAS = ("configuracion", "docs", "src", "tests")
# Una letra, un "?" y otra letra: rastro de un archivo guardado en ASCII o en una página de códigos sin tildes.
TILDE_PERDIDA = re.compile(r"[A-Za-z]\?[a-z]|¿?\?[A-Z][a-z]")
# Pendiente de DS: el holdout congelado perdió las tildes al guardarse; se repara con una nueva versión y su SHA-256.
PENDIENTES = {"tests/fixtures/holdout_final_analisis_semana3.json"}


def archivos_json():
    return sorted(r for carpeta in CARPETAS for r in (RAIZ / carpeta).rglob("*.json") if "__pycache__" not in r.parts)


def textos(valor):
    """Todas las cadenas de un JSON, para no confundir la sintaxis con el contenido."""
    if isinstance(valor, str):
        yield valor
    elif isinstance(valor, dict):
        for clave, contenido in valor.items():
            yield clave
            yield from textos(contenido)
    elif isinstance(valor, list):
        for contenido in valor:
            yield from textos(contenido)


class PruebasSaneamientoJson(unittest.TestCase):
    def test_utf8_sin_bom_y_json_valido(self):
        for ruta in archivos_json():
            with self.subTest(ruta=ruta.relative_to(RAIZ).as_posix()):
                contenido = ruta.read_bytes()
                self.assertFalse(contenido.startswith(b"\xef\xbb\xbf"), "tiene BOM")
                json.loads(contenido.decode("utf-8"))

    def test_sin_mojibake_ni_tildes_perdidas(self):
        for ruta in archivos_json():
            relativa = ruta.relative_to(RAIZ).as_posix()
            if relativa in PENDIENTES:
                continue
            with self.subTest(ruta=relativa):
                cadenas = list(textos(json.loads(ruta.read_text(encoding="utf-8"))))
                self.assertEqual([c for c in cadenas if detectar_mojibake(c)], [])
                self.assertEqual([c for c in cadenas if TILDE_PERDIDA.search(c) and "://" not in c], [])

    def test_los_pendientes_siguen_detectandose(self):
        """Cuando DS repare el holdout, esta prueba avisa para sacarlo de PENDIENTES."""
        for relativa in PENDIENTES:
            with self.subTest(ruta=relativa):
                texto = (RAIZ / relativa).read_text(encoding="utf-8")
                self.assertRegex(texto, TILDE_PERDIDA)


if __name__ == "__main__":
    unittest.main()
