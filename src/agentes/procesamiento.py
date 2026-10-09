"""Procesamiento del paquete de Datos: validación, ciclos y recuperación final."""

import time

from src.agentes.grafo import MAX_INTERACCIONES_POR_SOLICITUD, procesar_estados_por_lotes
from src.agentes.observabilidad import (
    configurar_logging,
    contexto_ejecucion,
    registrar_evento,
)
from src.agentes.recuperacion import ids_reintentables, reprocesar_resultados


PASADAS_RECUPERACION = 1


def _validar_paquete(paquete: dict) -> tuple[dict, set[str], list[str]]:
    """Devuelve estados por ID, IDs de contenido y pendientes, o falla si el plan es inconsistente."""
    plan = paquete["plan"]
    estados_por_id = {}

    for estado in paquete["estados"]:
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

    ids_planificados = [
        identificador
        for ciclo in plan["ciclos"]
        for identificador in ciclo["ids"]
    ]
    ids_pendientes = list(plan["pendientes"])
    cubiertos = ids_planificados + ids_pendientes

    if len(cubiertos) != len(set(cubiertos)) or set(cubiertos) != set(estados_por_id):
        raise ValueError("Los ciclos y pendientes no cubren todos los estados por ID")

    return estados_por_id, ids_contenido, ids_pendientes


def _ejecutar_ciclos(paquete: dict, *, tamano_lote: int) -> dict:
    """Ejecuta los ciclos planificados por ID y devuelve los estados pendientes."""
    estados_por_id, ids_contenido, ids_pendientes = _validar_paquete(paquete)
    ciclos_resultantes = []
    resultados = []

    for ciclo in paquete["plan"]["ciclos"]:
        resultados_ciclo = procesar_estados_por_lotes(
            [estados_por_id[identificador] for identificador in ciclo["ids"]],
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


def procesar_paquete_entrega(
    paquete: dict,
    *,
    tamano_lote: int = MAX_INTERACCIONES_POR_SOLICITUD,
    pasadas_recuperacion: int = PASADAS_RECUPERACION,
) -> dict:
    """Procesa el paquete, registra la ejecución y recupera fallos transitorios."""
    configurar_logging()
    with contexto_ejecucion() as id_ejecucion:
        inicio = time.perf_counter()
        registrar_evento(
            "procesamiento_iniciado",
            total_estados=len(paquete["estados"]),
            ciclos=len(paquete["plan"]["ciclos"]),
            pendientes=len(paquete["plan"]["pendientes"]),
        )

        salida = _ejecutar_ciclos(paquete, tamano_lote=tamano_lote)
        salida["id_ejecucion"] = id_ejecucion

        for _ in range(pasadas_recuperacion):
            if not ids_reintentables(salida["resultados"]):
                break
            salida = reprocesar_resultados(
                salida,
                solo_reintentables=True,
                tamano_lote=tamano_lote,
            )

        registrar_evento(
            "procesamiento_finalizado",
            duracion_ms=round((time.perf_counter() - inicio) * 1000, 1),
            procesados=len(salida["resultados"]),
            con_fallos=sum(
                bool(resultado.get("fallos"))
                for resultado in salida["resultados"]
            ),
            ids_reintentables=ids_reintentables(salida["resultados"]),
        )
        return salida
