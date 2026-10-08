from functools import lru_cache
from typing import cast

from langchain_core.runnables import RunnableConfig, RunnableLambda

from src.agentes.configuracion_ia import (
    PROVEEDOR_GEMINI,
    PROVEEDOR_NVIDIA_NIM,
    obtener_proveedor_analisis,
)
from src.agentes.modelo_ia import (
    invocar_modelo_con_fallback,
    obtener_modelo_analisis_estructurado,
)
from src.agentes.modelos import (
    AnalisisLote,
    AnalisisMensaje,
)
from src.agentes.observabilidad import registrar_evento
from src.agentes.prompts.analisis import (
    template_analisis,
    template_analisis_lote,
)


@lru_cache(maxsize=2)
def _obtener_cadena_analisis(
    proveedor: str,
):
    modelo = obtener_modelo_analisis_estructurado(
        AnalisisMensaje,
        proveedor=proveedor,
    )
    return template_analisis | modelo


@lru_cache(maxsize=2)
def _obtener_cadena_analisis_lote(
    proveedor: str,
):
    modelo = obtener_modelo_analisis_estructurado(
        AnalisisLote,
        proveedor=proveedor,
    )
    return template_analisis_lote | modelo


def _registrar_traza_proveedor(
    traza: dict,
    config: RunnableConfig,
) -> None:
    """Asocia la decisión de proveedor a la interacción en observabilidad."""
    metadata = config.get("metadata", {}) or {}

    contexto = {
        campo: metadata[campo]
        for campo in (
            "etapa",
            "intento",
            "id_interaccion",
            "ids_interaccion",
            "ruta",
        )
        if metadata.get(campo) is not None
    }

    registrar_evento(
        "proveedor_ia_resuelto",
        proveedor_primario=traza.get(
            "proveedor_primario"
        ),
        proveedor_usado=traza.get(
            "proveedor_usado"
        ),
        fallback_activado=traza.get(
            "fallback_activado",
            False,
        ),
        motivo_fallback=traza.get(
            "motivo_fallback"
        ),
        **contexto,
    )


def _invocar_con_fallback(
    entrada: dict,
    config: RunnableConfig,
    *,
    obtener_cadena,
):
    """Ejecuta NVIDIA como primario y Gemini como respaldo."""

    def primario(valor):
        return obtener_cadena(
            PROVEEDOR_NVIDIA_NIM
        ).invoke(
            valor,
            config=config,
        )

    primario.__name__ = PROVEEDOR_NVIDIA_NIM

    def respaldo(valor):
        return obtener_cadena(
            PROVEEDOR_GEMINI
        ).invoke(
            valor,
            config=config,
        )

    respaldo.__name__ = PROVEEDOR_GEMINI

    salida = invocar_modelo_con_fallback(
        entrada,
        primario=primario,
        respaldo=respaldo,
    )

    _registrar_traza_proveedor(
        salida["traza"],
        config,
    )

    return salida["resultado"]


def _invocar_analisis(
    entrada: dict,
    config: RunnableConfig,
) -> AnalisisMensaje:
    proveedor = obtener_proveedor_analisis()

    if proveedor == PROVEEDOR_NVIDIA_NIM:
        resultado = _invocar_con_fallback(
            entrada,
            config,
            obtener_cadena=_obtener_cadena_analisis,
        )
    else:
        resultado = _obtener_cadena_analisis(
            proveedor
        ).invoke(
            entrada,
            config=config,
        )

    return cast(
        AnalisisMensaje,
        resultado,
    )


def _invocar_analisis_lote(
    entrada: dict,
    config: RunnableConfig,
) -> AnalisisLote:
    proveedor = obtener_proveedor_analisis()

    if proveedor == PROVEEDOR_NVIDIA_NIM:
        resultado = _invocar_con_fallback(
            entrada,
            config,
            obtener_cadena=_obtener_cadena_analisis_lote,
        )
    else:
        resultado = _obtener_cadena_analisis_lote(
            proveedor
        ).invoke(
            entrada,
            config=config,
        )

    return cast(
        AnalisisLote,
        resultado,
    )


cadena_analisis = RunnableLambda(
    _invocar_analisis
)

cadena_analisis_lote = RunnableLambda(
    _invocar_analisis_lote
)