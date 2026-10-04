import json

from src.agentes.cadenas import cadena_analisis, cadena_analisis_lote
from src.agentes.modelos import AnalisisLote, AnalisisMensaje
from src.agentes.estado_agente import EstadoAgente


def _entrada_analisis(estado: EstadoAgente) -> dict:
    return {
        "origen": estado.get("origen", ""),
        "canal": estado.get("canal", ""),
        "idioma": estado.get("idioma", "es"),
        "tipo_original": estado.get("tipo_original", ""),
        "texto": estado["texto"],
    }


def _campos_analisis(resultado) -> dict:
    if isinstance(resultado, dict):
        analisis = AnalisisMensaje.model_validate(resultado)
    else:
        analisis = AnalisisMensaje.model_validate(resultado.model_dump())

    return analisis.model_dump()


def _error_analisis(
    prefijo: str,
    error: Exception,
    identificador: str | None = None,
) -> dict:
    fallo = {
        "etapa": prefijo,
        "tipo_error": type(error).__name__,
        "mensaje": str(error),
    }
    if identificador is not None:
        fallo["id"] = identificador

    return {
        "errores": [f"{prefijo}: {type(error).__name__}: {error}"],
        "fallos": [fallo],
    }


def _analizar_individualmente(estado: EstadoAgente) -> dict:
    try:
        return _campos_analisis(
            cadena_analisis.invoke(_entrada_analisis(estado))
        )
    except Exception as error:
        return _error_analisis(
            "analizar_mensaje",
            error,
            estado.get("id"),
        )


def analizar_mensaje(estado: EstadoAgente) -> dict:
    """
    Analiza una interacción utilizando la cadena de LangChain.

    Recibe el estado actual y devuelve únicamente
    los nuevos campos generados por la IA.

    Si ocurre un error, lo registra en EstadoAgente
    para que LangGraph pueda finalizar el flujo
    de forma controlada.
    """

    try:
        return _analizar_individualmente(estado)

    except Exception as error:
        errores = list(estado.get("errores", []))
        fallos = list(estado.get("fallos", []))

        errores.append(
            f"analizar_mensaje: "
            f"{type(error).__name__}: {error}"
        )
        fallo = {
            "etapa": "analizar_mensaje",
            "tipo_error": type(error).__name__,
            "mensaje": str(error),
        }
        if estado.get("id") is not None:
            fallo["id"] = estado["id"]
        fallos.append(fallo)

        return {
            "errores": errores,
            "fallos": fallos,
        }


def analizar_lote(estados: list[EstadoAgente]) -> list[dict]:
    """Analiza un grupo y asocia cada resultado mediante el ID estable."""
    ids = [estado.get("id") for estado in estados]
    if any(
        not isinstance(identificador, str) or not identificador.strip()
        for identificador in ids
    ):
        raise ValueError("El análisis por lotes requiere IDs no vacíos")
    if len(set(ids)) != len(ids):
        raise ValueError("El análisis por lotes requiere IDs únicos")
    if not estados:
        return []

    mensajes = []
    for estado in estados:
        mensajes.append(
            {
                "id": estado["id"],
                **_entrada_analisis(estado),
            }
        )

    try:
        respuesta = cadena_analisis_lote.invoke(
            {
                "mensajes_json": json.dumps(
                    mensajes,
                    ensure_ascii=False,
                )
            }
        )
        if isinstance(respuesta, dict):
            respuesta = AnalisisLote.model_validate(respuesta)
        else:
            respuesta = AnalisisLote.model_validate(
                respuesta.model_dump()
            )
    except Exception as error:
        return [
            _error_analisis("analizar_lote", error, estado["id"])
            for estado in estados
        ]

    estados_por_id = {
        estado["id"]: estado
        for estado in estados
    }
    resultados_por_id = {}
    ids_duplicados = set()

    for resultado in respuesta.resultados:
        identificador = resultado.id
        if identificador not in estados_por_id:
            continue
        if identificador in resultados_por_id:
            resultados_por_id.pop(identificador)
            ids_duplicados.add(identificador)
            continue
        if identificador not in ids_duplicados:
            resultados_por_id[identificador] = _campos_analisis(resultado)

    resultados = []
    for estado in estados:
        identificador = estado["id"]
        resultado = resultados_por_id.get(identificador)
        if resultado is None:
            resultado = _analizar_individualmente(estado)
        resultados.append(resultado)

    return resultados