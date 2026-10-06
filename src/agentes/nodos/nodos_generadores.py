"""Generación de activos por ruta; prompts en src/agentes/prompts y salidas en modelos.py."""

from functools import lru_cache
from typing import cast

from pydantic import BaseModel

from src.agentes.estado_agente import EstadoAgente
from src.agentes.modelo_ia import obtener_modelo_gemini
from src.agentes.modelos import (
    CasoDeExito,
    DestaqueBoletin,
    InsightMejora,
    PublicacionLinkedIn,
    SugerenciaPreguntasFrecuentes,
)
from src.agentes.observabilidad import config_ejecucion
from src.agentes.prompts.boletin import prompt_boletin
from src.agentes.prompts.caso_exito import prompt_caso_exito
from src.agentes.prompts.insight_mejora import prompt_insight_mejora
from src.agentes.prompts.linkedin import prompt_linkedin
from src.agentes.prompts.preguntas_frecuentes import prompt_preguntas_frecuentes
from src.agentes.reintentos import (
    construir_fallo,
    describir_error,
    ejecutar_con_reintentos,
)


@lru_cache(maxsize=1)
def _obtener_generadores():
    modelo = obtener_modelo_gemini()

    return {
        "linkedin": (
            prompt_linkedin
            | modelo.with_structured_output(PublicacionLinkedIn)
        ),
        # La clave técnica "boletin" se conserva por compatibilidad,
        # aunque el activo generado funciona como Community Highlight.
        "boletin": (
            prompt_boletin
            | modelo.with_structured_output(DestaqueBoletin)
        ),
        "preguntas_frecuentes": (
            prompt_preguntas_frecuentes
            | modelo.with_structured_output(SugerenciaPreguntasFrecuentes)
        ),
        "caso_exito": (
            prompt_caso_exito
            | modelo.with_structured_output(CasoDeExito)
        ),
        "insight_mejora": (
            prompt_insight_mejora
            | modelo.with_structured_output(InsightMejora)
        ),
    }


def _contexto(estado: EstadoAgente) -> dict:
    return {
        "autor": estado.get("autor") or "Anónimo",
        "texto": estado["texto"],
        "tema_principal": estado.get("tema_principal") or "",
        "subtema": estado.get("subtema") or "",
        "tipo_detectado": estado.get("tipo_detectado") or "",
    }


def generar_activos(state: EstadoAgente) -> dict:
    """
    Genera contenido para cada ruta seleccionada por LangGraph.

    Si una ruta falla, las demás continúan de forma independiente.
    """

    activos = {}
    errores = list(state.get("errores", []))
    fallos = list(state.get("fallos", []))
    rutas = state.get("rutas", [])
    identificador = state.get("id")

    if not rutas:
        return {
            "activos_generados": activos,
            "errores": errores,
            "fallos": fallos,
        }

    contexto = _contexto(state)
    try:
        generadores = _obtener_generadores()
    except Exception as error:
        for ruta in rutas:
            errores.append(
                describir_error("inicializar_generadores", error, ruta)
            )
            fallos.append(
                construir_fallo(
                    "inicializar_generadores",
                    error,
                    id_interaccion=identificador,
                    ruta=ruta,
                )
            )
        return {
            "activos_generados": activos,
            "errores": errores,
            "fallos": fallos,
        }

    for ruta in rutas:
        cadena = generadores.get(ruta)

        if cadena is None:
            errores.append(
                f"generar_activos[{ruta}]: generador no configurado"
            )
            fallo = {
                "etapa": "generar_activos",
                "ruta": ruta,
                "tipo_error": "GeneradorNoConfigurado",
                "mensaje": "generador no configurado",
                "intentos": 0,
                "reintentable": False,
            }
            if identificador is not None:
                fallo["id"] = identificador
            fallos.append(fallo)
            continue

        def invocar(intento: int, cadena=cadena, ruta=ruta) -> BaseModel:
            return cast(
                BaseModel,
                cadena.invoke(
                    contexto,
                    config=config_ejecucion(
                        "generar_activos",
                        intento=intento,
                        id_interaccion=identificador,
                        ruta=ruta,
                    ),
                ),
            )

        try:
            resultado = ejecutar_con_reintentos(
                invocar,
                contexto={
                    "etapa": "generar_activos",
                    "id_interaccion": identificador,
                    "ruta": ruta,
                },
            )
            activo = resultado.model_dump()

            if ruta == "insight_mejora":
                activo["area"] = state.get("tema_principal") or "otros"

            if ruta == "linkedin":
                activo["canal_recomendado"] = "LinkedIn Oficial"

            activos[ruta] = activo

        except Exception as error:
            errores.append(describir_error("generar_activos", error, ruta))
            fallos.append(
                construir_fallo(
                    "generar_activos",
                    error,
                    id_interaccion=identificador,
                    ruta=ruta,
                )
            )

    return {
        "activos_generados": activos,
        "errores": errores,
        "fallos": fallos,
    }
