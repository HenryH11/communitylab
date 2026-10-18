"""Saneamiento de la Semana 5: los JSON versionados están en UTF-8 limpio y con 4 espacios. Sin IA ni red."""

import json
import re
import unittest
from pathlib import Path

from src.datos.limpieza import detectar_mojibake

RAIZ = Path(__file__).resolve().parents[1]
CARPETAS = ("configuracion", "docs", "src", "tests")
# Rastros de un archivo guardado en ASCII o en una página de códigos sin tildes:
# una letra, un "?" y otra letra ("Despu?s"), o un "¿" perdido al abrir una pregunta ("?C?mo ...?").
LETRA_INTERROGACION_LETRA = re.compile(r"[A-Za-z]\?[a-z]")
APERTURA_PERDIDA = re.compile(r"(?:^|[\s(\"'])\?[A-Z][^?¿]*\?")
URL = re.compile(r"\S+://\S+")
# Pendiente de DS: el holdout congelado perdió las tildes al guardarse; se repara con una nueva versión y su SHA-256.
PENDIENTES = {"tests/fixtures/holdout_final_analisis_semana3.json"}
# Matriz 3 (cierre técnico): JSON con indentación homogénea de 4 espacios, también en lo que escribe src/datos.
INDENTACION_DISTINTA_DE_4 = re.compile(r"indent\s*=\s*(?!4\b)\d+")


def archivos_json():
    return sorted(r for carpeta in CARPETAS for r in (RAIZ / carpeta).rglob("*.json") if "__pycache__" not in r.parts)


def tiene_tilde_perdida(cadena):
    # Solo se quitan los segmentos de URL; el resto de la cadena se sigue revisando.
    cadena = URL.sub(" ", cadena)
    # Con tantos "¿" como "?", cada "?" puede cerrar una pregunta ("¿Python?claro"): es puntuación.
    if LETRA_INTERROGACION_LETRA.search(cadena) and cadena.count("?") > cadena.count("¿"):
        return True
    return bool(APERTURA_PERDIDA.search(cadena))


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
                self.assertEqual([c for c in cadenas if tiene_tilde_perdida(c)], [])

    def test_criterio_de_tildes_perdidas(self):
        """Contraejemplos de la revisión de DA (Jhonattan, 17 oct)."""
        casos = {
            "¿Python?Claro, lo usamos ayer.": False,
            "¿Python?claro, lo usamos ayer.": False,
            "?Python es obligatorio": False,
            "despu?s de la clase": True,
            "https://ejemplo.com/x y sigue despu?s": True,
            "?C?mo me inscribo?": True,
            "?Cuando empieza el curso?": True,
            "Gracias, ¿y despu?s?": True,
            "Más info en https://ejemplo.com/?id=3": False,
        }
        for cadena, esperado in casos.items():
            with self.subTest(cadena=cadena):
                self.assertIs(tiene_tilde_perdida(cadena), esperado)

    def test_indentacion_de_4_espacios(self):
        for ruta in archivos_json():
            with self.subTest(ruta=ruta.relative_to(RAIZ).as_posix()):
                # Se normalizan los saltos para que la prueba no dependa de core.autocrlf en Windows.
                texto = ruta.read_bytes().decode("utf-8").replace("\r\n", "\n")
                self.assertEqual(texto, json.dumps(json.loads(texto), ensure_ascii=False, indent=4) + "\n")

    def test_escritores_de_datos_usan_4_espacios(self):
        for ruta in sorted((RAIZ / "src" / "datos").glob("*.py")):
            with self.subTest(ruta=ruta.relative_to(RAIZ).as_posix()):
                self.assertNotRegex(ruta.read_text(encoding="utf-8"), INDENTACION_DISTINTA_DE_4)

    def test_los_pendientes_siguen_detectandose(self):
        """Cuando DS repare el holdout, esta prueba avisa para sacarlo de PENDIENTES."""
        for relativa in PENDIENTES:
            with self.subTest(ruta=relativa):
                cadenas = textos(json.loads((RAIZ / relativa).read_text(encoding="utf-8")))
                self.assertTrue(any(tiene_tilde_perdida(c) for c in cadenas))


if __name__ == "__main__":
    unittest.main()
