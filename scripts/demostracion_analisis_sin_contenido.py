from src.agentes.grafo import procesar_estados_por_lotes
from scripts.apoyo_demostraciones import (
    cargar_paquete_demostracion,
    obtener_evaluaciones_por_id,
)

ID_PRUEBA = "int-008"
UMBRAL_RELEVANCIA = 40


def principal():
    paquete = cargar_paquete_demostracion(tamano_ciclo=12)

    estados_por_id = {
        estado["id"]: estado
        for estado in paquete["estados"]
    }

    evaluaciones_por_id = obtener_evaluaciones_por_id(
        paquete["informe"]
    )

    estado = estados_por_id[ID_PRUEBA]
    evaluacion = evaluaciones_por_id[ID_PRUEBA]

    ids_contenido = set(
        paquete["plan"]["ids_contenido"]
    )

    print("=" * 80)
    print("PRUEBA DE SENTIMIENTO SIN GENERACIÓN DE CONTENIDO")
    print("=" * 80)

    print()
    print("ESTADO DEL AGENTE DESDE DATOS")
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
        "Puntaje de relevancia:",
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

    resultado = procesar_estados_por_lotes(
        [estado],
        ids_contenido=ids_contenido,
    )[0]

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
            f"{resultado.get('errores')}"
        )

    if not resultado.get("sentimiento"):
        raise AssertionError(
            "El mensaje debe ser analizado "
            "para sentimiento."
        )

    print()
    print("VALIDACIÓN: OK")


if __name__ == "__main__":
    principal()
