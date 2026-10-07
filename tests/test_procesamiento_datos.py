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

from src.datos.ingesta import (
    construir_ciclos,
    construir_estado_agente,
    construir_estados_agente,
    contar_caracteres_no_ascii,
    estimar_tokens,
    guardar_ciclos,
    limpiar_texto,
    procesar_datos,
)
from src.datos.relevancia import (
    ConfiguracionRelevancia,
    es_pregunta_completa,
    leer_fecha,
    puntuar_interaccion,
)


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
    return procesar_datos(datos, fecha_referencia=FECHA, configuracion=ConfiguracionRelevancia(**opciones))


class PruebasSeleccion(unittest.TestCase):
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
        entrada = lote({"autor": "Ana", "canal": "#ayuda", "tipo": "pregunta_tecnica", "texto": "¿Cómo configuro los reintentos del modelo de lenguaje en LangGraph?"})
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

    def test_maximo_por_lote_por_lote_orden_estable_y_razon_de_corte(self):
        entrada = {"lotes": [lote(mensaje("uno"), mensaje("dos", autor="Otra")), lote(mensaje("tres"))]}
        salida, informe = procesar(entrada, maximo_por_lote=1)
        self.assertEqual([l["interacciones"][0]["id"] for l in salida["lotes"]], ["uno", "tres"])
        self.assertIn("fuera_maximo_por_lote", informe["lotes"][0]["evaluaciones"][1]["motivos"])

    def test_orden_por_puntaje_no_por_posicion(self):
        salida, _ = procesar(lote(mensaje("bajo", tipo="comentario"), mensaje("alto", autor="Otra")))
        self.assertEqual([m["id"] for m in salida["interacciones"]], ["alto", "bajo"])

    def test_configuracion_cambia_seleccion(self):
        entrada = lote(mensaje(tipo="comentario", texto="Este mensaje aporta contexto sobre el encuentro comunitario."))
        normal, _ = procesar(entrada)
        flexible, _ = procesar(entrada, puntaje_minimo=0)
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
                procesar(lote(mensaje(**{campo: valor})))  # pyright: ignore[reportArgumentType]
        for entrada in ([], {"lotes": {}}, {"lotes": [None]}, lote(None), {"lotes": [], "interacciones": []}):
            with self.subTest(entrada=entrada), self.assertRaises(ValueError):
                procesar(entrada)

    def test_rechaza_configuracion_invalida(self):
        for opciones in ({"maximo_por_lote": 0}, {"maximo_por_lote": True}, {"puntaje_minimo": -1}, {"caracteres_minimos": 0}, {"puntos_por_longitud": 200}, {"puntos_por_tipo": {}}, {"palabras_clave": "python"}, {"dias_de_frescura": 1.5}):
            with self.subTest(opciones=opciones), self.assertRaises(ValueError):
                ConfiguracionRelevancia(**opciones)  # pyright: ignore[reportArgumentType]


class PruebasMapeoEstadoAgente(unittest.TestCase):
    def test_construir_estado_agente_mapea_claves_exactas_de_estado_agente(self):
        interaccion = mensaje(autor="Ana", canal="#dudas", tipo="pregunta_tecnica", texto="¿Cómo uso LangGraph?")
        estado = construir_estado_agente(interaccion, puntaje=77, origen="Discord_Grupo_ONE_G10")
        self.assertEqual(estado, {
            "autor": "Ana", "canal": "#dudas", "origen": "Discord_Grupo_ONE_G10",
            "texto": "¿Cómo uso LangGraph?", "tipo_original": "pregunta_tecnica",
            "score_relevancia": 77, "id": interaccion["id"], "idioma": "es", "elegible_faq": False,
        })

    def test_construir_estado_agente_no_toca_tipo_ni_fabrica_id_o_idioma(self):
        interaccion = {"autor": "Ana", "canal": "#dudas", "tipo": "comentario", "texto": "ok"}
        estado = construir_estado_agente(interaccion, puntaje=10, origen="LinkedIn_ONE_G10")
        self.assertNotIn("id", estado)
        self.assertNotIn("idioma", estado)
        self.assertEqual(interaccion["tipo"], "comentario")
        self.assertEqual(estado.get("tipo_original"), "comentario")

    def test_construir_estados_agente_aplana_lotes_seleccionados_en_orden_de_puntaje(self):
        entrada = lote(
            mensaje("bajo", texto="ok"),
            mensaje("alto", texto="¿Cómo despliego un proyecto con Python y OCI langchain?"),
            mensaje("medio", texto="Aprendi mucho del curso, gracias mentores"),
        )
        salida, informe = procesar(entrada, puntaje_minimo=0)
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


