"""Pruebas sin red de selección, contrato de entrada e interfaz de consola."""

from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from src.data.ingest import limpiar_texto, procesar_datos
from src.data.relevancia import ConfigRelevancia


FECHA = "2026-09-17T12:00:00Z"


def mensaje(identificador="prueba-1", **cambios):
    resultado = {
        "id": identificador, "autor": "Ana", "canal": "#dudas",
        "tipo": "pregunta_tecnica", "texto": "¿Cómo resuelvo este error en Python y LangGraph?",
        "fecha": "2026-09-16T12:00:00Z", "idioma": "es",
    }
    resultado.update(cambios)
    return resultado


def lote(*mensajes):
    return {"origen_comunidad": "Discord", "periodo_referencia": "Semana_00", "interacciones": list(mensajes)}


def procesar(datos, **opciones):
    return procesar_datos(datos, fecha_referencia=FECHA, config=ConfigRelevancia(**opciones))


class SeleccionTests(unittest.TestCase):
    def test_limpieza_preserva_espanol_emoji_y_expresiones_tecnicas(self):
        texto = "<p>¡Qué  útil! 👩‍💻 &amp; Python</p>\x00 a < b; List<T>\ufffd"
        self.assertEqual(limpiar_texto(texto), "¡Qué útil! 👩‍💻 & Python a < b; List<T>")
        self.assertEqual(limpiar_texto("&lt;p&gt;Hola&nbsp; mundo&lt;/p&gt;"), "Hola mundo")

    def test_limpieza_quita_script_sin_convertirlo_en_evidencia(self):
        self.assertEqual(limpiar_texto("Hola<script>proyecto trabajo</script> mundo"), "Hola mundo")

    def test_no_muta_entrada_y_conserva_campos_adicionales(self):
        entrada = {"metadata": {"fuente": "prueba"}, "lotes": [lote(mensaje(texto="<p>¿Cómo usar Python con LangGraph?</p>", enlace="referencia"))]}
        original = deepcopy(entrada)
        salida, _ = procesar(entrada)
        self.assertEqual(entrada, original)
        self.assertEqual(salida["metadata"], original["metadata"])
        self.assertEqual(salida["lotes"][0]["interacciones"][0]["enlace"], "referencia")

    def test_soporta_contrato_oficial_sin_extensiones(self):
        entrada = lote({"autor": "Ana", "canal": "#faq", "tipo": "pregunta_tecnica", "texto": "¿Cómo configuro los reintentos del LLM en LangGraph?"})
        salida, informe = procesar(entrada)
        self.assertEqual(salida, entrada)
        self.assertIn("sin_fecha", informe["lotes"][0]["evaluaciones"][0]["advertencias"])

    def test_ruido_excluido_y_pregunta_con_enlace_conservada(self):
        entrada = lote(
            mensaje("breve", texto="ok"),
            mensaje("enlace", texto="https://example.com/un-enlace-muy-largo?python=1"),
            mensaje("spam", texto="compra compra compra compra compra compra"),
            mensaje("borrado", texto="[deleted]"),
            mensaje("util", texto="¿Cómo configuro Python según la guía https://example.com/guia?"),
        )
        salida, informe = procesar(entrada)
        self.assertEqual([m["id"] for m in salida["interacciones"]], ["util"])
        motivos = {e["id"]: e["motivos"] for e in informe["lotes"][0]["evaluaciones"]}
        for identificador, motivo in (("breve", "texto_corto"), ("enlace", "solo_enlaces"), ("spam", "texto_repetitivo"), ("borrado", "contenido_eliminado")):
            self.assertIn(motivo, motivos[identificador])
        self.assertEqual(informe["resumen"], {"total": 5, "seleccionadas": 1, "descartadas": 4})

    def test_deduplica_mismo_autor_canal_pero_preserva_recurrencia(self):
        primero = mensaje()
        copia = mensaje("copia", texto=primero["texto"].upper().replace(" ", "  "))
        otra_persona = mensaje("otro", autor="Pedro")
        salida, informe = procesar(lote(primero, copia, otra_persona))
        self.assertEqual([m["id"] for m in salida["interacciones"]], ["prueba-1", "otro"])
        self.assertIn("duplicado", informe["lotes"][0]["evaluaciones"][1]["motivos"])

    def test_id_repetido_se_descarta_solo_dentro_del_lote(self):
        entrada = {"lotes": [lote(mensaje(), mensaje(autor="Otro")), lote(mensaje())]}
        salida, informe = procesar(entrada)
        self.assertEqual([len(l["interacciones"]) for l in salida["lotes"]], [1, 1])
        self.assertEqual(informe["resumen"]["descartadas"], 1)

    def test_queja_util_no_se_descarta_por_ser_negativa(self):
        salida, _ = procesar(lote(mensaje(tipo="feedback", texto="Estoy frustrada porque el curso de Python tiene un error y el mentor no responde.")))
        self.assertEqual(len(salida["interacciones"]), 1)

    def test_top_n_por_lote_orden_estable_y_razon_de_corte(self):
        entrada = {"lotes": [lote(mensaje("uno"), mensaje("dos", autor="Otra")), lote(mensaje("tres"))]}
        salida, informe = procesar(entrada, top_n=1)
        self.assertEqual([l["interacciones"][0]["id"] for l in salida["lotes"]], ["uno", "tres"])
        self.assertIn("fuera_top_n", informe["lotes"][0]["evaluaciones"][1]["motivos"])

    def test_orden_por_puntaje_no_por_posicion(self):
        salida, _ = procesar(lote(mensaje("bajo", tipo="comentario"), mensaje("alto", autor="Otra")))
        self.assertEqual([m["id"] for m in salida["interacciones"]], ["alto", "bajo"])

    def test_configuracion_cambia_seleccion(self):
        entrada = lote(mensaje(tipo="comentario", texto="Este mensaje aporta contexto sobre el encuentro comunitario."))
        normal, _ = procesar(entrada)
        flexible, _ = procesar(entrada, min_puntaje=0)
        self.assertFalse(normal["interacciones"])
        self.assertEqual(len(flexible["interacciones"]), 1)

    def test_palabras_clave_son_unicas_y_no_subcadenas(self):
        _, informe = procesar(lote(mensaje(texto="Aprendí python python con pitonpython y desaprendizaje.")))
        evaluacion = informe["lotes"][0]["evaluaciones"][0]
        self.assertEqual(evaluacion["palabras_clave"], ["aprendi", "python"])
        self.assertEqual(evaluacion["desglose"]["palabras_clave"], 10)

    def test_fechas_invalidas_futuras_y_antiguas_no_reciben_bonus(self):
        for fecha, aviso in (("ayer", "fecha_invalida"), ("2026-09-18T12:00:00Z", "fecha_futura"), ("2026-09-16T12:00:00", "fecha_invalida"), ("2020-01-01T00:00:00Z", None)):
            with self.subTest(fecha=fecha):
                _, informe = procesar(lote(mensaje(fecha=fecha)))
                e = informe["lotes"][0]["evaluaciones"][0]
                self.assertEqual(e["desglose"]["frescura"], 0)
                if aviso:
                    self.assertIn(aviso, e["advertencias"])

    def test_limite_de_frescura_y_zonas_horarias(self):
        for fecha, puntos in (("2026-09-10T07:00:00-05:00", 10), ("2026-09-10T11:59:59Z", 0)):
            _, informe = procesar(lote(mensaje(fecha=fecha)))
            self.assertEqual(informe["lotes"][0]["evaluaciones"][0]["desglose"]["frescura"], puntos)

    def test_reproducible_con_referencia_fija(self):
        entrada = lote(mensaje())
        self.assertEqual(procesar(entrada), procesar(entrada))
        with self.assertRaises(ValueError):
            procesar_datos(entrada, fecha_referencia=datetime(2026, 9, 17))

    def test_lotes_vacios_son_validos(self):
        for entrada in (lote(), {"lotes": []}):
            salida, informe = procesar(entrada)
            self.assertEqual(salida, entrada)
            self.assertEqual(informe["resumen"]["total"], 0)

    def test_rechaza_esquemas_invalidos_con_ubicacion(self):
        for campo, valor in (("autor", None), ("texto", 25), ("tipo", "desconocido"), ("fecha", []), ("id", "")):
            with self.subTest(campo=campo), self.assertRaisesRegex(ValueError, r"lotes\[0\].interacciones\[0\]"):
                procesar(lote(mensaje(**{campo: valor})))
        for entrada in ([], {"lotes": {}}, {"lotes": [None]}, lote(None), {"lotes": [], "interacciones": []}):
            with self.subTest(entrada=entrada), self.assertRaises(ValueError):
                procesar(entrada)

    def test_rechaza_configuracion_invalida(self):
        for opciones in ({"top_n": 0}, {"top_n": True}, {"min_puntaje": -1}, {"min_caracteres": 0}, {"puntos_longitud": 200}, {"puntos_tipo": {}}, {"palabras_clave": "python"}, {"dias_frescura": 1.5}):
            with self.subTest(opciones=opciones), self.assertRaises(ValueError):
                ConfigRelevancia(**opciones)


