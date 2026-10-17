"""Pruebas del evaluador de proveedores: sentimiento y métricas.

Todas las pruebas funcionan sin llamadas a proveedores LLM.
"""
import hashlib
import json
import sys

import pytest

import scripts.evaluar_holdout_proveedores as evaluador
from scripts.evaluar_holdout_proveedores import (
    FIXTURE_POR_DEFECTO,
    cargar_holdout,
    estabilidad,
    evaluar_corrida,
    normalizar_sentimiento,
    resultados_moda,
)


def construir_corridas_simuladas(sentimientos: list[str]) -> list[dict]:
    return [
        {
            "resultados": {
                "test-001": {
                    "sentimiento": sentimiento,
                    "tema_principal": "datos_ia",
                    "tipo_detectado": "comentario",
                }
            }
        }
        for sentimiento in sentimientos
    ]

@pytest.mark.parametrize(
    "original, esperado",
    [
        ("muy_positivo", "positivo"),
        ("positivo", "positivo"),
        ("neutral", "neutral"),
        ("negativo", "negativo"),
        ("muy_negativo", "negativo"),
    ],
)
def test_normalizar_sentimiento_tres_clases(original, esperado):
    resultado = normalizar_sentimiento(original, "3-clases")

    assert resultado == esperado


@pytest.mark.parametrize(
    "sentimiento",
    [
        "muy_positivo",
        "positivo",
        "neutral",
        "negativo",
        "muy_negativo",
    ],
)
def test_modo_exacto_conserva_cinco_clases(sentimiento):
    resultado = normalizar_sentimiento(sentimiento, "exacto")

    assert resultado == sentimiento


def test_rechaza_sentimiento_desconocido():
    with pytest.raises(ValueError, match="Sentimiento no reconocido"):
        normalizar_sentimiento("desconocido", "3-clases")


def test_rechaza_modo_desconocido():
    with pytest.raises(ValueError, match="Modo de sentimiento no reconocido"):
        normalizar_sentimiento("positivo", "modo-invalido")


@pytest.mark.parametrize(
    "sentimiento_predicho, sentimiento_esperado, modo, correctos",
    [
        ("muy_positivo", "positivo", "exacto", 0),
        ("muy_positivo", "positivo", "3-clases", 1),
        ("muy_negativo", "negativo", "exacto", 0),
        ("muy_negativo", "negativo", "3-clases", 1),
    ],
)
def test_accuracy_y_triple_correcto(
    sentimiento_predicho,
    sentimiento_esperado,
    modo,
    correctos,
):
    casos = [{
        "id": "test-001",
        "sentimiento_esperado": sentimiento_esperado,
        "tema_esperado": "datos_ia",
        "tipo_esperado": "comentario",
    }]

    resultados = {
        "test-001": {
            "sentimiento": sentimiento_predicho,
            "tema_principal": "datos_ia",
            "tipo_detectado": "comentario",
        }
    }

    metricas = evaluar_corrida(casos, resultados, modo)

    assert metricas["sentimiento"]["correctos"] == correctos
    assert metricas["triple_correcto"]["correctos"] == correctos

    assert metricas["tema_principal"]["correctos"] == 1
    assert metricas["tipo_detectado"]["correctos"] == 1

    assert metricas["sentimiento"]["por_clase"][
        sentimiento_esperado
    ]["total"] == 1

@pytest.mark.parametrize(
    "sentimientos, esperado_exacto, esperado_agrupado",
    [
        (
            ["muy_positivo", "positivo", "neutral"],
            "muy_positivo",
            "positivo",
        ),
        (
            ["muy_negativo", "negativo", "neutral"],
            "muy_negativo",
            "negativo",
        ),
    ],
)
def test_moda_respeta_modo_sentimiento(
    sentimientos,
    esperado_exacto,
    esperado_agrupado,
):
    casos = [{"id": "test-001"}]

    corridas = construir_corridas_simuladas(sentimientos)

    exacto = resultados_moda(casos, corridas, "exacto")
    agrupado = resultados_moda(casos, corridas, "3-clases")

    assert exacto["test-001"]["sentimiento"] == esperado_exacto
    assert agrupado["test-001"]["sentimiento"] == esperado_agrupado

    assert exacto["test-001"]["tema_principal"] == "datos_ia"
    assert agrupado["test-001"]["tipo_detectado"] == "comentario"


@pytest.mark.parametrize(
    "sentimientos",
    [
        ["muy_positivo", "positivo", "positivo"],
        ["muy_negativo", "negativo", "negativo"],
    ],
)
def test_estabilidad_respeta_modo_sentimiento(sentimientos):
    casos = [{"id": "test-001"}]

    corridas = [
        {
            "resultados": {
                "test-001": {
                    "sentimiento": sentimiento,
                    "tema_principal": "datos_ia",
                    "tipo_detectado": "comentario",
                }
            }
        }
        for sentimiento in sentimientos
    ]

    exacto = estabilidad(casos, corridas, "exacto")
    agrupado = estabilidad(casos, corridas, "3-clases")

    assert exacto["sentimiento"]["estables"] == 0
    assert agrupado["sentimiento"]["estables"] == 1

    assert exacto["tema_principal"]["estables"] == 1
    assert agrupado["tema_principal"]["estables"] == 1

    assert exacto["tipo_detectado"]["estables"] == 1
    assert agrupado["tipo_detectado"]["estables"] == 1


