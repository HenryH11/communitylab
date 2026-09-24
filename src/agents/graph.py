from typing import Literal

from langgraph.graph import END, START, StateGraph

from src.agents.nodes.analyzer_node import analizar_mensaje
from src.agents.nodes.generator_nodes import generar_activos
from src.agents.nodes.router_node import determinar_rutas
from src.agents.state import AgentState


def comprobar_analisis(
    state: AgentState,
) -> Literal["continuar", "error"]:
    """
    Comprueba si el nodo de análisis terminó correctamente.
    """

    if state.get("errores"):
        return "error"

    return "continuar"


def comprobar_rutas(
    state: AgentState,
) -> Literal["generar", "finalizar"]:
    """
    Decide si existen activos que generar.
    """

    if state.get("rutas"):
        return "generar"

    return "finalizar"


def construir_grafo():
    workflow = StateGraph(AgentState)

    # Nodos
    workflow.add_node(
        "analizar_mensaje",
        analizar_mensaje,
    )

    workflow.add_node(
        "determinar_rutas",
        determinar_rutas,
    )

    workflow.add_node(
        "generar_activos",
        generar_activos,
    )
    # Inicio
    workflow.add_edge(
        START,
        "analizar_mensaje",
    )

    # Si el análisis falla, terminamos.
    # Si funciona, continuamos al router.
    workflow.add_conditional_edges(
        "analizar_mensaje",
        comprobar_analisis,
        {
            "continuar": "determinar_rutas",
            "error": END,
        },
    )

    # Si existen rutas, generamos los MOCK.
    # Si no existen, finalizamos.
    workflow.add_conditional_edges(
        "determinar_rutas",
        comprobar_rutas,
        {
            "generar": "generar_activos",
            "finalizar": END,
        },
    )

    workflow.add_edge(
        "generar_activos",
        END,
    )

    return workflow.compile()


grafo = construir_grafo()