"""Métricas por población, conservación Unicode y registro de ejecución sin red."""

from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from src.datos.entrega_ia import preparar_paquete_ia
from src.datos.ingesta import limpiar_texto, principal, procesar_datos
from src.datos.relevancia import ConfiguracionRelevancia

FECHA = "2026-09-17T12:00:00Z"


def mensaje(identificador, texto, **campos):
    return {
        "id": identificador, "autor": identificador, "canal": "#pruebas",
        "tipo": "pregunta_tecnica", "texto": texto,
        "fecha": "2026-09-16T12:00:00Z", "idioma": "es", **campos,
    }


def lote(*mensajes):
    return {"origen_comunidad": "Prueba", "periodo_referencia": "Semana_02",
            "interacciones": list(mensajes)}


class PruebasRendimientoDatos(unittest.TestCase):
    def test_unicode_visible_se_conserva_en_ambas_entradas_publicas(self):
        casos = [
            ("<p>¡El niño aprendió Python! 👩‍💻</p>", "¡El niño aprendió Python! 👩‍💻"),
            ("  Ação, coração e São Paulo. 🇧🇷  ", "Ação, coração e São Paulo. 🇧🇷"),
            ("Cafe\u0301, nin\u0303o y a\u0323\u0301", "Café, niño y ạ́"),
            ("<p title='ñ'>caf&eacute;&nbsp; &amp; SQL</p>", "café & SQL"),
            ("<script>ñ🙂</script><style>é</style>Python útil", "Python útil"),
            ("\ufeffPython\x00 útil\u200b y café", "Python útil y café"),
        ]
        for original, esperado in casos:
            with self.subTest(original=original):
                entrada = lote(mensaje("uno", original))
                copia = deepcopy(entrada)
                self.assertEqual(limpiar_texto(original), esperado)
                _, informe = procesar_datos(entrada, fecha_referencia=FECHA)
                paquete = preparar_paquete_ia(entrada, fecha_referencia=FECHA)
                for revision in (informe, paquete["informe"]):
                    rendimiento = revision["rendimiento"]
                    self.assertEqual(rendimiento["lotes_con_alerta_caracteres"], [])
                    self.assertEqual(rendimiento["caracteres_entrada_total"], len(original))
                    self.assertEqual(rendimiento["caracteres_limpios_total"], len(esperado))
                self.assertEqual(paquete["estados"][0]["texto"], esperado)
                self.assertEqual(entrada, copia)

    def test_alerta_detecta_sustitucion_o_perdida_aunque_el_conteo_no_baje(self):
        original = "El niño aprendió Python con la comunidad 👩‍💻"
        limpiar_real = limpiar_texto
        cambios = [
            lambda t: t.replace("ñ", "é"),
            lambda t: t.replace("\u200d", ""),
            lambda t: t.encode("ascii", errors="ignore").decode("ascii"),
        ]
        for cambio in cambios:
            with self.subTest(cambio=cambio):
                with patch("src.datos.ingesta.limpiar_texto",
                           side_effect=lambda t: cambio(limpiar_real(t))):
                    entrada = lote(mensaje("uno", original))
                    _, informe = procesar_datos(entrada, fecha_referencia=FECHA)
                    paquete = preparar_paquete_ia(entrada, fecha_referencia=FECHA)
                for revision in (informe, paquete["informe"]):
                    rendimiento = revision["rendimiento"]
                    self.assertEqual(rendimiento["lotes_con_alerta_caracteres"], [0])
                    self.assertEqual(rendimiento["lotes"][0]["interacciones_con_alerta_caracteres"], [0])

    def test_caracter_de_reemplazo_se_registra_como_alerta(self):
        paquete = preparar_paquete_ia(lote(mensaje("uno", "El ni\ufffdo usa Python")),
                                     fecha_referencia=FECHA)
        self.assertEqual(paquete["informe"]["rendimiento"]["lotes_con_alerta_caracteres"], [0])

    def test_poblaciones_separan_ruido_criticas_y_limite_de_contenido(self):
        texto = "¿Cómo configuro Python con LangGraph y SQL?"
        entrada = {"lotes": [
            lote(mensaje("uno", "<p>" + texto + "</p>"),
                 mensaje("dos", texto), mensaje("queja", "Muy mal", tipo="feedback"),
                 mensaje("ruido", "https://example.com/")),
            {**lote(mensaje("otro", "Gracias", tipo="comentario")),
             "origen_comunidad": "Otra"},
        ]}
        configuracion = ConfiguracionRelevancia(maximo_por_lote=1)
        paquete = preparar_paquete_ia(entrada, fecha_referencia=FECHA, configuracion=configuracion)
        r = paquete["informe"]["rendimiento"]
        self.assertEqual(r["interacciones_analisis_total"], 4)
        self.assertEqual(r["caracteres_analisis_total"], 2 * len(texto) + 7 + 7)
        self.assertEqual(r["caracteres_contenido_total"], len(texto))
        self.assertGreater(r["tokens_estimados_analisis_total"], r["tokens_estimados_contenido_total"])
        self.assertEqual(r["tokens_estimados_total"], r["tokens_estimados_contenido_total"])
        self.assertEqual(paquete["plan"]["ids_contenido"], ["uno"])
        for campo in ("caracteres_entrada", "caracteres_limpios", "caracteres_analisis", "caracteres_contenido"):
            self.assertEqual(r[campo + "_total"], sum(l[campo] for l in r["lotes"]))
        self.assertEqual(paquete, preparar_paquete_ia(entrada, fecha_referencia=FECHA, configuracion=configuracion))

    def test_analisis_no_calculado_es_null_y_paquete_vacio_es_cero(self):
        for entrada in ({"lotes": []}, lote()):
            with self.subTest(entrada=entrada):
                _, informe = procesar_datos(entrada, fecha_referencia=FECHA)
                self.assertIsNone(informe["rendimiento"]["tokens_estimados_analisis_total"])
                paquete = preparar_paquete_ia(entrada, fecha_referencia=FECHA)
                self.assertEqual(paquete["informe"]["rendimiento"]["tokens_estimados_analisis_total"], 0)
                self.assertEqual(paquete["estados"], [])

    def test_texto_no_codificable_se_rechaza_con_contexto(self):
        for campo in ("texto", "autor", "idioma"):
            interaccion = mensaje("uno", "Texto válido")
            interaccion[campo] = "\ud800"
            with self.subTest(campo=campo), self.assertRaisesRegex(ValueError, campo + ":.*UTF-8"):
                procesar_datos(lote(interaccion), fecha_referencia=FECHA)

    def test_cli_guarda_tiempo_separado_sin_cambiar_informe_y_preserva_utf8(self):
        with tempfile.TemporaryDirectory() as temporal:
            carpeta = Path(temporal)
            entrada, salida, informe, registro = [carpeta / n for n in (
                "entrada.json", "salida.json", "informe.json", "rendimiento.json")]
            texto = "¡El niño aprendió Python! Ação 👩‍💻"
            entrada.write_text(json.dumps(lote(mensaje("uno", texto)), ensure_ascii=False), encoding="utf-8")
            argumentos = ["--entrada", str(entrada), "--salida", str(salida),
                          "--informe", str(informe), "--fecha-referencia", FECHA,
                          "--entrega-ia", str(carpeta / "ia")]
            with redirect_stdout(io.StringIO()):
                principal(argumentos)
            self.assertFalse(registro.exists())
            informe_previo = informe.read_bytes()
            for tiempos in ([10.0, 10.125], [20.0, 20.5]):
                with patch("src.datos.ingesta.time.perf_counter", side_effect=tiempos), redirect_stdout(io.StringIO()):
                    principal(argumentos + ["--registro-rendimiento", str(registro)])
                ejecucion = json.loads(registro.read_text(encoding="utf-8"))
                self.assertEqual(ejecucion["tiempo_procesamiento_seg"], tiempos[1] - tiempos[0])
                self.assertEqual(informe.read_bytes(), informe_previo)
            estados = json.loads((carpeta / "ia/estados_agente.json").read_text(encoding="utf-8"))
            self.assertEqual(estados[0]["texto"], texto)
            self.assertIn(texto.encode("utf-8"), (carpeta / "ia/estados_agente.json").read_bytes())
            self.assertNotIn("tiempo_procesamiento_seg", json.loads(informe_previo)["rendimiento"])

    def test_cli_rechaza_colision_de_registro_antes_de_escribir(self):
        with tempfile.TemporaryDirectory() as temporal:
            carpeta = Path(temporal)
            entrada = carpeta / "entrada.json"
            entrada.write_text(json.dumps(lote(mensaje("uno", "Texto para probar Python y SQL"))), encoding="utf-8")
            original = entrada.read_bytes()
            salida, informe = carpeta / "salida.json", carpeta / "informe.json"
            for registro in (entrada, salida, informe, carpeta / "ia/plan_procesamiento.json"):
                with self.subTest(registro=registro), self.assertRaises(SystemExit) as error:
                    principal(["--entrada", str(entrada), "--salida", str(salida),
                               "--informe", str(informe), "--entrega-ia", str(carpeta / "ia"),
                               "--registro-rendimiento", str(registro)])
                self.assertEqual(error.exception.code, 2)
                self.assertEqual(entrada.read_bytes(), original)
                self.assertFalse(salida.exists())


if __name__ == "__main__":
    unittest.main()
