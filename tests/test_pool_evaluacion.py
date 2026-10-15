"""Pool de evaluación v2 (DA): construcción reproducible, sin red ni IA."""

import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts.construir_pool_evaluacion import (
    candidatos_so, candidatos_uca, construir, es_espanol, limpiar_pregunta, limpiar_tuit,
    muestrear_por_grupo, textos_congelados,
)

RAIZ = Path(__file__).resolve().parents[1]
POOL = RAIZ / "datos_evaluacion" / "pool_v2"
CAMPOS_HOLDOUT = {"id", "texto", "origen", "canal", "idioma", "sentimiento_esperado",
                  "tema_esperado", "tipo_esperado", "subtema_referencia"}

TUITS = [
    ("1", "Me encanta cómo la inteligencia artificial ayuda a los estudiantes de programación", "P"),
    ("2", "Es preocupante que la inteligencia artificial se use para engañar a las personas mayores", "N"),
    ("3", "La inteligencia artificial es un tema que se discute mucho en las redes y en los medios", "NEU"),
    ("4", "We love the new AI tools for the team and the community", "P"),
    ("5", "@alguien hola https://t.co/x", "NEU"),
    ("6", "Me encanta cómo la inteligencia artificial ayuda a los estudiantes de programación", "P"),
]


def escribir_fuentes(carpeta):
    carpeta = Path(carpeta)
    ruta_csv = carpeta / "ia_tweets.csv"
    with open(ruta_csv, "w", encoding="utf-8", newline="") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(["ID", "text", "polarity"])
        escritor.writerows(TUITS)
    so = carpeta / "so"
    so.mkdir()
    preguntas = {"items": [
        {"question_id": 10, "title": "¿Cómo leo un CSV con pandas?", "body": "<p>Tengo un archivo y quiero cargarlo.</p><pre><code>pd.read_csv()</code></pre>",
         "link": "https://es.stackoverflow.com/q/10", "owner": {"display_name": "Ana"}, "content_license": "CC BY-SA 4.0"},
        {"question_id": 11, "title": "Error al agrupar en pandas", "body": "<p>Al usar groupby obtengo un KeyError en la columna.</p>",
         "link": "https://es.stackoverflow.com/q/11", "owner": {"display_name": "Luis"}, "content_license": "CC BY-SA 3.0"},
    ]}
    (so / "pandas.json").write_text(json.dumps(preguntas, ensure_ascii=False), encoding="utf-8")
    (so / "otra-etiqueta.json").write_text(json.dumps(preguntas), encoding="utf-8")
    return ruta_csv, so


class PruebasPoolEvaluacion(unittest.TestCase):
    def test_tuits_filtra_ingles_vacios_y_duplicados_y_anonimiza(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta_csv, _ = escribir_fuentes(carpeta)
            casos = candidatos_uca(ruta_csv)
        self.assertEqual([c["id"] for c in casos], ["uca-1", "uca-2", "uca-3"])
        self.assertEqual([c["sentimiento_esperado"] for c in casos], ["positivo", "negativo", "neutral"])
        self.assertEqual(limpiar_tuit("@pepe mira https://t.co/abc  esto"), "@usuario mira esto")
        self.assertFalse(es_espanol("We love the new AI tools for the team"))

    def test_preguntas_sin_codigo_con_atribucion_y_tema_por_etiqueta(self):
        with tempfile.TemporaryDirectory() as carpeta:
            _, so = escribir_fuentes(carpeta)
            casos = candidatos_so(so)
        self.assertEqual([c["id"] for c in casos], ["so-10", "so-11"])
        self.assertEqual(casos[0]["texto"], "¿Cómo leo un CSV con pandas? Tengo un archivo y quiero cargarlo. [código]")
        self.assertEqual(casos[0]["tema_esperado"], "datos_ia")
        self.assertEqual(casos[1]["atribucion"]["licencia"], "CC BY-SA 3.0")
        self.assertEqual(limpiar_pregunta("Error en git", "<p>No sube.</p>"), "Error en git. No sube.")

    def test_muestreo_estratificado_y_reproducible(self):
        filas = [{"id": f"x-{i:03d}", "g": "a" if i % 3 else "b"} for i in range(90)]
        primera = muestrear_por_grupo(filas, "g", 20, 7)
        self.assertEqual(primera, muestrear_por_grupo(filas, "g", 20, 7))
        self.assertEqual(sum(f["g"] == "a" for f in primera), 10)
        with self.assertRaisesRegex(ValueError, "Faltan casos"):
            muestrear_por_grupo(filas, "g", 80, 7)

    def test_construir_escribe_formato_holdout_y_manifiesto(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta_csv, so = escribir_fuentes(carpeta)
            manifiesto = construir(ruta_csv, so, Path(carpeta, "pool"), por_fuente=2,
                                   excluir_textos=[TUITS[2][1]])
            uca = json.loads(Path(carpeta, "pool", "uca_ia_tweets.json").read_text(encoding="utf-8"))
        self.assertEqual(manifiesto["archivos"]["uca_ia_tweets.json"]["casos"], 2)
        self.assertNotIn("uca-3", [c["id"] for c in uca["casos"]])
        self.assertTrue(CAMPOS_HOLDOUT <= set(uca["casos"][0]))

    @unittest.skipUnless((POOL / "manifiesto.json").exists(), "pool_v2 no generado")
    def test_pool_versionado_coincide_con_manifiesto_y_no_repite_congelados(self):
        import hashlib
        manifiesto = json.loads((POOL / "manifiesto.json").read_text(encoding="utf-8"))
        congelados = {" ".join(t.split()) for t in textos_congelados(RAIZ)}
        ids = set()
        for nombre, datos in manifiesto["archivos"].items():
            ruta = POOL / nombre
            # El SHA se calcula sobre saltos LF: en Windows, git puede dejar CRLF al hacer checkout.
            contenido = ruta.read_bytes().replace(b"\r\n", b"\n")
            self.assertEqual(hashlib.sha256(contenido).hexdigest(), datos["sha256"])
            casos = json.loads(ruta.read_text(encoding="utf-8"))["casos"]
            self.assertEqual(len(casos), manifiesto["por_fuente"])
            for caso in casos:
                self.assertTrue(CAMPOS_HOLDOUT <= set(caso), caso["id"])
                self.assertNotIn(caso["texto"], congelados)
                self.assertNotIn(caso["id"], ids)
                ids.add(caso["id"])


if __name__ == "__main__":
    unittest.main()