class IntegracionTests(unittest.TestCase):
    def test_dataset_mvp_contiene_y_selecciona_casos_obligatorios(self):
        entrada = json.loads((RAIZ / "src/data/mensajes_comunidad_simulados.json").read_text(encoding="utf-8"))
        mensajes = [m for l in entrada["lotes"] for m in l["interacciones"]]
        self.assertGreaterEqual(len(mensajes), 10)
        self.assertEqual(len({m["id"] for m in mensajes}), len(mensajes))
        salida, _ = procesar(entrada)
        autores = {m["autor"] for l in salida["lotes"] for m in l["interacciones"]}
        self.assertTrue({"Mariana Souza", "Lucas Albuquerque"} <= autores)
        for nombre in ("Mariana Souza", "Lucas Albuquerque"):
            self.assertEqual(sum(m["autor"] == nombre for m in mensajes), 1)

    def test_snapshot_reddit_separa_enlace_sin_contexto(self):
        entrada = json.loads((RAIZ / "tests/fixtures/prueba_reddit_controlada.json").read_text(encoding="utf-8"))
        _, informe = procesar(entrada)
        enlace = next(e for e in informe["lotes"][0]["evaluaciones"] if e["id"] == "reddit-t1_pa338ud")
        self.assertFalse(enlace["seleccionado"])
        self.assertIn("solo_enlaces", enlace["motivos"])

    def ejecutar_cli(self, carpeta, *argumentos):
        return subprocess.run(
            [sys.executable, "-X", "utf8", str(RAIZ / "src/data/ingest.py"), *map(str, argumentos)],
            cwd=carpeta, capture_output=True, text=True, encoding="utf-8",
        )

    def test_cli_desde_otro_directorio_config_y_json_reproducibles(self):
        with tempfile.TemporaryDirectory() as temporal:
            carpeta = Path(temporal)
            entrada = carpeta / "entrada.json"
            salida = carpeta / "salida.json"
            informe = carpeta / "informe.json"
            config = carpeta / "config.json"
            entrada.write_text(json.dumps(lote(mensaje("uno"), mensaje("dos", autor="Otro"))), encoding="utf-8")
            config.write_text('{"top_n": 1}', encoding="utf-8")
            args = ("--entrada", entrada, "--salida", salida, "--informe", informe, "--config", config, "--fecha-referencia", FECHA)
            corrida = self.ejecutar_cli(carpeta, *args)
            self.assertEqual(corrida.returncode, 0, corrida.stderr)
            self.assertEqual(len(json.loads(salida.read_text(encoding="utf-8"))["interacciones"]), 1)
            primera = (salida.read_bytes(), informe.read_bytes())
            self.assertEqual(self.ejecutar_cli(carpeta, *args).returncode, 0)
            self.assertEqual(primera, (salida.read_bytes(), informe.read_bytes()))

    def test_cli_rechaza_archivo_invalido_sin_crear_salidas(self):
        with tempfile.TemporaryDirectory() as temporal:
            carpeta = Path(temporal)
            entrada = carpeta / "entrada.json"
            salida = carpeta / "salida.json"
            informe = carpeta / "informe.json"
            for contenido in ('{"lotes":', '{"lotes": {}}'):
                entrada.write_text(contenido, encoding="utf-8")
                corrida = self.ejecutar_cli(carpeta, "--entrada", entrada, "--salida", salida, "--informe", informe)
                self.assertEqual(corrida.returncode, 2)
                self.assertFalse(salida.exists())
                self.assertFalse(informe.exists())

    def test_cli_impide_sobrescribir_la_entrada(self):
        with tempfile.TemporaryDirectory() as temporal:
            entrada = Path(temporal) / "entrada.json"
            entrada.write_text(json.dumps(lote(mensaje())), encoding="utf-8")
            original = entrada.read_bytes()
            corrida = self.ejecutar_cli(temporal, "--entrada", entrada, "--salida", entrada)
            self.assertEqual(corrida.returncode, 2)
            self.assertEqual(entrada.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
