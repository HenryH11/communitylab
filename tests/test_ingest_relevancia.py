"""Pruebas sin red de selección, contrato de entrada e interfaz de consola."""

from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from src.data.ingest import (
    construir_ciclos, construir_estado_agente, construir_estados_agente,
    guardar_ciclos, limpiar_texto, procesar_datos,
)
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


class MapeoAgentStateTests(unittest.TestCase):
    def test_construir_estado_agente_mapea_claves_exactas_de_agentstate(self):
        interaccion = mensaje(autor="Ana", canal="#dudas", tipo="pregunta_tecnica", texto="¿Cómo uso LangGraph?")
        estado = construir_estado_agente(interaccion, puntaje=77, origen="Discord_Grupo_ONE_G10")
        self.assertEqual(estado, {
            "autor": "Ana", "canal": "#dudas", "origen": "Discord_Grupo_ONE_G10",
            "texto": "¿Cómo uso LangGraph?", "tipo_original": "pregunta_tecnica",
            "score_relevancia": 77, "id": interaccion["id"], "idioma": "es",
        })

    def test_construir_estado_agente_no_toca_tipo_ni_fabrica_id_o_idioma(self):
        interaccion = {"autor": "Ana", "canal": "#dudas", "tipo": "comentario", "texto": "ok"}
        estado = construir_estado_agente(interaccion, puntaje=10, origen="LinkedIn_ONE_G10")
        self.assertNotIn("id", estado)
        self.assertNotIn("idioma", estado)
        self.assertEqual(interaccion["tipo"], "comentario")
        self.assertEqual(estado["tipo_original"], "comentario")

    def test_construir_estados_agente_aplana_lotes_seleccionados_en_orden_de_puntaje(self):
        entrada = lote(
            mensaje("bajo", texto="ok"),
            mensaje("alto", texto="¿Cómo despliego un proyecto con Python y OCI langchain?"),
            mensaje("medio", texto="Aprendi mucho del curso, gracias mentores"),
        )
        salida, informe = procesar(entrada, min_puntaje=0)
        estados = construir_estados_agente(salida, informe)
        self.assertEqual(len(estados), len(salida["interacciones"]))
        puntajes = [e["score_relevancia"] for e in estados]
        self.assertEqual(puntajes, sorted(puntajes, reverse=True))
        for estado, interaccion in zip(estados, salida["interacciones"]):
            self.assertEqual(estado["origen"], "Discord")
            self.assertEqual(estado["texto"], interaccion["texto"])
            self.assertEqual(estado["tipo_original"], interaccion["tipo"])

    def test_construir_estados_agente_soporta_envoltorio_de_lotes(self):
        entrada = {"metadata": {}, "lotes": [lote(mensaje("uno")), lote(mensaje("dos"))]}
        salida, informe = procesar(entrada)
        estados = construir_estados_agente(salida, informe)
        self.assertEqual(len(estados), 2)
        self.assertEqual({e["id"] for e in estados}, {"uno", "dos"})