@pytest.mark.parametrize(
    "variante, mensaje_esperado",
    [
        ("vacio", "al menos un caso"),
        ("incompleto", "campos obligatorios"),
        ("duplicado", "IDs duplicados"),
        ("id_invalido", "ID inválido"),
        ("tipo_invalido", "objeto JSON"),
    ],
)
def test_rechaza_fixtures_invalidos(
    tmp_path, variante, mensaje_esperado
):
    caso_valido = {
        "id": "test-001",
        "texto": "Estoy aprendiendo Python.",
        "origen": "Discord",
        "canal": "general",
        "idioma": "es",
        "sentimiento_esperado": "positivo",
        "tema_esperado": "programacion",
        "tipo_esperado": "comentario",
    }

    variantes = {
        "vacio": [],
        "incompleto": [{"id": "test-001"}],
        "duplicado": [caso_valido, caso_valido.copy()],
        "id_invalido": [{**caso_valido, "id": ""}],
        "tipo_invalido": ["mensaje sin estructura"],
    }

    ruta = tmp_path / "fixture.json"
    ruta.write_text(
        json.dumps({"casos": variantes[variante]}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=mensaje_esperado):
        cargar_holdout(ruta)


def test_holdout_v1_carga_y_hash_sin_modificaciones():
    contenido_antes = FIXTURE_POR_DEFECTO.read_bytes()
    hash_antes = hashlib.sha256(contenido_antes).hexdigest()

    casos, hash_evaluador = cargar_holdout(FIXTURE_POR_DEFECTO)

    assert len(casos) == 30
    assert len({caso["id"] for caso in casos}) == 30
    assert hash_evaluador == hash_antes

    contenido_despues = FIXTURE_POR_DEFECTO.read_bytes()

    assert contenido_antes == contenido_despues


@pytest.mark.parametrize(
    "argumento_modo, modo_esperado, accuracy_primera, estables",
    [
        ([], "exacto", 0, 0),
        (["--modo-sentimiento", "exacto"], "exacto", 0, 0),
        (["--modo-sentimiento", "3-clases"], "3-clases", 1, 1),
    ],
)
def test_main_respeta_modo_y_guarda_json(
    tmp_path,
    monkeypatch,
    argumento_modo,
    modo_esperado,
    accuracy_primera,
    estables,
):
    fixture = tmp_path / "fixture.json"
    salida = tmp_path / "resultados"

    fixture.write_text(
        json.dumps({
            "casos": [{
                "id": "test-001",
                "texto": "Me gusta aprender inteligencia artificial.",
                "origen": "Discord",
                "canal": "general",
                "idioma": "es",
                "sentimiento_esperado": "positivo",
                "tema_esperado": "datos_ia",
                "tipo_esperado": "comentario",
            }]
        }),
        encoding="utf-8",
    )

    llamadas = []
    sentimientos = ["muy_positivo", "positivo", "positivo"]

    def ejecutar_corrida_simulada(
        proveedor,
        numero_corrida,
        casos,
        tamano_lote,
        max_intentos,
        pausa,
        huella,
        salida,
    ):
        llamadas.append((proveedor, numero_corrida))

        return {
            "resultados": {
                "test-001": {
                    "sentimiento": sentimientos[numero_corrida - 1],
                    "tema_principal": "datos_ia",
                    "tipo_detectado": "comentario",
                }
            },
            "retries": [],
            "tiempos": [0.1],
        }

    monkeypatch.setattr(
        evaluador,
        "ejecutar_corrida",
        ejecutar_corrida_simulada,
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "evaluar_holdout_proveedores.py",
            "--fixture", str(fixture),
            "--salida", str(salida),
            "--corridas", "3",
            *argumento_modo,
        ],
    )

    evaluador.main()

    # Tres corridas por proveedor: NVIDIA + Gemini.
    assert len(llamadas) == 6

    ruta_resumen = salida / "resumen_holdout_final.json"
    assert ruta_resumen.exists()

    resumen = json.loads(ruta_resumen.read_text(encoding="utf-8"))

    assert resumen["modo_sentimiento"] == modo_esperado
    assert resumen["casos"] == 1
    assert resumen["corridas_por_proveedor"] == 3

    for proveedor in ("nvidia", "gemini"):
        datos = resumen[proveedor]

        primera = datos["metricas_por_corrida"][0]

        assert (
            primera["sentimiento"]["accuracy"]
            == accuracy_primera
        )

        assert (
            datos["metricas_moda"]["triple_correcto"]["accuracy"]
            == 1
        )

        assert (
            datos["estabilidad"]["sentimiento"]["estables"]
            == estables
        )

        assert datos["retries_externos"] == 0
        assert datos["tiempo_total_lotes_s"] == 0.3
