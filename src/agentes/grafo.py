"""Grafo de LangGraph y ejecución por lotes; el paquete se procesa en procesamiento.py."""

import logging
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from typing import Literal, cast

from langgraph.graph import END, START, StateGraph

from src.agentes.configuracion_ia import (
    obtener_concurrencia_lotes_analisis,
    obtener_concurrencia_mensajes,
)
from src.agentes.estado_agente import EstadoAgente
from src.agentes.observabilidad import registrar_evento
from src.agentes.reintentos import construir_fallo, describir_error
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

    concurrencia = obtener_concurrencia_mensajes()
    trabajadores_lotes = obtener_concurrencia_lotes_analisis()

    def lotes_secuenciales():
        for inicio in range(0, len(estados), tamano_lote):
            grupo = estados[inicio : inicio + tamano_lote]
            yield grupo, analizar_lote_protegido(grupo)

    def analizar_lote_protegido(grupo):
        try:
            return analizar_lote(grupo)
        except Exception as error:
            registrar_evento(
                "analisis_lote_excepcion_inesperada",
                nivel=logging.ERROR,
                exc_info=error,
                etapa="analizar_lote",
                ids_interaccion=[estado["id"] for estado in grupo],
                tipo_error=type(error).__name__,
            )
            return [
                {
                    "errores": [
                        describir_error("analizar_lote", error)
                    ],
                    "fallos": [
                        construir_fallo(
                            "analizar_lote",
                            error,
                            id_interaccion=estado["id"],
                        )
                    ],
                }
                for estado in grupo
            ]

    if trabajadores_lotes == 1 or len(estados) <= tamano_lote:
        lotes_analizados = lotes_secuenciales()
    else:
        grupos = [
            estados[inicio : inicio + tamano_lote]
            for inicio in range(0, len(estados), tamano_lote)
        ]

        with ThreadPoolExecutor(
            max_workers=trabajadores_lotes
        ) as ejecutor:
            futuros = [
                ejecutor.submit(
                    copy_context().run,
                    analizar_lote_protegido,
                    grupo,
                )
                for grupo in grupos
            ]

            lotes_analizados = [
                (grupo, futuro.result())
                for grupo, futuro in zip(grupos, futuros)
            ]

    resultados = []
    for grupo, analisis in lotes_analizados:
        pendientes = []

        # Evitar que zip descarte mensajes silenciosamente.
        # Si el lote no cumple el contrato, no es seguro asociar
        # resultados parciales a los IDs por posición.
        if not isinstance(analisis, list) or len(analisis) != len(grupo):
            recibidos = (
                len(analisis)
                if isinstance(analisis, list)
                else "formato_invalido"
            )

            error = ValueError(
                f"analizar_lote devolvio {recibidos} resultados "
                f"para {len(grupo)} mensajes"
            )

            registrar_evento(
                "analisis_lote_cantidad_invalida",
                nivel=logging.ERROR,
                etapa="analizar_lote",
                ids_interaccion=[estado["id"] for estado in grupo],
                cantidad_esperada=len(grupo),
                cantidad_recibida=recibidos,
            )

            analisis = [
                {
                    "errores": [
                        describir_error("analizar_lote", error)
                    ],
                    "fallos": [
                        construir_fallo(
                            "analizar_lote",
                            error,
                            id_interaccion=estado["id"],
                        )
                    ],
                }
                for estado in grupo
            ]

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
                if concurrencia == 1:
                    resultados.append(estado_actualizado)
                else:
                    pendientes.append((False, estado_actualizado))
                continue

            estado_actualizado.setdefault("rutas", [])
            estado_actualizado.setdefault("activos_generados", {})

            if concurrencia == 1:
                resultados.append(
                    grafo_desde_analisis.invoke(estado_actualizado)
                )
            else:
                pendientes.append((True, estado_actualizado))

        if concurrencia == 2:
            with ThreadPoolExecutor(max_workers=2) as ejecutor:
                trabajos = [
                    (
                        procesar,
                        ejecutor.submit(
                            copy_context().run,
                            grafo_desde_analisis.invoke,
                            estado_pendiente,
                        ) if procesar else estado_pendiente,
                    )
                    for procesar, estado_pendiente in pendientes
                ]

                for (procesar, trabajo), (_, estado_pendiente) in zip(
                    trabajos, pendientes
                ):
                    if not procesar:
                        resultados.append(trabajo)
                        continue

                    try:
                        resultados.append(trabajo.result())
                    except Exception as error:
                        identificador = estado_pendiente.get("id")

                        registrar_evento(
                            "procesamiento_grafo_fallido",
                            nivel=logging.ERROR,
                            exc_info=error,
                            etapa="procesar_grafo",
                            id_interaccion=identificador,
                            tipo_error=type(error).__name__,
                        )

                        fallo = construir_fallo(
                            "procesar_grafo",
                            error,
                            id_interaccion=identificador,
                        )

                        # Sin conocer el nodo que fallo, no es seguro
                        # aplicar recuperacion automatica por ruta.
                        fallo["reintentable"] = False

                        resultados.append(
                            cast(
                                EstadoAgente,
                                {
                                    **estado_pendiente,
                                    "rutas": [],
                                    "activos_generados": {},
                                    "errores": [
                                        *estado_pendiente.get("errores", []),
                                        describir_error(
                                            "procesar_grafo", error
                                        ),
                                    ],
                                    "fallos": [
                                        *estado_pendiente.get("fallos", []),
                                        fallo,
                                    ],
                                },
                            )
                        )

    return resultados


def procesar_paquete_entrega(*args, **kwargs):
    """Compatibilidad: la implementación vive en src.agentes.procesamiento."""
    from src.agentes.procesamiento import procesar_paquete_entrega as _impl

    return _impl(*args, **kwargs)


grafo = construir_grafo()
grafo_desde_analisis = construir_grafo_desde_analisis()
