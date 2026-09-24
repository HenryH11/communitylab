import json
from datetime import datetime, timezone
from pathlib import Path

from src.agents.graph import grafo
from src.agents.state import AgentState
from src.data.relevancia import (
    ConfigRelevancia,
    leer_fecha,
    seleccionar_lote,
)


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


def main():
    print("=" * 80)
    print("PRUEBA DE 2 MENSAJES REALES")
    print("=" * 80)

    dataset = cargar_dataset()
    lotes = obtener_lotes(dataset)

    config = ConfigRelevancia()

    fecha_referencia = (
        obtener_fecha_referencia(lotes)
    )

    casos = []

    # --------------------------------------------------
    # Buscar los dos mensajes reales
    # y calcular su relevancia
    # --------------------------------------------------

    for lote in lotes:
        seleccionados, evaluaciones = (
            seleccionar_lote(
                lote,
                config,
                fecha_referencia,
            )
        )

        evaluaciones_por_id = {
            evaluacion["id"]: evaluacion
            for evaluacion in evaluaciones
            if evaluacion["id"] is not None
        }

        for mensaje in lote.get(
            "interacciones",
            [],
        ):
            mensaje_id = mensaje.get("id")

            if mensaje_id not in IDS_PRUEBA:
                continue

            casos.append(
                {
                    "mensaje": mensaje,
                    "evaluacion": (
                        evaluaciones_por_id[
                            mensaje_id
                        ]
                    ),
                    "origen": lote.get(
                        "origen_comunidad",
                        "",
                    ),
                    "periodo": lote.get(
                        "periodo_referencia",
                        "",
                    ),
                }
            )

    if len(casos) != len(IDS_PRUEBA):
        encontrados = {
            item["mensaje"]["id"]
            for item in casos
        }

        faltantes = (
            IDS_PRUEBA - encontrados
        )

        raise ValueError(
            f"No se encontraron "
            f"los IDs: {faltantes}"
        )

    # Para que la salida sea siempre
    # int-022 y luego int-002
    orden = {
        "int-022": 1,
        "int-002": 2,
    }

    casos.sort(
        key=lambda item: orden[
            item["mensaje"]["id"]
        ]
    )

    # --------------------------------------------------
    # Procesar uno por uno
    # --------------------------------------------------

    for numero, item in enumerate(
        casos,
        start=1,
    ):
        mensaje = item["mensaje"]
        evaluacion = item["evaluacion"]

        score = evaluacion["puntaje"]

        estado_inicial: AgentState = {
            "id": mensaje["id"],
            "autor": mensaje.get(
                "autor",
                "",
            ),
            "canal": mensaje.get(
                "canal",
                "",
            ),
            "origen": item["origen"],
            "idioma": mensaje.get(
                "idioma",
                "es",
            ),
            "texto": mensaje["texto"],
            "tipo_original": mensaje.get(
                "tipo",
                "",
            ),
            "score_relevancia": score,
            "rutas": [],
            "activos_generados": {},
            "errores": [],
        }

        print()
        print("=" * 80)
        print(
            f"CASO {numero}: "
            f"{mensaje['id']}"
        )
        print("=" * 80)

        print(
            "Autor:",
            mensaje.get("autor"),
        )
        print(
            "Canal:",
            mensaje.get("canal"),
        )
        print(
            "Texto:",
            mensaje["texto"],
        )

        print()
        print("DATOS")
        print("-" * 80)

        print(
            "Tipo original:",
            mensaje.get("tipo"),
        )
        print(
            "Score relevancia:",
            score,
        )
        print(
            "Desglose:",
            evaluacion.get(
                "desglose"
            ),
        )

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
            resultado.get(
                "sentimiento"
            ),
        )
        print(
            "Tema principal:",
            resultado.get(
                "tema_principal"
            ),
        )
        print(
            "Subtema:",
            resultado.get(
                "subtema"
            ),
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

        for ruta, activo in (
            activos.items()
        ):
            print()
            print(f"[{ruta}]")

            for clave, valor in (
                activo.items()
            ):
                print(
                    f"{clave}: {valor}"
                )

        print()
        print(
            "Errores:",
            resultado.get(
                "errores"
            ),
        )

    print()
    print("=" * 80)
    print("PRUEBA FINALIZADA")
    print("=" * 80)


if __name__ == "__main__":
    main()