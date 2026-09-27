import json
from datetime import datetime, timezone
from pathlib import Path

from src.agents.graph import grafo
from src.data.entrega_ia import preparar_paquete_ia
from src.data.relevancia import ConfigRelevancia, leer_fecha


RUTA_DATASET = Path(
    "src/data/mensajes_comunidad_simulados.json"
)

IDS_PRUEBA = {
    "int-022",
    "int-002",
}


def cargar_dataset():
    with RUTA_DATASET.open(
        "r",
        encoding="utf-8",
    ) as archivo:
        return json.load(archivo)


def obtener_lotes(dataset):
    if "lotes" in dataset:
        return dataset["lotes"]

    if "interacciones" in dataset:
        return [dataset]

    raise ValueError(
        "El dataset no contiene "
        "'lotes' ni 'interacciones'."
    )


def obtener_fecha_referencia(lotes):
    fechas_validas = []

    for lote in lotes:
        for mensaje in lote.get(
            "interacciones",
            [],
        ):
            fecha = mensaje.get("fecha")

            if not fecha:
                continue

            try:
                fechas_validas.append(
                    leer_fecha(fecha)
                )
            except ValueError:
                continue

    if fechas_validas:
        return max(fechas_validas)

    return datetime.now(timezone.utc)


def obtener_evaluaciones_por_id(informe):
    evaluaciones = {}

    for lote in informe["lotes"]:
        for evaluacion in lote["evaluaciones"]:
            mensaje_id = evaluacion.get("id")

            if mensaje_id:
                evaluaciones[mensaje_id] = evaluacion

    return evaluaciones


def main():
    print("=" * 80)
    print("PRUEBA DATA -> DATA SCIENCE -> LANGGRAPH")
    print("=" * 80)

    dataset = cargar_dataset()
    lotes = obtener_lotes(dataset)
    config = ConfigRelevancia()

    fecha_referencia = obtener_fecha_referencia(
        lotes
    )

    paquete = preparar_paquete_ia(
        dataset,
        fecha_referencia=fecha_referencia,
        config=config,
    )

    estados_por_id = {
        estado["id"]: estado
        for estado in paquete["estados"]
    }

    evaluaciones_por_id = (
        obtener_evaluaciones_por_id(
            paquete["informe"]
        )
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
            f"los IDs en AgentState: "
            f"{faltantes}"
        )

    orden = [
        "int-022",
        "int-002",
    ]

    for numero, mensaje_id in enumerate(
        orden,
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
        print("ENTREGA DATA -> DATA SCIENCE")
        print("-" * 80)

        print(
            "Tipo original:",
            estado_inicial.get(
                "tipo_original"
            ),
        )
        print(
            "Score relevancia:",
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
            "AgentState recibido "
            "desde Data:"
        )
        print(estado_inicial)

        print()
        print(
            "Procesando con "
            "LangChain + LangGraph..."
        )

        resultado = grafo.invoke(
            estado_inicial
        )

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
        print("ROUTING")
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
    main()
