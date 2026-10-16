"""Auditoría de estrés de Datos con los 3 lotes de la Semana 4 (éxito, FAQ y ruido/spam).

Corre la preparación de Datos en paralelo y verifica cero caídas, resultados
idénticos entre corridas y las decisiones esperadas por caso. Sin IA ni red.
"""

import json
from pathlib import Path

import pytest

import scripts.estres_lotes_datos as estres
from src.datos.entrega_ia import preparar_paquete_ia
from src.datos.limpieza import limpiar_texto
from src.datos.relevancia import ConfiguracionRelevancia


RAIZ = Path(__file__).resolve().parents[1]
DATOS = json.loads(estres.FIXTURE.read_text(encoding="utf-8"))
CONFIGURACION = ConfiguracionRelevancia(**json.loads(estres.CONFIGURACION.read_text(encoding="utf-8")))


def evaluaciones(indice_lote):
    paquete = preparar_paquete_ia(estres.separar_lotes(DATOS)[indice_lote], fecha_referencia=estres.FECHA_REFERENCIA,
                                  configuracion=CONFIGURACION)
    return {e["id"]: e for e in paquete["informe"]["lotes"][0]["evaluaciones"]}


@pytest.fixture(scope="module")
def reporte():
    return estres.auditar(DATOS, configuracion=CONFIGURACION, repeticiones=3, hilos=3, volumen=5)


def test_los_tres_lotes_corren_en_paralelo_sin_caidas(reporte):
    resumen = reporte["resumen"]
    assert resumen["en_verde"], resumen
    assert resumen["caidas"] == resumen["distintas_a_la_referencia"] == resumen["entradas_modificadas"] == 0
    assert [l["origen_comunidad"] for l in reporte["fases"]["base"]][:3] == [
        "Estres_Casos_Exito", "Estres_Dudas_FAQ", "Estres_Ruido_Spam",
    ]


def test_juntos_forman_ciclos_y_por_separado_quedan_pendientes(reporte):
    *separados, juntos = reporte["fases"]["base"]
    assert all(l["ciclos"] == [] and l["pendientes"] == l["incluidas_sentimiento"] for l in separados)
    assert (juntos["total"], juntos["incluidas_sentimiento"], juntos["ciclos"]) == (29, 22, [11, 11])


def test_el_volumen_escala_sin_perder_mensajes(reporte):
    for base, ampliado in zip(reporte["fases"]["base"], reporte["fases"]["volumen"]):
        assert ampliado["total"] == 5 * base["total"]
        assert ampliado["incluidas_sentimiento"] == 5 * base["incluidas_sentimiento"]


def test_casos_de_exito_llegan_completos_a_contenido():
    casos = evaluaciones(0)
    assert len(casos) == 8
    assert all(e["seleccionado"] and e["incluido_sentimiento"] and not e["motivos"] for e in casos.values())


def test_dudas_de_faq_conservan_preguntas_y_recurrencia_entre_autores():
    casos = evaluaciones(1)
    assert sorted(i for i, e in casos.items() if e["elegible_faq"]) == [
        "faq-int-004", "faq-int-007", "faq-int-010", "faq-int-013", "faq-int-015",
    ]
    # La misma duda escrita por otra persona no es una copia.
    assert casos["faq-int-023"]["seleccionado"] and "duplicado" not in casos["faq-int-023"]["motivos"]


def test_ruido_y_spam_por_caso():
    casos = evaluaciones(2)
    excluidos = sorted(i for i, e in casos.items() if not e["incluido_sentimiento"])
    assert excluidos == ["ruido-02", "ruido-03", "ruido-04", "ruido-05", "ruido-06", "ruido-07", "ruido-12"]
    assert sorted(i for i, e in casos.items() if e["seleccionado"]) == ["ruido-10", "ruido-11"]
    assert "duplicado" in casos["ruido-07"]["motivos"]
    # Límite conocido: las reglas no detectan spam semántico. Queda fuera de contenido
    # solo por puntaje bajo y sigue en la población de sentimiento.
    assert casos["ruido-01"]["motivos"] == ["bajo_umbral"] and casos["ruido-01"]["incluido_sentimiento"]


def test_mojibake_de_windows_se_repara_al_original():
    roto = estres.leer_como_cp1252("ok 👍 acción")
    assert "\x8d" in roto and roto != "ok 👍 acción"
    assert limpiar_texto(roto) == "ok 👍 acción"


def test_una_caida_se_reporta_y_corta_el_verde(monkeypatch):
    original = estres.preparar_paquete_ia
    llamadas = {"ruido": 0}

    def falla_a_veces(datos, **opciones):
        if datos["lotes"][0]["origen_comunidad"] == "Estres_Ruido_Spam":
            llamadas["ruido"] += 1
            # La 1.ª es la corrida de referencia; la 2.ª, una de las concurrentes.
            if llamadas["ruido"] == 2:
                raise RuntimeError("caída simulada")
        return original(datos, **opciones)

    monkeypatch.setattr(estres, "preparar_paquete_ia", falla_a_veces)
    reporte = estres.auditar(DATOS, configuracion=CONFIGURACION, repeticiones=2, hilos=2, volumen=1)
    assert not reporte["resumen"]["en_verde"]
    assert reporte["resumen"]["caidas"] > 0
    assert "RuntimeError: caída simulada" in reporte["fases"]["base"][2]["errores"]


def test_cli_escribe_reportes_y_sale_en_cero(tmp_path, capsys):
    salida_json, salida_md = tmp_path / "estres.json", tmp_path / "estres.md"
    codigo = estres.principal(["--repeticiones", "2", "--volumen", "2", "--salida-json", str(salida_json),
                               "--salida-md", str(salida_md)])
    assert codigo == 0
    assert json.loads(salida_json.read_text(encoding="utf-8"))["resumen"]["en_verde"]
    assert salida_md.read_text(encoding="utf-8").startswith("Estado: EN VERDE")
    assert "EN VERDE" in capsys.readouterr().out
