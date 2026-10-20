"""Conjunto Consultable de DA (Semana 5.1, subfase A). Sin IA ni red."""

import json
import unittest
from pathlib import Path

from src.datos.conjunto_consultable import CAMPOS, construir_conjunto_consultable, principal, recortar

DATASET = Path(__file__).resolve().parents[1] / "src/datos/mensajes_comunidad_simulados.json"


def entrega_v13():
    """Forma del contrato de salida de DS: campos planos y sin fecha."""
    return {"version_contrato": "1.3", "interacciones": [
        {"id": "int-002", "canal": "#dudas-langgraph", "texto": "¿Cómo uso aristas condicionales?",
         "sentimiento": "neutral", "tema_principal": "langgraph", "subtema": "aristas", "tipo_detectado": "pregunta_tecnica"},
        {"id": "int-001", "canal": "#logros-y-empleos", "texto": "Conseguí mi primer trabajo como analista de datos.",
         "sentimiento": "muy_positivo", "tema_principal": "empleabilidad", "tipo_detectado": "testimonio"},
    ]}


def entrega_v14():
    """Contrato v1.4: DS marca el spam con es_spam_detectado y motivo_spam."""
    entrega = entrega_v13()
    entrega["version_contrato"] = "1.4"
    for interaccion in entrega["interacciones"]:
        interaccion.update(es_spam_detectado=False, motivo_spam=None)
    entrega["interacciones"].append(
        {"id": "int-050", "canal": "#general", "texto": "Gana dinero desde casa, escríbeme al privado.",
         "sentimiento": "positivo", "tema_principal": "otros", "tipo_detectado": "comentario",
         "es_spam_detectado": True, "motivo_spam": "Captación no solicitada"})
    return entrega


def entrega_v12():
    """Forma del paquete de auditoría: entrada, datos y analisis anidados."""
    return {"version_auditoria": "1.2", "interacciones": [
        {"id": "int-001", "entrada": {"canal": "#logros-y-empleos", "texto": "Conseguí trabajo.", "fecha": "2026-09-10T14:32:00Z"},
         "datos": {"excluido_por_data": False}, "analisis": {"sentimiento": "positivo", "tema_principal": "empleabilidad", "tipo_detectado": "testimonio"}},
        {"id": "int-099", "entrada": {"canal": "#general", "texto": "compra ahora compra ahora"},
         "datos": {"excluido_por_data": True}, "analisis": None},
    ]}


class PruebasConjuntoConsultable(unittest.TestCase):
    def test_campos_estrictos_y_orden_por_id(self):
        conjunto = construir_conjunto_consultable(entrega_v13())
        self.assertEqual(conjunto["campos"], list(CAMPOS))
        self.assertEqual([r["id"] for r in conjunto["registros"]], ["int-001", "int-002"])
        for registro in conjunto["registros"]:
            self.assertEqual(tuple(registro), CAMPOS)
        self.assertEqual(conjunto["registros"][1]["tema"], "langgraph")
        self.assertEqual(conjunto["registros"][1]["tipo"], "pregunta_tecnica")

    def test_fecha_del_dataset_cuando_la_entrega_no_la_trae(self):
        mensajes = json.loads(DATASET.read_text(encoding="utf-8"))
        sin_dataset = construir_conjunto_consultable(entrega_v13())
        con_dataset = construir_conjunto_consultable(entrega_v13(), mensajes)
        self.assertIsNone(sin_dataset["registros"][0]["fecha"])
        self.assertTrue(con_dataset["registros"][0]["fecha"].startswith("2026-"))

    def test_paquete_de_auditoria_y_exclusiones_de_datos(self):
        conjunto = construir_conjunto_consultable(entrega_v12())
        self.assertEqual(conjunto["total"], 1)
        self.assertEqual(conjunto["registros"][0]["fecha"], "2026-09-10T14:32:00Z")
        self.assertEqual(conjunto["registros"][0]["sentimiento"], "positivo")

    def test_v14_excluye_el_spam_de_ds_y_lo_cuenta(self):
        conjunto = construir_conjunto_consultable(entrega_v14())
        self.assertEqual([r["id"] for r in conjunto["registros"]], ["int-001", "int-002"])
        self.assertEqual(conjunto["total"], 2)
        self.assertEqual(conjunto["total_spam_excluido"], 1)
        for registro in conjunto["registros"]:
            self.assertEqual(tuple(registro), CAMPOS)

    def test_v13_sin_marca_de_spam_no_cambia(self):
        conjunto = construir_conjunto_consultable(entrega_v13())
        self.assertEqual(conjunto["total"], 2)
        self.assertEqual(conjunto["total_spam_excluido"], 0)

    def test_rechaza_ids_duplicados(self):
        entrega = entrega_v13()
        entrega["interacciones"].append(dict(entrega["interacciones"][0]))
        with self.assertRaisesRegex(ValueError, "int-002"):
            construir_conjunto_consultable(entrega)

    def test_contenido_corto_en_una_linea_y_acotado(self):
        largo = "palabra " * 60
        corto = recortar(largo)
        self.assertLessEqual(len(corto), 160)
        self.assertTrue(corto.endswith("…"))
        self.assertEqual(recortar("Hola\n  mundo"), "Hola mundo")
        self.assertEqual(recortar("¿Qué tal? 🎉"), "¿Qué tal? 🎉")

    def test_cli_escribe_json_utf8(self):
        import tempfile
        with tempfile.TemporaryDirectory() as carpeta:
            entrada, salida = Path(carpeta, "entrega.json"), Path(carpeta, "conjunto.json")
            entrada.write_text(json.dumps(entrega_v13(), ensure_ascii=False), encoding="utf-8")
            self.assertEqual(principal(["--entrega", str(entrada), "--mensajes", str(DATASET), "--salida", str(salida)]), 0)
            self.assertNotIn(b"\r\n", salida.read_bytes())
            conjunto = json.loads(salida.read_text(encoding="utf-8"))
            self.assertEqual(conjunto["total"], 2)
            self.assertIn("¿Cómo", conjunto["registros"][1]["contenido_corto"])


if __name__ == "__main__":
    unittest.main()
