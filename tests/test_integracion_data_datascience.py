import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.data.entrega_ia import preparar_paquete_ia
from src.data.relevancia import ConfigRelevancia, leer_fecha


RUTA_DATASET = Path(
    "src/data/mensajes_comunidad_simulados.json"
)

UMBRAL_RELEVANCIA = 40


def _obtener_lotes(dataset):
    if "lotes" in dataset:
        return dataset["lotes"]

    return [dataset]


def _fecha_referencia(dataset):
    fechas = []

    for lote in _obtener_lotes(dataset):
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
    with RUTA_DATASET.open(
        "r",
        encoding="utf-8",
    ) as archivo:
        dataset = json.load(archivo)

    return preparar_paquete_ia(
        dataset,
        fecha_referencia=_fecha_referencia(
            dataset
        ),
        config=ConfigRelevancia(),
    )


def test_agentstate_respeta_contrato_data_science(
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
