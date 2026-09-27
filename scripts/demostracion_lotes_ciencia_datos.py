from src.agentes.grafo import procesar_estados_por_lotes
from scripts.apoyo_demostraciones import (
    cargar_paquete_demostracion,
    obtener_evaluaciones_por_id,
)

IDS_PRUEBA = {
    "int-022",
    "int-002",
}


def principal():
    print("=" * 80)
    print("PRUEBA: DATOS -> CIENCIA DE DATOS -> LANGGRAPH")
    print("=" * 80)

    paquete = cargar_paquete_demostracion(tamano_ciclo=12)

    estados_por_id = {
        estado["id"]: estado
        for estado in paquete["estados"]
    }
    evaluaciones_por_id = obtener_evaluaciones_por_id(
        paquete["informe"]
    )

    ids_contenido = set(
        paquete["plan"]["ids_contenido"]
    )

    faltantes = (
        IDS_PRUEBA - estados_por_id.keys()
    )

    if faltantes:
        raise ValueError(
            f"No se encontraron "
            f"los IDs en EstadoAgente: "
            f"{faltantes}"
        )

    orden = ("int-022", "int-002")
    estados_prueba = [estados_por_id[mensaje_id] for mensaje_id in orden]
    resultados = procesar_estados_por_lotes(
        estados_prueba,
        ids_contenido=ids_contenido,
    )

    for numero, (mensaje_id, resultado) in enumerate(
        zip(orden, resultados),
        start=1,
    ):
        estado_inicial = (
            estados_por_id[mensaje_id]
        )

        evaluacion = (
            evaluaciones_por_id[mensaje_id]
        )

        print()
        print("=" * 80)
        print(
            f"CASO {numero}: "
            f"{mensaje_id}"
        )
        print("=" * 80)

        print(
            "Autor:",
            estado_inicial.get("autor"),
        )
        print(
            "Canal:",
            estado_inicial.get("canal"),
        )
        print(
            "Origen:",
            estado_inicial.get("origen"),
        )
        print(
            "Texto:",
            estado_inicial.get("texto"),
        )

        print()
        print("ENTREGA DATOS -> CIENCIA DE DATOS")
        print("-" * 80)

        print(
            "Tipo original:",
            estado_inicial.get(
                "tipo_original"
            ),
        )
        print(
            "Puntaje de relevancia:",
            estado_inicial.get(
                "score_relevancia"
            ),
        )
        print(
            "Incluido sentimiento:",
            evaluacion.get(
                "incluido_sentimiento"
            ),
        )
        print(
            "Elegible contenido:",
            mensaje_id in ids_contenido,
        )
        print(
            "Desglose:",
            evaluacion.get("desglose"),
        )

        print()
        print(
            "Estado del agente recibido "
            "desde Datos:"
        )
        print(estado_inicial)

        print()
        print("RESULTADO IA")
        print("-" * 80)

        print(
            "Sentimiento:",
            resultado.get("sentimiento"),
        )
        print(
            "Tema principal:",
            resultado.get(
                "tema_principal"
            ),
        )
        print(
            "Subtema:",
            resultado.get("subtema"),
        )
        print(
            "Tipo detectado:",
            resultado.get(
                "tipo_detectado"
            ),
        )

        print()
        print("ENRUTAMIENTO")
        print("-" * 80)

        print(
            "Rutas:",
            resultado.get("rutas"),
        )

        print()
        print("ACTIVOS GENERADOS")
        print("-" * 80)

        activos = resultado.get(
            "activos_generados",
            {},
        )

        for ruta, activo in activos.items():
            print()
            print(f"[{ruta}]")

            for clave, valor in activo.items():
                print(
                    f"{clave}: {valor}"
                )

        print()
        print(
            "Errores:",
            resultado.get("errores"),
        )

    print()
    print("=" * 80)
    print("PRUEBA FINALIZADA")
    print("=" * 80)


if __name__ == "__main__":
    principal()
