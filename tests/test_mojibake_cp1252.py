"""Reparación de mojibake cuando el UTF-8 se leyó como Windows-1252 (CP1252).

Es el caso típico en Windows: además de las tildes, se dañan las comillas tipográficas,
las rayas, el apóstrofo, el euro y los emojis. Sin red ni dependencias.
"""

import unittest

from src.datos.limpieza import detectar_mojibake, limpiar_texto, reparar_mojibake


def danar_como_cp1252(texto: str) -> str:
    """Lee los bytes UTF-8 como CP1252; los bytes que CP1252 no define quedan como Latin-1."""
    caracteres = []
    for byte in texto.encode("utf-8"):
        try:
            caracteres.append(bytes([byte]).decode("cp1252"))
        except UnicodeDecodeError:
            caracteres.append(chr(byte))
    return "".join(caracteres)


def danar_como_latin1(texto: str) -> str:
    return texto.encode("utf-8").decode("latin-1")


ORIGINALES = [
    "Ingeniería y mañana",
    "“Hola” — ¿qué tal?",
    "Costó 5 €",
    "It’s mi primer año",
    "Logré mi meta 🎉 “gracias”",
]


class PruebasMojibakeCp1252(unittest.TestCase):
    def test_detecta_y_repara_texto_leido_como_cp1252(self):
        for original in ORIGINALES:
            with self.subTest(original=original):
                danado = danar_como_cp1252(original)
                self.assertTrue(detectar_mojibake(danado), danado)
                self.assertEqual(reparar_mojibake(danado), original)

    def test_sigue_reparando_texto_leido_como_latin1(self):
        for original in ORIGINALES:
            with self.subTest(original=original):
                self.assertEqual(reparar_mojibake(danar_como_latin1(original)), original)

    def test_texto_correcto_no_se_marca_ni_se_modifica(self):
        correctos = ORIGINALES + [
            "Señor “Núñez” pagó 5 € — ¡genial! 🎉",
            "CAMPAÑÍA DE INSCRIPCIÓN",
            "El pâté y la crème brûlée",
        ]
        for texto in correctos:
            with self.subTest(texto=texto):
                self.assertFalse(detectar_mojibake(texto))
                self.assertEqual(reparar_mojibake(texto), texto)

    def test_repara_fragmentos_danados_junto_a_emojis_validos(self):
        texto = danar_como_cp1252("“Gracias” al programa") + " 🚀"
        self.assertEqual(reparar_mojibake(texto), "“Gracias” al programa 🚀")

    def test_limpiar_texto_repara_cp1252_automaticamente(self):
        self.assertEqual(limpiar_texto(danar_como_cp1252("<p>Costó 5 € — “vale”</p>")), "Costó 5 € — “vale”")


if __name__ == "__main__":
    unittest.main()
