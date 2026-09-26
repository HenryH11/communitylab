"""Pruebas offline de entrega de Datos, contrato y planificación."""
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from src.data.entrega_ia import construir_plan_procesamiento, preparar_entrega, preparar_paquete_ia
from src.data.ingest import construir_estados_agente, construir_ciclos, guardar_ciclos, main
from src.data.ingesta_reddit import parsear_entradas_atom, transformar_entrada, comentario_fue_eliminado, construir_lote
from src.data.relevancia import ConfigRelevancia
from test_ingest_relevancia import FECHA, lote, mensaje
from verificar_transformacion_reddit import FIXTURE_COMENTARIOS

class EntregaTests(unittest.TestCase):
    def preparar(self, datos, **opciones):
        return preparar_entrega(datos, fecha_referencia=FECHA, config=ConfigRelevancia(**opciones))

    def test_queja_breve_y_bajo_puntaje_permanecen_en_sentimiento(self):
        completos, contenido, informe = self.preparar(lote(
            mensaje("queja", tipo="feedback", texto="Muy mal"),
            mensaje("elogio", tipo="comentario", texto="Gracias"),
            mensaje("util"),
        ))
        self.assertEqual([m["id"] for m in completos["lotes"][0]["interacciones"]], ["queja", "elogio", "util"])
        self.assertEqual([m["id"] for m in contenido["lotes"][0]["interacciones"]], ["util"])
        self.assertEqual(informe["resumen_sentimiento"], {"total": 3, "incluidas": 3, "excluidas_calidad": 0})

    def test_top_n_no_reduce_poblacion_de_sentimiento(self):
        completos, contenido, _ = self.preparar(lote(mensaje("uno"), mensaje("dos", autor="Otra")), top_n=1)
        self.assertEqual(len(completos["lotes"][0]["interacciones"]), 2)
        self.assertEqual(len(contenido["lotes"][0]["interacciones"]), 1)

    def test_calidad_separa_ruido_y_preserva_recurrencia_entre_autores(self):
        entrada = lote(mensaje("valido"), mensaje("copia"), mensaje("otra", autor="Eva"),
                       mensaje("vacio", texto="<p> </p>"), mensaje("url", texto="https://example.com/"),
                       mensaje("spam", texto="compra compra compra compra compra compra"),
                       mensaje("eliminado", texto="[removed]"))
        completos, _, informe = self.preparar(entrada)
        self.assertEqual([m["id"] for m in completos["lotes"][0]["interacciones"]], ["valido", "otra"])
        self.assertEqual(informe["resumen_sentimiento"]["excluidas_calidad"], 5)
        vacio = informe["lotes"][0]["evaluaciones"][3]
        self.assertIn("texto_vacio", vacio["motivos_exclusion_sentimiento"])

    def test_id_obligatorio_y_unico_entre_lotes(self):
        sin_id = mensaje()
        sin_id.pop("id")
        for entrada in (lote(sin_id), lote(mensaje(), mensaje()), {"lotes": [lote(mensaje()), lote(mensaje())]}, lote(mensaje(" espacios "))):
            with self.subTest(entrada=entrada), self.assertRaises(ValueError):
                self.preparar(entrada)

    def test_metadatos_ausentes_o_invalidos_no_se_inventan(self):
        for campo in ("fecha", "idioma"):
            m = mensaje()
            m.pop(campo)
            with self.subTest(campo=campo), self.assertRaisesRegex(ValueError, campo):
                self.preparar(lote(m))
        for fecha in ("ayer", "2026-09-17T12:00:00", "2026-09-17 12:00:00Z", "2026-02-30T12:00:00Z"):
            with self.subTest(fecha=fecha), self.assertRaisesRegex(ValueError, "fecha"):
                self.preparar(lote(mensaje(fecha=fecha)))

    def test_preserva_original_y_proyecta_solo_campos_del_contrato(self):
        entrada = {"metadata": {"total": 99}, "lotes": [lote(mensaje(texto="<p>¡Qué mal! 😞</p>", privado="no enviar"))]}
        copia = deepcopy(entrada)
        completos, _, _ = self.preparar(entrada)
        self.assertEqual(entrada, copia)
        self.assertNotIn("metadata", completos)
        m = completos["lotes"][0]["interacciones"][0]
        self.assertNotIn("privado", m)
        self.assertEqual(m["texto"], "¡Qué mal! 😞")
        self.assertEqual(set(m), {"id", "autor", "canal", "tipo", "texto", "fecha", "idioma"})


    def test_cruce_por_id_tras_reordenar_lotes_y_mensajes(self):
        completos, contenido, informe = self.preparar({"lotes": [
            lote(mensaje("alto"), mensaje("bajo", tipo="comentario", texto="Gracias")),
            {**lote(mensaje("otro")), "origen_comunidad": "Alura"},
        ]})
        completos["lotes"].reverse()
        completos["lotes"][1]["interacciones"].reverse()
        informe["lotes"].reverse()
        estados = construir_estados_agente(completos, informe, poblacion="sentimiento")
        por_id = {e["id"]: e for e in estados}
        self.assertGreater(por_id["alto"]["score_relevancia"], por_id["bajo"]["score_relevancia"])
        self.assertEqual(por_id["otro"]["origen"], "Alura")
        self.assertEqual(por_id["alto"]["tipo_original"], "pregunta_tecnica")
        self.assertEqual(len(construir_estados_agente(contenido, informe)), 2)

    def test_mapeo_rechaza_informes_incompatibles(self):
        completos, _, original = self.preparar(lote(mensaje()))
        for cambio in ("id", "origen", "periodo", "duplicado", "faltante", "poblacion"):
            informe = deepcopy(original)
            revision = informe["lotes"][0]
            if cambio == "id":
                revision["evaluaciones"][0]["id"] = "otro"
            elif cambio in ("origen", "periodo"):
                revision["origen_comunidad" if cambio == "origen" else "periodo_referencia"] = "Otro"
            elif cambio == "duplicado":
                revision["evaluaciones"].append(deepcopy(revision["evaluaciones"][0]))
            elif cambio == "poblacion":
                revision["evaluaciones"][0].pop("incluido_sentimiento")
            else:
                revision["evaluaciones"] = []
            with self.subTest(cambio=cambio), self.assertRaises(ValueError):
                construir_estados_agente(completos, informe, poblacion="sentimiento")
        completos["lotes"][0]["interacciones"] = []
        with self.assertRaises(ValueError):
            construir_estados_agente(completos, original, poblacion="sentimiento")

    def test_mapeo_rechaza_ids_repetidos_en_salida(self):
        completos, _, informe = self.preparar(lote(mensaje()))
        completos["lotes"][0]["interacciones"] *= 2
        with self.assertRaises(ValueError):
            construir_estados_agente(completos, informe, poblacion="sentimiento")

    def test_dataset_23_sentimiento_14_contenido_dos_ciclos(self):
        datos = json.loads((RAIZ / "src/data/mensajes_comunidad_simulados.json").read_text(encoding="utf-8"))
        paquete = preparar_paquete_ia(datos, fecha_referencia=FECHA)
        self.assertEqual(len(paquete["estados"]), 23)
        self.assertEqual(paquete["informe"]["resumen"]["seleccionadas"], 14)
        plan = paquete["plan"]
        self.assertEqual([c["cantidad"] for c in plan["ciclos"]], [12, 11])
        self.assertEqual(plan["pendientes"], [])
        self.assertTrue({"int-022", "int-023"} <= set(plan["ids_contenido"]))
        administrativos = {"int-004", "int-007", "int-010", "int-013", "int-015"}
        self.assertFalse(administrativos & set(plan["ids_contenido"]))
        self.assertTrue(administrativos <= {e["id"] for e in paquete["estados"]})
        claves = {"id", "autor", "canal", "origen", "idioma", "texto", "tipo_original", "score_relevancia"}
        self.assertTrue(all(set(e) == claves for e in paquete["estados"]))

    def test_reddit_original_se_conecta_al_mismo_adaptador(self):
        entradas = parsear_entradas_atom(FIXTURE_COMENTARIOS)
        mensajes = [transformar_entrada(e, "webdev", idioma="en") for e in entradas if not comentario_fue_eliminado(e)]
        paquete = preparar_paquete_ia(construir_lote("webdev", "Semana_00", mensajes), fecha_referencia=FECHA)
        self.assertEqual(len(paquete["estados"]), 2)
        self.assertEqual(paquete["estados"][0]["id"], "reddit-t1_def456")
        self.assertEqual(paquete["estados"][0]["origen"], "Reddit_r_webdev")
        self.assertEqual(paquete["estados"][0]["idioma"], "en")
        self.assertEqual(len(paquete["plan"]["pendientes"]), 2)

    def test_plan_conserva_ids_sin_perdida_ni_repeticion_en_limites(self):
        for n in (0, 1, 9, 10, 11, 19, 20, 21, 23, 29, 30, 31, 39, 59, 61):
            for tamano in (10, 15, 20, 30):
                ids = [str(i) for i in range(n)]
                plan = construir_plan_procesamiento([{"id": i} for i in ids], tamano)
                with self.subTest(n=n, tamano=tamano):
                    self.assertEqual([i for c in plan["ciclos"] for i in c["ids"]] + plan["pendientes"], ids)
                    self.assertTrue(all(10 <= c["cantidad"] <= tamano for c in plan["ciclos"]))
                    self.assertLess(len(plan["pendientes"]), 10)

    def test_plan_rechaza_ids_y_tamanos_invalidos(self):
        for tamano in (9, 31, True, "20", 0):
            with self.assertRaises(ValueError):
                construir_plan_procesamiento([], tamano)
        for estados in ([{}], [{"id": " x "}], [{"id": "x"}, {"id": "x"}]):
            with self.assertRaises(ValueError):
                construir_plan_procesamiento(estados)

    def test_fragmentos_rechazan_fecha_invalida_y_ids_duplicados(self):
        for fecha in ("ayer", "2026-02-30T12:00:00Z", "2026-09-17T12:00:00", "2026-09-17T12:00:00+00:99"):
            with self.assertRaises(ValueError):
                construir_ciclos(lote(mensaje(fecha=fecha)), 20)
        with self.assertRaises(ValueError):
            construir_ciclos({"lotes": [lote(mensaje()), lote(mensaje())]}, 20)

    def test_guardado_rechaza_raiz_output_y_manifest_con_ruta_ajena(self):
        with tempfile.TemporaryDirectory() as temporal, mock.patch("src.data.ingest.RAIZ", Path(temporal)):
            output = Path(temporal) / "output"
            destino = output / "entregas"
            destino.mkdir(parents=True)
            ajeno = output / "mensajes_filtrados.json"
            ajeno.write_text("preservar", encoding="utf-8")
            with self.assertRaises(ValueError):
                guardar_ciclos(output, [])
            (destino / "manifest.json").write_text(json.dumps({"ciclos": [{"archivo": "../mensajes_filtrados.json"}]}), encoding="utf-8")
            with self.assertRaises(ValueError):
                guardar_ciclos(destino, [])
            self.assertEqual(ajeno.read_text(encoding="utf-8"), "preservar")

    def test_guardado_rechaza_colision_con_archivo_no_administrado(self):
        with tempfile.TemporaryDirectory() as temporal, mock.patch("src.data.ingest.RAIZ", Path(temporal)):
            destino = Path(temporal) / "output/entregas"
            destino.mkdir(parents=True)
            ciclos = construir_ciclos(lote(mensaje()), 20)
            archivo = destino / ciclos[0]["archivo"]
            archivo.write_text("ajeno", encoding="utf-8")
            with self.assertRaises(ValueError):
                guardar_ciclos(destino, ciclos)
            self.assertEqual(archivo.read_text(encoding="utf-8"), "ajeno")

    def ejecutar_cli(self, carpeta, *extra):
        args = ["--entrada", str(carpeta / "entrada.json"), "--salida", str(carpeta / "filtrados.json"),
                "--informe", str(carpeta / "informe.json"), "--entrega-ia", str(carpeta / "ia"),
                "--fecha-referencia", FECHA, *map(str, extra)]
        with redirect_stdout(io.StringIO()):
            main(args)

    def test_cli_entrega_reproducible_y_fragmentos_completos(self):
        with tempfile.TemporaryDirectory() as temporal, mock.patch("src.data.ingest.RAIZ", Path(temporal)):
            carpeta = Path(temporal)
            datos = json.loads((RAIZ / "src/data/mensajes_comunidad_simulados.json").read_text(encoding="utf-8"))
            (carpeta / "entrada.json").write_text(json.dumps(datos), encoding="utf-8")
            args = ("--tamano-ciclo", 20, "--ciclos", carpeta / "output/entregas")
            self.ejecutar_cli(carpeta, *args)
            primera = {p.relative_to(carpeta).as_posix(): p.read_bytes() for p in carpeta.rglob("*.json")}
            self.ejecutar_cli(carpeta, *args)
            self.assertEqual(primera, {p.relative_to(carpeta).as_posix(): p.read_bytes() for p in carpeta.rglob("*.json")})
            manifest = json.loads((carpeta / "output/entregas/manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(sum(c["cantidad"] for c in manifest["ciclos"]), 23)
            self.assertEqual(len(json.loads((carpeta / "ia/estados_agente.json").read_text(encoding="utf-8"))), 23)

    def test_cli_errores_de_validacion_no_modifican_salidas(self):
        with tempfile.TemporaryDirectory() as temporal, mock.patch("src.data.ingest.RAIZ", Path(temporal)):
            carpeta = Path(temporal)
            entrada = carpeta / "entrada.json"
            salida = carpeta / "filtrados.json"
            salida.write_text("preservar", encoding="utf-8")
            entrada.write_text(json.dumps(lote(mensaje(fecha="ayer"))), encoding="utf-8")
            with self.assertRaises(SystemExit) as error:
                self.ejecutar_cli(carpeta)
            self.assertEqual(error.exception.code, 2)
            self.assertEqual(salida.read_text(encoding="utf-8"), "preservar")
            self.assertFalse((carpeta / "informe.json").exists())
            entrada.write_text(json.dumps(lote(mensaje())), encoding="utf-8")
            for destino in (carpeta / "output", carpeta):
                with self.assertRaises(SystemExit):
                    self.ejecutar_cli(carpeta, "--tamano-ciclo", 20, "--ciclos", destino)
                self.assertEqual(salida.read_text(encoding="utf-8"), "preservar")
            with self.assertRaises(SystemExit):
                self.ejecutar_cli(carpeta, "--salida", entrada)

if __name__ == "__main__":
    unittest.main()
