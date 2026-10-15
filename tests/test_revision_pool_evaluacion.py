"""Plantilla y resumen de la revisión humana del pool v2. Sin red ni IA."""

import csv
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from scripts.revision_pool_evaluacion import COLUMNAS, POOL, plantilla, resumen


@unittest.skipUnless((POOL / "manifiesto.json").exists(), "pool_v2 no generado")
class PruebasRevisionPool(unittest.TestCase):
    def test_plantilla_40_por_fuente_estratificada_y_reproducible(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta, "revision.csv")
            self.assertEqual(plantilla(ruta), 80)
            primera = ruta.read_bytes()
            self.assertTrue(primera.startswith(b"\xef\xbb\xbf"))
            plantilla(ruta)
            self.assertEqual(ruta.read_bytes(), primera)
            with open(ruta, encoding="utf-8-sig", newline="") as archivo:
                filas = list(csv.DictReader(archivo, delimiter=";"))
        self.assertEqual(list(filas[0]), COLUMNAS)
        self.assertEqual(Counter(f["fuente"] for f in filas), {"uca_ia_tweets": 40, "stackoverflow_es": 40})
        sentimientos = Counter(f["sentimiento_propuesto"] for f in filas if f["fuente"] == "uca_ia_tweets")
        self.assertEqual(sorted(sentimientos.values()), [13, 13, 14])

    def test_resumen_cuenta_correcciones_y_marca_reglas_sobre_el_umbral(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta, "revision.csv")
            plantilla(ruta)
            with open(ruta, encoding="utf-8-sig", newline="") as archivo:
                filas = list(csv.DictReader(archivo, delimiter=";"))
            uca = [f for f in filas if f["fuente"] == "uca_ia_tweets"][:10]
            for i, fila in enumerate(uca):
                fila["revisor"] = "Gustavo"
                if i < 2:
                    fila["tema_revisado"] = "otros"
                if i == 0:
                    fila["sentimiento_revisado"] = fila["sentimiento_propuesto"]
            with open(ruta, "w", encoding="utf-8-sig", newline="") as archivo:
                escritor = csv.DictWriter(archivo, COLUMNAS, delimiter=";")
                escritor.writeheader()
                escritor.writerows(filas)
            informe = resumen(ruta)
        self.assertEqual(list(informe), ["uca_ia_tweets"])
        self.assertEqual(informe["uca_ia_tweets"]["tema"],
                         {"revisados": 10, "corregidos": 2, "tasa_error": 0.2, "corregir_regla": True})
        self.assertFalse(informe["uca_ia_tweets"]["sentimiento"]["corregir_regla"])


if __name__ == "__main__":
    unittest.main()
