"""Cadenas de análisis con Gemini; las plantillas viven en src/agentes/prompts."""

from functools import lru_cache
from typing import cast

from langchain_core.runnables import RunnableConfig, RunnableLambda

from src.agentes.modelo_ia import obtener_modelo_gemini
from src.agentes.modelos import AnalisisLote, AnalisisMensaje
from src.agentes.prompts.analisis import template_analisis, template_analisis_lote


@lru_cache(maxsize=1)
def _obtener_cadena_analisis():
    modelo = obtener_modelo_gemini().with_structured_output(AnalisisMensaje)
    return template_analisis | modelo


@lru_cache(maxsize=1)
def _obtener_cadena_analisis_lote():
    modelo = obtener_modelo_gemini().with_structured_output(AnalisisLote)
    return template_analisis_lote | modelo


def _invocar_analisis(entrada: dict, config: RunnableConfig) -> AnalisisMensaje:
    return cast(
        AnalisisMensaje,
        _obtener_cadena_analisis().invoke(entrada, config=config),
    )


def _invocar_analisis_lote(entrada: dict, config: RunnableConfig) -> AnalisisLote:
    return cast(
        AnalisisLote,
        _obtener_cadena_analisis_lote().invoke(entrada, config=config),
    )


cadena_analisis = RunnableLambda(_invocar_analisis)
cadena_analisis_lote = RunnableLambda(_invocar_analisis_lote)
