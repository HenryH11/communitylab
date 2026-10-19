import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from unittest.mock import patch

from src.agentes.grafo import procesar_paquete_entrega
from src.datos.entrega_ia import preparar_paquete_ia
from src.datos.relevancia import ConfiguracionRelevancia, leer_fecha


RUTA_CONJUNTO_DATOS = Path(
    "src/datos/mensajes_comunidad_simulados.json"
)

UMBRAL_RELEVANCIA = 40


def _obtener_lotes(conjunto_datos):
    if "lotes" in conjunto_datos:
        return conjunto_datos["lotes"]

    return [conjunto_datos]


def _fecha_referencia(conjunto_datos):
    fechas = []

    for lote in _obtener_lotes(conjunto_datos):
        for mensaje in lote.get(
            "interacciones",
            [],
        ):
            fecha = mensaje.get("fecha")

            if not fecha:
                continue

            try:
                fechas.append(
                    leer_fecha(fecha)
                )
            except ValueError:
                continue

    if fechas:
        return max(fechas)

    return datetime.now(timezone.utc)


@pytest.fixture(scope="module")
def paquete():
    with RUTA_CONJUNTO_DATOS.open(
        "r",
        encoding="utf-8",
    ) as archivo:
        conjunto_datos = json.load(archivo)

    return preparar_paquete_ia(
        conjunto_datos,
        fecha_referencia=_fecha_referencia(
            conjunto_datos
        ),
        configuracion=ConfiguracionRelevancia(),
    )


def test_estado_agente_respeta_contrato_ciencia_datos(
    paquete,
):
    estados = {
        estado["id"]: estado
        for estado in paquete["estados"]
    }

    estado = estados["int-022"]

    assert estado["tipo_original"] == "testimonio"
    assert estado["score_relevancia"] >= UMBRAL_RELEVANCIA
    assert estado["origen"] == "Discord_Grupo_ONE_G10"
    assert estado["idioma"] == "es"

    for campo in (
        "sentimiento",
        "tema_principal",
        "subtema",
        "tipo_detectado",
        "rutas",
        "activos_generados",
    ):
        assert campo not in estado


def test_separa_sentimiento_de_contenido(
    paquete,
):
    estados = {
        estado["id"]: estado
        for estado in paquete["estados"]
    }

    ids_contenido = set(
        paquete["plan"]["ids_contenido"]
    )

    assert "int-022" in estados
    assert "int-002" in estados
    assert "int-008" in estados

    assert "int-022" in ids_contenido
    assert "int-002" in ids_contenido
    assert "int-008" not in ids_contenido

    assert (
        estados["int-022"]["score_relevancia"]
        >= UMBRAL_RELEVANCIA
    )
    assert (
        estados["int-002"]["score_relevancia"]
        >= UMBRAL_RELEVANCIA
    )
    assert (
        estados["int-008"]["score_relevancia"]
        < UMBRAL_RELEVANCIA
    )


def test_tipo_original_se_conserva(
    paquete,
):
    estados = {
        estado["id"]: estado
        for estado in paquete["estados"]
    }

    assert (
        estados["int-002"]["tipo_original"]
        == "pregunta_tecnica"
    )
    assert (
        estados["int-008"]["tipo_original"]
        == "comentario"
    )


def test_grafo_consume_ciclos_de_datos_por_id_y_conserva_pendientes(
    paquete,
):
    def procesar_estados_sin_llm(estados, *, ids_contenido, tamano_lote):
        assert tamano_lote == 10
        return [
            {
                **estado,
                "sentimiento": "neutral",
                "rutas": [],
                "activos_generados": {},
            }
            for estado in estados
        ]

    with patch(
        "src.agentes.grafo.procesar_estados_por_lotes",
        side_effect=procesar_estados_sin_llm,
    ):
        resultado = procesar_paquete_entrega(paquete)

    ids_en_ciclos = [
        mensaje_id
        for ciclo in paquete["plan"]["ciclos"]
        for mensaje_id in ciclo["ids"]
    ]
    ids_procesados = [
        estado["id"]
        for estado in resultado["resultados"]
    ]

    assert ids_procesados == ids_en_ciclos
    assert resultado["ids_pendientes"] == paquete["plan"]["pendientes"]
    assert {
        estado["id"]
        for estado in resultado["pendientes"]
    } == set(paquete["plan"]["pendientes"])