class PruebasCiclos(unittest.TestCase):
    def test_construir_ciclos_parte_en_grupos_consecutivos_por_lote(self):
        entrada = lote(*(mensaje(str(i), texto=f"Aprendi mucho del curso {i}, gracias mentores") for i in range(21)))
        salida, _ = procesar(entrada, puntaje_minimo=0)
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

    def test_guardar_ciclos_rechaza_directorio_fuera_de_salida(self):
        with tempfile.TemporaryDirectory() as temporal:
            fuera = Path(temporal) / "fuera_de_output"
            with self.assertRaises(ValueError):
                guardar_ciclos(fuera, [])

    def test_guardar_ciclos_solo_retira_archivos_del_manifest_anterior(self):
        with tempfile.TemporaryDirectory() as temporal:
            directorio = Path(temporal) / "salida" / "datos" / "entregas"
            directorio.mkdir(parents=True)
            (directorio / "huerfano.json").write_text("{}", encoding="utf-8")
            anterior = "Discord_Semana_00_lote0_ciclo99.json"
            (directorio / anterior).write_text("{}", encoding="utf-8")
            (directorio / "manifiesto.json").write_text(json.dumps({"ciclos": [{"archivo": anterior}]}), encoding="utf-8")
            entrada = lote(*(mensaje(str(i), texto=f"Aprendi mucho del curso {i}, gracias mentores") for i in range(4)))
            salida, _ = procesar(entrada, puntaje_minimo=0)
            ciclos = construir_ciclos(salida, tamano_ciclo=10)
            with mock.patch("src.datos.ingesta.RAIZ", Path(temporal)):
                ruta_manifest = guardar_ciclos(directorio, ciclos)
            self.assertTrue((directorio / "huerfano.json").exists())
            self.assertFalse((directorio / anterior).exists())
            manifiesto = json.loads(ruta_manifest.read_text(encoding="utf-8"))
            self.assertEqual(len(manifiesto["ciclos"]), 1)
            for entrada_manifiesto in manifiesto["ciclos"]:
                self.assertTrue((directorio / entrada_manifiesto["archivo"]).exists())


class PruebasIntegracion(unittest.TestCase):
    def test_conjunto_datos_pmv_contiene_y_selecciona_casos_obligatorios(self):
        entrada = json.loads((RAIZ / "src/datos/mensajes_comunidad_simulados.json").read_text(encoding="utf-8"))
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
            [sys.executable, "-X", "utf8", str(RAIZ / "src/datos/ingesta.py"), *map(str, argumentos)],
            cwd=carpeta, capture_output=True, text=True, encoding="utf-8",
        )

    def test_cli_desde_otro_directorio_configuracion_y_json_reproducibles(self):
        with tempfile.TemporaryDirectory() as temporal:
            carpeta = Path(temporal)
            entrada = carpeta / "entrada.json"
            salida = carpeta / "salida.json"
            informe = carpeta / "informe.json"
            configuracion = carpeta / "configuracion.json"
            entrada.write_text(json.dumps(lote(mensaje("uno"), mensaje("dos", autor="Otro"))), encoding="utf-8")
            configuracion.write_text('{"maximo_por_lote": 1}', encoding="utf-8")
            argumentos_cli = ("--entrada", entrada, "--salida", salida, "--informe", informe, "--config", configuracion, "--fecha-referencia", FECHA)
            corrida = self.ejecutar_cli(carpeta, *argumentos_cli)
            self.assertEqual(corrida.returncode, 0, corrida.stderr)
            self.assertEqual(len(json.loads(salida.read_text(encoding="utf-8"))["interacciones"]), 1)
            primera = (salida.read_bytes(), informe.read_bytes())
            self.assertEqual(self.ejecutar_cli(carpeta, *argumentos_cli).returncode, 0)
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

    def test_cli_con_tamano_ciclo_genera_archivos_y_manifiesto(self):
        directorio_ciclos = RAIZ / "salida" / "datos" / "entregas_prueba_tmp"
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
            manifiesto = json.loads((directorio_ciclos / "manifiesto.json").read_text(encoding="utf-8"))
            self.assertEqual(sum(c["cantidad"] for c in manifiesto["ciclos"]), 3)
            for c in manifiesto["ciclos"]:
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
            self.assertFalse((carpeta / "manifiesto.json").exists())


