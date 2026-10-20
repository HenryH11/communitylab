"""Grafo de LangGraph y ejecución por lotes; el paquete se procesa en procesamiento.py."""

from typing import Literal, cast

from langgraph.graph import END, START, StateGraph

from src.agentes.estado_agente import EstadoAgente
from src.agentes.nodos.nodo_analizador import analizar_lote, analizar_mensaje
from src.agentes.nodos.nodo_enrutador import determinar_rutas
from src.agentes.nodos.nodos_generadores import generar_activos


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
            errores = [
                *estado.get("errores", []),
                *campos_analisis.get("errores", []),
            ]
            fallos = [
                *estado.get("fallos", []),
                *campos_analisis.get("fallos", []),
            ]
            estado_actualizado = cast(
                EstadoAgente,
                {**estado, **campos_analisis},
            )

            if ids_contenido is not None:
                estado_actualizado["elegible_contenido"] = (
                    estado["id"] in ids_contenido
                )

            if errores:
                estado_actualizado["errores"] = errores
                estado_actualizado["fallos"] = fallos
                estado_actualizado["rutas"] = []
                estado_actualizado["activos_generados"] = {}
                resultados.append(estado_actualizado)
                continue

            estado_actualizado.setdefault("rutas", [])
            estado_actualizado.setdefault("activos_generados", {})
            resultados.append(
                grafo_desde_analisis.invoke(estado_actualizado)
            )

    return resultados


def procesar_paquete_entrega(*args, **kwargs):
    """Compatibilidad: la implementación vive en src.agentes.procesamiento."""
    from src.agentes.procesamiento import procesar_paquete_entrega as _impl

    return _impl(*args, **kwargs)


grafo = construir_grafo()
grafo_desde_analisis = construir_grafo_desde_analisis()
