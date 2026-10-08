"""Cadenas de análisis independientes del proveedor de IA."""

from functools import lru_cache
from typing import cast


from langchain_core.runnables import (RunnableConfig,RunnableLambda,)

from src.agentes.configuracion_ia import (obtener_proveedor_analisis,obtener_proveedor_analisis,)

from src.agentes.modelo_ia import (obtener_modelo_analisis_estructurado,)

from src.agentes.modelos import (AnalisisLote,AnalisisMensaje,)

from src.agentes.prompts.analisis import (template_analisis,template_analisis_lote,)


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


def _invocar_analisis(
    entrada: dict,
    config: RunnableConfig,
) -> AnalisisMensaje:
    proveedor = obtener_proveedor_analisis()

    return cast(
        AnalisisMensaje,
        _obtener_cadena_analisis(
            proveedor
        ).invoke(
            entrada,
            config=config,
        ),
    )


def _invocar_analisis_lote(
    entrada: dict,
    config: RunnableConfig,
) -> AnalisisLote:
    proveedor = obtener_proveedor_analisis()

    return cast(
        AnalisisLote,
        _obtener_cadena_analisis_lote(
            proveedor
        ).invoke(
            entrada,
            config=config,
        ),
    )


cadena_analisis = RunnableLambda(
    _invocar_analisis
)

cadena_analisis_lote = RunnableLambda(
    _invocar_analisis_lote
)