class PruebasPreguntaPrograma(unittest.TestCase):
    TEXTO_INT_004 = "¿El certificado final tiene costo adicional o está incluido en el programa?"

    def puntuar(self, texto, tipo="pregunta_programa", **cambios):
        interaccion = mensaje("x", tipo=tipo, texto=texto, fecha="2026-09-12T08:15:00Z", **cambios)
        return puntuar_interaccion(interaccion, ConfiguracionRelevancia(), leer_fecha(FECHA))

    def test_pregunta_completa_se_detecta_con_signos_o_palabra_interrogativa(self):
        self.assertTrue(es_pregunta_completa(self.TEXTO_INT_004))
        self.assertTrue(es_pregunta_completa("Interesante propuesta, ¿tienen alguna alianza con empresas para prácticas profesionales?"))
        self.assertTrue(es_pregunta_completa("Hasta cuándo puedo inscribirme al hackathon?"))

    def test_afirmacion_fragmento_o_pregunta_breve_no_son_pregunta_completa(self):
        self.assertFalse(es_pregunta_completa("El certificado final tiene costo adicional?"))
        self.assertFalse(es_pregunta_completa("¿El certificado final tiene costo adicional o"))
        self.assertFalse(es_pregunta_completa("¿Cuándo empieza?"))

    def test_int_004_etiquetada_pregunta_programa_es_elegible_faq_con_bonus(self):
        resultado = self.puntuar(self.TEXTO_INT_004)
        self.assertEqual(resultado["puntaje"], 62)
        self.assertEqual(resultado["desglose"]["pregunta_completa"], 25)
        self.assertTrue(resultado["elegible_faq"])
        self.assertEqual(resultado["advertencias"], [])

    def test_mismo_texto_etiquetado_comentario_no_recibe_bonus_y_avisa(self):
        resultado = self.puntuar(self.TEXTO_INT_004, tipo="comentario")
        self.assertEqual(resultado["puntaje"], 37)
        self.assertFalse(resultado["elegible_faq"])
        self.assertIn("pregunta_no_etiquetada", resultado["advertencias"])

    def test_pregunta_breve_o_fuera_de_tema_no_recibe_bonus(self):
        self.assertFalse(self.puntuar("¿Cuándo empieza?")["elegible_faq"])
        resultado = self.puntuar("¿Cómo se llama el mejor restaurante de la ciudad hoy?")
        self.assertEqual(resultado["desglose"]["pregunta_completa"], 0)
        self.assertFalse(resultado["elegible_faq"])

    def test_pregunta_tecnica_con_tema_de_programa_no_recibe_bonus_y_avisa(self):
        resultado = self.puntuar("¿Cómo configuro el curso de LangGraph en Python?", tipo="pregunta_tecnica")
        self.assertEqual(resultado["desglose"]["pregunta_completa"], 0)
        self.assertFalse(resultado["elegible_faq"])
        self.assertIn("pregunta_no_etiquetada", resultado["advertencias"])

    def test_prefijo_de_palabras_programa_no_marca_practica_tecnica(self):
        resultado = self.puntuar("¿Cuál es la diferencia práctica entre usar Grid y Flexbox para un layout?", tipo="pregunta_tecnica")
        self.assertNotIn("pregunta_no_etiquetada", resultado["advertencias"])

    def test_duplicado_no_es_elegible_faq_aunque_cumpla_la_regla(self):
        entrada = lote(
            mensaje("a", tipo="pregunta_programa", autor="Sofía", canal="#soporte", texto=self.TEXTO_INT_004, fecha="2026-09-12T08:15:00Z"),
            mensaje("b", tipo="pregunta_programa", autor="Sofía", canal="#soporte", texto=self.TEXTO_INT_004, fecha="2026-09-12T08:15:00Z"),
        )
        _, informe = procesar(entrada)
        por_id = {e["id"]: e for e in informe["lotes"][0]["evaluaciones"]}
        self.assertTrue(por_id["a"]["elegible_faq"])
        self.assertFalse(por_id["b"]["elegible_faq"])

    def test_configuracion_rechaza_bonus_que_supera_el_maximo_de_100(self):
        with self.assertRaises(ValueError):
            ConfiguracionRelevancia(puntos_por_pregunta_completa=60)
        with self.assertRaises(ValueError):
            ConfiguracionRelevancia(palabras_programa=("certificado", "123"))


