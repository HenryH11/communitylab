import json
from pathlib import Path

from src.agents.graph import grafo
from src.data.entrega_ia import preparar_paquete_ia
from src.data.relevancia import ConfigRelevancia
from scripts.probar_grafo_2_mensajes_reales import (
    obtener_fecha_referencia,
    obtener_lotes,
)


RUTA_DATASET = Path(
    "src/data/mensajes_comunidad_simulados.json"
)

ID_PRUEBA = "int-008"
UMBRAL_RELEVANCIA = 40


def main():
    with RUTA_DATASET.open(
        "r",
        encoding="utf-8",
    ) as archivo:
        dataset = json.load(archivo)

    paquete = preparar_paquete_ia(
        dataset,
        fecha_referencia=obtener_fecha_referencia(
            obtener_lotes(dataset)
        ),
        config=ConfigRelevancia(),
    )

    estados_por_id = {
        estado["id"]: estado
        for estado in paquete["estados"]
    }

    evaluaciones_por_id = {
        evaluacion["id"]: evaluacion
        for lote in paquete["informe"]["lotes"]
        for evaluacion in lote["evaluaciones"]
        if evaluacion.get("id")
    }

    estado = estados_por_id[ID_PRUEBA]
    evaluacion = evaluaciones_por_id[ID_PRUEBA]

    ids_contenido = set(
        paquete["plan"]["ids_contenido"]
    )

    print("=" * 80)
    print("PRUEBA SENTIMIENTO SIN CONTENIDO")
    print("=" * 80)

    print()
    print("AGENTSTATE DESDE DATA")
    print(estado)

    print()
    print(
        "Incluido en sentimiento:",
        evaluacion.get("incluido_sentimiento"),
    )
    print(
        "Elegible para contenido:",
        ID_PRUEBA in ids_contenido,
    )
    print(
        "Score relevancia:",
        estado["score_relevancia"],
    )

    if not evaluacion.get("incluido_sentimiento"):
        raise AssertionError(
            "El caso debería pertenecer "
            "a la población de sentimiento."
        )

    if ID_PRUEBA in ids_contenido:
        raise AssertionError(
            "El caso no debería pertenecer "
            "a la población de contenido."
        )

    if estado["score_relevancia"] >= UMBRAL_RELEVANCIA:
        raise AssertionError(
            "El caso debe estar por debajo "
            f"del umbral {UMBRAL_RELEVANCIA}."
        )

    print()
    print("Procesando con LangGraph...")

    resultado = grafo.invoke(estado)

    print()
    print("RESULTADO")
    print(
        "Sentimiento:",
        resultado.get("sentimiento"),
    )
    print(
        "Tema:",
        resultado.get("tema_principal"),
    )
    print(
        "Tipo:",
        resultado.get("tipo_detectado"),
    )
    print(
        "Rutas:",
        resultado.get("rutas"),
    )
    print(
        "Activos:",
        resultado.get(
            "activos_generados",
            {},
        ),
    )
    print(
        "Errores:",
        resultado.get("errores", []),
    )

    if resultado.get("rutas"):
        raise AssertionError(
            "Un mensaje bajo el umbral "
            "no debe activar rutas."
        )

    if resultado.get(
        "activos_generados",
        {},
    ):
        raise AssertionError(
            "Un mensaje no elegible "
            "no debe generar activos."
        )

    if resultado.get("errores"):
        raise AssertionError(
            "El grafo terminó con errores: "
            f"{resultado['errores']}"
        )

    if not resultado.get("sentimiento"):
        raise AssertionError(
            "El mensaje debe ser analizado "
            "para sentimiento."
        )

    print()
    print("VALIDACIÓN: OK")


if __name__ == "__main__":
    main()
