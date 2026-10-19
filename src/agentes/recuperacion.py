"""Recuperación de fallos: reanaliza o regenera solo lo que falló."""

from typing import cast

from src.agentes.estado_agente import EstadoAgente
from src.agentes.grafo import MAX_INTERACCIONES_POR_SOLICITUD, procesar_estados_por_lotes
from src.agentes.nodos.nodos_generadores import generar_activos
from src.agentes.observabilidad import (
    configurar_logging,
    contexto_ejecucion,
    registrar_evento,
)


_ETAPAS_ANALISIS = {"analizar_lote", "analizar_mensaje"}
_CAMPOS_RESULTADO_IA = (
    "sentimiento",
    "tema_principal",
    "subtema",
    "tipo_detectado",
    "rutas",
    "activos_generados",
    "errores",
    "fallos",
)


def _fallos_objetivo(resultado: dict, solo_reintentables: bool) -> list[dict]:
    return [
        fallo
        for fallo in resultado.get("fallos", [])
        if not solo_reintentables or fallo.get("reintentable") is True
    ]


def ids_reintentables(resultados: list[dict]) -> list[str]:
    return [
        resultado["id"]
        for resultado in resultados
        if _fallos_objetivo(resultado, solo_reintentables=True)
    ]


def _regenerar_rutas(resultado: dict, fallos_objetivo: list[dict]) -> dict:
    """Genera de nuevo solo las rutas fallidas y conserva los activos existentes."""
    rutas = list(
        dict.fromkeys(
            fallo["ruta"] for fallo in fallos_objetivo if fallo.get("ruta")
        )
    )
    if not rutas:
        return resultado

    prefijos = tuple(
        f"{fallo['etapa']}[{fallo['ruta']}]"
        for fallo in fallos_objetivo
        if fallo.get("ruta")
    )
    nuevo = generar_activos(
        cast(
            EstadoAgente,
            {**resultado, "rutas": rutas, "errores": [], "fallos": []},
        )
    )
    return {
        **resultado,
        "activos_generados": {
            **resultado.get("activos_generados", {}),
            **nuevo["activos_generados"],
        },
        "errores": [
            error
            for error in resultado.get("errores", [])
            if not error.startswith(prefijos)
        ]
        + nuevo["errores"],
        "fallos": [
            fallo
            for fallo in resultado.get("fallos", [])
            if fallo not in fallos_objetivo
        ]
        + nuevo["fallos"],
    }


def _reanalizar(resultados: list[dict], indices: list[int], tamano_lote: int) -> None:
    estados = [
        cast(
            EstadoAgente,
            {
                campo: valor
                for campo, valor in resultados[indice].items()
                if campo not in _CAMPOS_RESULTADO_IA
            },
        )
        for indice in indices
    ]
    nuevos = procesar_estados_por_lotes(estados, tamano_lote=tamano_lote)
    for indice, nuevo in zip(indices, nuevos):
        resultados[indice] = cast(dict, nuevo)


def reprocesar_resultados(
    salida: dict,
    *,
    solo_reintentables: bool,
    tamano_lote: int,
) -> dict:
    """Aplica una pasada de recuperación dentro de la ejecución actual."""
    resultados = list(salida["resultados"])
    indices_analisis = []
    ids_intentados = []

    for indice, resultado in enumerate(resultados):
        objetivo = _fallos_objetivo(resultado, solo_reintentables)
        if not objetivo:
            continue
        ids_intentados.append(resultado["id"])
        if any(fallo["etapa"] in _ETAPAS_ANALISIS for fallo in objetivo):
            indices_analisis.append(indice)
        else:
            resultados[indice] = _regenerar_rutas(resultado, objetivo)

    if indices_analisis:
        _reanalizar(resultados, indices_analisis, tamano_lote)

    por_id = {resultado["id"]: resultado for resultado in resultados}
    recuperados = [
        identificador
        for identificador in ids_intentados
        if not por_id[identificador].get("fallos")
    ]
    registrar_evento(
        "reprocesamiento_finalizado",
        intentados=len(ids_intentados),
        recuperados=len(recuperados),
        ids_sin_recuperar=[
            identificador
            for identificador in ids_intentados
            if identificador not in recuperados
        ],
    )

    return {
        **salida,
        "resultados": resultados,
        "resultados_por_id": por_id,
        "ciclos": [
            {
                **ciclo,
                "resultados": [
                    por_id[resultado["id"]] for resultado in ciclo["resultados"]
                ],
            }
            for ciclo in salida.get("ciclos", [])
        ],
        "reprocesamientos": [
            *salida.get("reprocesamientos", []),
            {
                "ids_intentados": ids_intentados,
                "ids_recuperados": recuperados,
            },
        ],
    }


def reprocesar_fallidos(
    salida: dict,
    *,
    solo_reintentables: bool = True,
    tamano_lote: int = MAX_INTERACCIONES_POR_SOLICITUD,
) -> dict:
    """Reintenta solo análisis o rutas fallidas sin repetir trabajo completado."""
    configurar_logging()
    with contexto_ejecucion(salida.get("id_ejecucion")):
        return reprocesar_resultados(
            salida,
            solo_reintentables=solo_reintentables,
            tamano_lote=tamano_lote,
        )