class PruebasRendimiento(unittest.TestCase):
    def test_estimar_tokens_es_determinista_y_proporcional_al_largo(self):
        self.assertEqual(estimar_tokens(""), 0)
        self.assertEqual(estimar_tokens("hola"), estimar_tokens("hola"))
        self.assertGreater(estimar_tokens("x" * 40), estimar_tokens("x" * 4))

    def test_contar_caracteres_no_ascii_cuenta_tildes_y_emoji_sin_contar_control(self):
        self.assertEqual(contar_caracteres_no_ascii("hola mundo"), 0)
        self.assertEqual(contar_caracteres_no_ascii("café 👩"), 2)
        self.assertEqual(contar_caracteres_no_ascii("sin control\x00aqui"), 0)

    def test_informe_incluye_rendimiento_con_tokens_y_sin_alertas_en_caso_normal(self):
        entrada = lote(
            mensaje("uno", texto="¿Cómo configuro Python con LangGraph? 🙂"),
            mensaje("dos", texto="Gracias por la ayuda, mentores"),
        )
        salida, informe = procesar(entrada)
        rendimiento = informe["rendimiento"]
        self.assertIn("tokens_estimados_total", rendimiento)
        self.assertGreater(rendimiento["tokens_estimados_total"], 0)
        self.assertEqual(rendimiento["lotes_con_alerta_caracteres"], [])
        self.assertEqual(len(rendimiento["lotes"]), 1)
        registro = rendimiento["lotes"][0]
        self.assertEqual(registro["origen_comunidad"], "Discord")
        self.assertTrue(registro["caracteres_especiales_preservados"])
        self.assertEqual(registro["interacciones_seleccionadas"], len(salida["interacciones"]))

    def test_rendimiento_no_usa_reloj_dentro_de_procesar_datos(self):
        """`procesar_datos` debe seguir siendo puro (sin timestamps ni duraciones
        embebidas en el informe), para no romper las pruebas de reproducibilidad
        byte a byte del CLI y de `PruebasSeleccion.test_reproducible_con_referencia_fija`."""
        entrada = lote(mensaje())
        _, informe = procesar(entrada)
        self.assertEqual(procesar(entrada)[1], informe)
        for clave in informe["rendimiento"]:
            self.assertNotIn("tiempo", clave)
        for registro in informe["rendimiento"]["lotes"]:
            for clave in registro:
                self.assertNotIn("tiempo", clave)

    def test_detecta_alerta_si_la_limpieza_pierde_caracteres_especiales(self):
        """Simula una regresiÃ³n futura en `limpiar_texto` (que empiece a tirar
        tildes/emoji) para confirmar que el log de rendimiento la detectarÃ­a."""
        entrada = lote(mensaje("uno", texto="Gracias por la ayuda con el código, mentores"))
        limpiador_con_bug = lambda texto: texto.encode("ascii", errors="ignore").decode("ascii")
        with mock.patch("src.datos.ingesta.limpiar_texto", side_effect=limpiador_con_bug):
            _, informe = procesar(entrada)
        self.assertEqual(informe["rendimiento"]["lotes_con_alerta_caracteres"], [0])
        self.assertFalse(informe["rendimiento"]["lotes"][0]["caracteres_especiales_preservados"])


if __name__ == "__main__":
    unittest.main()