class ChunkingTests(unittest.TestCase):
    def test_construir_ciclos_parte_en_grupos_consecutivos_por_lote(self):
        entrada = lote(*(mensaje(str(i), texto=f"Aprendi mucho del curso {i}, gracias mentores") for i in range(21)))
        salida, _ = procesar(entrada, min_puntaje=0)
        ciclos = construir_ciclos(salida, tamano_ciclo=10)
        self.assertEqual([c["cantidad"] for c in ciclos], [10, 10, 1])
        self.assertEqual([c["ciclo_indice"] for c in ciclos], [0, 1, 2])
        self.assertTrue(all(c["lote_indice"] == 0 for c in ciclos))
        for c in ciclos:
            self.assertEqual(set(c["contenido"]), {"origen_comunidad", "periodo_referencia", "interacciones"})

    def test_construir_ciclos_lote_vacio_no_genera_archivos(self):
        entrada = lote(mensaje(texto="ok"))
        salida, _ = procesar(entrada)
        self.assertEqual(salida["interacciones"], [])
        self.assertEqual(construir_ciclos(salida, tamano_ciclo=10), [])

    def test_construir_ciclos_rechaza_tamano_invalido(self):
        salida, _ = procesar(lote(mensaje()))
        for tamano in (0, -1, 1, 9, 31, "10", 1.5, True):
            with self.subTest(tamano=tamano), self.assertRaises(ValueError):
                construir_ciclos(salida, tamano)

    def test_construir_ciclos_respeta_envoltorio_de_lotes(self):
        entrada = {"metadata": {}, "lotes": [lote(mensaje("uno"), mensaje("dos", autor="Otro"))]}
        salida, _ = procesar(entrada)
        ciclos = construir_ciclos(salida, tamano_ciclo=10)
        self.assertEqual(len(ciclos), 1)
        self.assertEqual([m["id"] for m in ciclos[0]["contenido"]["interacciones"]], ["uno", "dos"])

    def test_construir_ciclos_proyecta_al_contrato_de_nelson_sin_campos_extra(self):
        entrada = lote(mensaje(enlace="referencia", nota_interna="borrar antes de entregar"))
        salida, _ = procesar(entrada)
        ciclos = construir_ciclos(salida, tamano_ciclo=10)
        interaccion_entregada = ciclos[0]["contenido"]["interacciones"][0]
        self.assertEqual(set(interaccion_entregada), {"id", "autor", "canal", "tipo", "texto", "fecha", "idioma"})

    def test_construir_ciclos_exige_los_siete_campos_del_contrato_de_entrega(self):
        entrada = lote({"autor": "Ana", "canal": "#faq", "tipo": "pregunta_tecnica", "texto": "¿Cómo configuro los reintentos del LLM en LangGraph?"})
        salida, _ = procesar(entrada)
        with self.assertRaises(ValueError):
            construir_ciclos(salida, tamano_ciclo=10)

    def test_nombre_de_archivo_sanea_caracteres_inseguros(self):
        entrada = {"origen_comunidad": "../../etc", "periodo_referencia": "Semana 00!", "interacciones": [mensaje()]}
        salida, _ = procesar(entrada)
        ciclos = construir_ciclos(salida, tamano_ciclo=10)
        self.assertEqual(len(ciclos), 1)
        nombre = ciclos[0]["archivo"]
        self.assertNotIn("/", nombre)
        self.assertNotIn("..", nombre)

    def test_guardar_ciclos_rechaza_directorio_fuera_de_output(self):
        with tempfile.TemporaryDirectory() as temporal:
            fuera = Path(temporal) / "fuera_de_output"
            with self.assertRaises(ValueError):
                guardar_ciclos(fuera, [])

    def test_guardar_ciclos_solo_retira_archivos_del_manifest_anterior(self):
        with tempfile.TemporaryDirectory() as temporal:
            directorio = Path(temporal) / "output" / "datos" / "entregas"
            directorio.mkdir(parents=True)
            (directorio / "huerfano.json").write_text("{}", encoding="utf-8")
            anterior = "Discord_Semana_00_lote0_ciclo99.json"
            (directorio / anterior).write_text("{}", encoding="utf-8")
            (directorio / "manifest.json").write_text(json.dumps({"ciclos": [{"archivo": anterior}]}), encoding="utf-8")
            entrada = lote(*(mensaje(str(i), texto=f"Aprendi mucho del curso {i}, gracias mentores") for i in range(4)))
            salida, _ = procesar(entrada, min_puntaje=0)
            ciclos = construir_ciclos(salida, tamano_ciclo=10)
            with mock.patch("src.data.ingest.RAIZ", Path(temporal)):
                ruta_manifest = guardar_ciclos(directorio, ciclos)
            self.assertTrue((directorio / "huerfano.json").exists())
            self.assertFalse((directorio / anterior).exists())
            manifest = json.loads(ruta_manifest.read_text(encoding="utf-8"))
            self.assertEqual(len(manifest["ciclos"]), 1)
            for entrada_manifest in manifest["ciclos"]:
                self.assertTrue((directorio / entrada_manifest["archivo"]).exists())


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

    def test_cli_tamano_ciclo_es_opt_in_no_cambia_la_salida_por_defecto(self):
        with tempfile.TemporaryDirectory() as temporal:
            carpeta = Path(temporal)
            entrada = carpeta / "entrada.json"
            salida = carpeta / "salida.json"
            informe = carpeta / "informe.json"
            entrada.write_text(json.dumps(lote(mensaje())), encoding="utf-8")
            args = ("--entrada", entrada, "--salida", salida, "--informe", informe, "--fecha-referencia", FECHA)
            sin_flag = self.ejecutar_cli(carpeta, *args)
            self.assertEqual(sin_flag.returncode, 0, sin_flag.stderr)
            self.assertNotIn("Ciclos:", sin_flag.stdout)
            referencia = (salida.read_bytes(), informe.read_bytes())
            self.assertEqual(self.ejecutar_cli(carpeta, *args).returncode, 0)
            self.assertEqual((salida.read_bytes(), informe.read_bytes()), referencia)

    def test_cli_con_tamano_ciclo_genera_archivos_y_manifest(self):
        directorio_ciclos = RAIZ / "output" / "datos" / "entregas_prueba_tmp"
        self.addCleanup(shutil.rmtree, directorio_ciclos, ignore_errors=True)
        with tempfile.TemporaryDirectory() as temporal:
            carpeta = Path(temporal)
            entrada = carpeta / "entrada.json"
            salida = carpeta / "salida.json"
            informe = carpeta / "informe.json"
            mensajes = (mensaje(str(i), texto=f"Aprendi mucho del curso {i}, gracias mentores") for i in range(3))
            entrada.write_text(json.dumps(lote(*mensajes)), encoding="utf-8")
            args = (
                "--entrada", entrada, "--salida", salida, "--informe", informe,
                "--fecha-referencia", FECHA, "--tamano-ciclo", "10", "--ciclos", directorio_ciclos,
            )
            corrida = self.ejecutar_cli(carpeta, *args)
            self.assertEqual(corrida.returncode, 0, corrida.stderr)
            self.assertIn("Ciclos:", corrida.stdout)
            manifest = json.loads((directorio_ciclos / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(sum(c["cantidad"] for c in manifest["ciclos"]), 3)
            for c in manifest["ciclos"]:
                self.assertTrue((directorio_ciclos / c["archivo"]).exists())

    def test_cli_rechaza_ciclos_coincidente_con_entrada(self):
        with tempfile.TemporaryDirectory() as temporal:
            carpeta = Path(temporal)
            entrada = carpeta / "entrada.json"
            salida = carpeta / "salida.json"
            informe = carpeta / "informe.json"
            entrada.write_text(json.dumps(lote(mensaje())), encoding="utf-8")
            args = (
                "--entrada", entrada, "--salida", salida, "--informe", informe,
                "--fecha-referencia", FECHA, "--tamano-ciclo", "5", "--ciclos", carpeta,
            )
            corrida = self.ejecutar_cli(carpeta, *args)
            self.assertEqual(corrida.returncode, 2)
            self.assertFalse((carpeta / "manifest.json").exists())


if __name__ == "__main__":
    unittest.main()
