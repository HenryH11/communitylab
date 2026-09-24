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


RUTA_DATASET = Path("src/data/mensajes_comunidad_simulados.json")
CANTIDAD_MENSAJES = 3


def cargar_dataset():
    with RUTA_DATASET.open("r", encoding="utf-8") as archivo:
        return json.load(archivo)


def obtener_lotes(dataset):
    """
    Admite dos formatos:

    1. Dataset con varios lotes:
       {"lotes": [...]}

    2. Un único lote:
       {"origen_comunidad": ..., "interacciones": [...]}
    """

    if "lotes" in dataset:
        return dataset["lotes"]

    if "interacciones" in dataset:
        return [dataset]

    raise ValueError(
        "El dataset no contiene ni 'lotes' ni 'interacciones'."
    )


def obtener_fecha_referencia(lotes):
    """
    Obtiene la fecha válida más reciente de todos los lotes.
    """

    fechas_validas = []

    for lote in lotes:
        for mensaje in lote.get("interacciones", []):
            fecha = mensaje.get("fecha")

            if not fecha:
                continue

            try:
                fechas_validas.append(leer_fecha(fecha))
            except ValueError:
                continue

    if fechas_validas:
        return max(fechas_validas)

    return datetime.now(timezone.utc)


def main():
    print("=" * 80)
    print("PRUEBA DE 3 MENSAJES DEL DATASET")
    print("=" * 80)

    # --------------------------------------------------
    # 1. Cargar dataset
    # --------------------------------------------------

    dataset = cargar_dataset()
    lotes = obtener_lotes(dataset)

    total_interacciones = sum(
        len(lote.get("interacciones", []))
        for lote in lotes
    )

    print()
    print(f"Lotes encontrados: {len(lotes)}")
    print(f"Mensajes encontrados: {total_interacciones}")

    # --------------------------------------------------
    # 2. Configuración de relevancia
    # --------------------------------------------------

    config = ConfigRelevancia()

    fecha_referencia = obtener_fecha_referencia(lotes)

    print(
        "Fecha de referencia:",
        fecha_referencia.isoformat(),
    )

    # --------------------------------------------------
    # 3. Procesar relevancia lote por lote
    # --------------------------------------------------

    mensajes_relevantes = []

    for lote in lotes:

        seleccionados, evaluaciones = seleccionar_lote(
            lote,
            config,
            fecha_referencia,
        )

        evaluaciones_por_id = {
            evaluacion["id"]: evaluacion
            for evaluacion in evaluaciones
            if evaluacion["id"] is not None
        }

        for mensaje in seleccionados:

            mensaje_id = mensaje.get("id")

            mensajes_relevantes.append(
                {
                    "mensaje": mensaje,
                    "evaluacion": evaluaciones_por_id.get(
                        mensaje_id,
                        {},
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

    print(
        f"Mensajes que superaron relevancia: "
        f"{len(mensajes_relevantes)}"
    )

    # --------------------------------------------------
    # 4. Tomar solo 3
    # --------------------------------------------------

    mensajes_prueba = mensajes_relevantes[
        :CANTIDAD_MENSAJES
    ]

    print(
        f"Mensajes enviados al grafo: "
        f"{len(mensajes_prueba)}"
    )

    # --------------------------------------------------
    # 5. Ejecutar uno por uno
    # --------------------------------------------------

    for numero, item in enumerate(
        mensajes_prueba,
        start=1,
    ):

        mensaje = item["mensaje"]
        evaluacion = item["evaluacion"]

        mensaje_id = mensaje.get("id")
        score = evaluacion.get("puntaje")

        estado_inicial: AgentState = {
            "id": mensaje_id,
            "autor": mensaje.get("autor", ""),
            "canal": mensaje.get("canal", ""),
            "origen": item["origen"],
            "idioma": mensaje.get("idioma", "es"),
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
            f"MENSAJE {numero} "
            f"DE {len(mensajes_prueba)}"
        )
        print("=" * 80)

        print("ID:", mensaje_id)
        print("Origen:", item["origen"])
        print("Periodo:", item["periodo"])
        print("Autor:", mensaje.get("autor"))
        print("Canal:", mensaje.get("canal"))
        print("Texto:", mensaje["texto"])

        print()
        print("DATOS / RELEVANCIA")
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
            evaluacion.get("desglose"),
        )
        print(
            "Palabras clave:",
            evaluacion.get(
                "palabras_clave"
            ),
        )

        print()
        print(
            "Procesando con "
            "LangChain + LangGraph..."
        )

        # --------------------------------------------------
        # 6. Ejecutar grafo
        # --------------------------------------------------

        resultado = grafo.invoke(
            estado_inicial
        )

        # --------------------------------------------------
        # 7. Resultado
        # --------------------------------------------------

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
        print(
            "Activos:",
            resultado.get(
                "activos_generados"
            ),
        )
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