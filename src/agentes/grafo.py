from typing import Literal

from langgraph.graph import END, START, StateGraph

from src.agentes.nodos.nodo_analizador import analizar_lote, analizar_mensaje
from src.agentes.nodos.nodos_generadores import generar_activos
from src.agentes.nodos.nodo_enrutador import determinar_rutas
from src.agentes.estado_agente import EstadoAgente


MAX_INTERACCIONES_POR_SOLICITUD = 10


def comprobar_analisis(
    estado: EstadoAgente,
) -> Literal["continuar", "fallo"]:
    """
    Comprueba si el nodo de análisis terminó correctamente.
    """

    if estado.get("errores"):
        return "fallo"

    return "continuar"


def comprobar_rutas(
    estado: EstadoAgente,
) -> Literal["generar", "finalizar"]:
    """
    Decide si existen activos que generar.
    """

    if estado.get("rutas"):
        return "generar"

    return "finalizar"


def construir_grafo():
    flujo_trabajo = StateGraph(EstadoAgente)

    # Nodos
    flujo_trabajo.add_node(
        "analizar_mensaje",
        analizar_mensaje,
    )

    flujo_trabajo.add_node(
        "determinar_rutas",
        determinar_rutas,
    )

    flujo_trabajo.add_node(
        "generar_activos",
        generar_activos,
    )
    # Inicio
    flujo_trabajo.add_edge(
        START,
        "analizar_mensaje",
    )

    # Si el análisis falla, terminamos.
    # Si funciona, continúa al enrutador.
    flujo_trabajo.add_conditional_edges(
        "analizar_mensaje",
        comprobar_analisis,
        {
            "continuar": "determinar_rutas",
            "fallo": END,
        },
    )

    # Si existen rutas, generamos los activos.
    # Si no existen, finalizamos.
    flujo_trabajo.add_conditional_edges(
        "determinar_rutas",
        comprobar_rutas,
        {
            "generar": "generar_activos",
            "finalizar": END,
        },
    )

    flujo_trabajo.add_edge(
        "generar_activos",
        END,
    )

    return flujo_trabajo.compile()


def construir_grafo_desde_analisis():
    """Construye el tramo de enrutamiento y generación para estados ya analizados."""
    flujo_trabajo = StateGraph(EstadoAgente)
    flujo_trabajo.add_node("determinar_rutas", determinar_rutas)
    flujo_trabajo.add_node("generar_activos", generar_activos)
    flujo_trabajo.add_edge(START, "determinar_rutas")
    flujo_trabajo.add_conditional_edges(
        "determinar_rutas",
        comprobar_rutas,
        {
            "generar": "generar_activos",
            "finalizar": END,
        },
    )
    flujo_trabajo.add_edge("generar_activos", END)
    return flujo_trabajo.compile()


def procesar_estados_por_lotes(
    estados: list[EstadoAgente],
    *,
    ids_contenido: set[str] | None = None,
    tamano_lote: int = MAX_INTERACCIONES_POR_SOLICITUD,
) -> list[EstadoAgente]:
    """Analiza estados en lotes acotados y enruta cada resultado por separado."""
    if (
        type(tamano_lote) is not int
        or not 1 <= tamano_lote <= MAX_INTERACCIONES_POR_SOLICITUD
    ):
        raise ValueError(
            "El tamaño del lote debe estar entre 1 y "
            f"{MAX_INTERACCIONES_POR_SOLICITUD}"
        )

    ids = [estado.get("id") for estado in estados]
    if any(
        not isinstance(identificador, str)
        or not identificador.strip()
        or identificador != identificador.strip()
        for identificador in ids
    ):
        raise ValueError("El análisis por lotes requiere IDs válidos")
    if len(set(ids)) != len(ids):
        raise ValueError("El análisis por lotes requiere IDs únicos")

    resultados = []
    for inicio in range(0, len(estados), tamano_lote):
        grupo = estados[inicio : inicio + tamano_lote]
        analisis = analizar_lote(grupo)

        for estado, campos_analisis in zip(grupo, analisis):
            estado_actualizado = dict(estado)
            errores = list(estado_actualizado.get("errores", []))
            errores.extend(campos_analisis.get("errores", []))
            estado_actualizado.update(campos_analisis)

            if errores:
                estado_actualizado["errores"] = errores
                estado_actualizado["rutas"] = []
                estado_actualizado["activos_generados"] = {}
                resultados.append(estado_actualizado)
                continue

            if ids_contenido is not None:
                estado_actualizado["elegible_contenido"] = (
                    estado["id"] in ids_contenido
                )

            estado_actualizado.setdefault("rutas", [])
            estado_actualizado.setdefault("activos_generados", {})
            resultados.append(
                grafo_desde_analisis.invoke(estado_actualizado)
            )

    return resultados


def procesar_paquete_entrega(
    paquete: dict,
    *,
    tamano_lote: int = MAX_INTERACCIONES_POR_SOLICITUD,
) -> dict:
    """Ejecuta los ciclos planificados por ID y devuelve los estados pendientes."""
    estados = paquete["estados"]
    plan = paquete["plan"]
    estados_por_id = {}

    for estado in estados:
        identificador = estado.get("id")
        if (
            not isinstance(identificador, str)
            or not identificador.strip()
            or identificador != identificador.strip()
            or identificador in estados_por_id
        ):
            raise ValueError("El paquete contiene IDs inválidos o repetidos")
        estados_por_id[identificador] = estado

    ids_contenido = set(plan["ids_contenido"])
    if not ids_contenido.issubset(estados_por_id):
        raise ValueError("ids_contenido contiene IDs ausentes de los estados")

    ids_planificados = []
    for ciclo in plan["ciclos"]:
        ids_planificados.extend(ciclo["ids"])
    ids_pendientes = list(plan["pendientes"])

    if (
        len(ids_planificados + ids_pendientes)
        != len(set(ids_planificados + ids_pendientes))
        or set(ids_planificados + ids_pendientes) != set(estados_por_id)
    ):
        raise ValueError("Los ciclos y pendientes no cubren todos los estados por ID")

    ciclos_resultantes = []
    resultados = []

    for ciclo in plan["ciclos"]:
        estados_ciclo = [
            estados_por_id[identificador]
            for identificador in ciclo["ids"]
        ]
        resultados_ciclo = procesar_estados_por_lotes(
            estados_ciclo,
            ids_contenido=ids_contenido,
            tamano_lote=tamano_lote,
        )
        ciclos_resultantes.append(
            {
                "indice": ciclo["indice"],
                "ids": list(ciclo["ids"]),
                "resultados": resultados_ciclo,
            }
        )
        resultados.extend(resultados_ciclo)

    return {
        "resultados": resultados,
        "resultados_por_id": {
            resultado["id"]: resultado
            for resultado in resultados
        },
        "ciclos": ciclos_resultantes,
        "pendientes": [
            estados_por_id[identificador]
            for identificador in ids_pendientes
        ],
        "ids_pendientes": ids_pendientes,
    }


grafo = construir_grafo()
grafo_desde_analisis = construir_grafo_desde_analisis()