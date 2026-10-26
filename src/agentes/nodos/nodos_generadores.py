"""Generación de activos por ruta; prompts en src/agentes/prompts y salidas en modelos.py."""

from functools import lru_cache
from typing import cast

from pydantic import BaseModel

from src.agentes.estado_agente import EstadoAgente

from src.agentes.configuracion_ia import (
    PROVEEDOR_GEMINI,
    PROVEEDOR_NVIDIA_NIM,
    obtener_proveedor_generacion,
    obtener_tier_por_ruta,
)
from src.agentes.modelo_ia import (
    invocar_modelo_con_fallback,
    obtener_modelo_generacion_estructurado,
)
from src.agentes.observabilidad import (
    config_ejecucion,
    contexto_llamada_ia,
    registrar_evento,
)

from src.agentes.modelos import (
    CasoDeExito,
    DestaqueBoletin,
    InsightMejoraIA,
    PublicacionLinkedInIA,
    SugerenciaPreguntasFrecuentes,
)
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


@lru_cache(maxsize=8)
def _obtener_generadores(
    proveedor: str,
):
    return {
        "linkedin": (
            prompt_linkedin
            | obtener_modelo_generacion_estructurado(
                PublicacionLinkedInIA,
                proveedor=proveedor,
                ruta="linkedin",
            )
        ),
        "boletin": (
            prompt_boletin
            | obtener_modelo_generacion_estructurado(
                DestaqueBoletin,
                proveedor=proveedor,
                ruta="boletin",
            )
        ),
        "preguntas_frecuentes": (
            prompt_preguntas_frecuentes
            | obtener_modelo_generacion_estructurado(
                SugerenciaPreguntasFrecuentes,
                proveedor=proveedor,
                ruta="preguntas_frecuentes",
            )
        ),
        "caso_exito": (
            prompt_caso_exito
            | obtener_modelo_generacion_estructurado(
                CasoDeExito,
                proveedor=proveedor,
                ruta="caso_exito",
            )
        ),
        "insight_mejora": (
            prompt_insight_mejora
            | obtener_modelo_generacion_estructurado(
                InsightMejoraIA,
                proveedor=proveedor,
                ruta="insight_mejora",
            )
        ),
    }


def _registrar_traza_generacion(
    traza: dict,
    *,
    identificador: str | None,
    ruta: str,
) -> None:
    """Registra qué proveedor resolvió una ruta de generación."""
    registrar_evento(
        "proveedor_ia_resuelto",
        etapa="generar_activos",
        id_interaccion=identificador,
        ruta=ruta,
        tier=obtener_tier_por_ruta(ruta),
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
    )


def _invocar_generador_con_fallback(
    *,
    ruta: str,
    contexto: dict,
    identificador: str | None,
) -> BaseModel:
    """Genera una ruta con NVIDIA y usa Gemini como respaldo."""

    generador_nvidia = _obtener_generadores(
        PROVEEDOR_NVIDIA_NIM
    )[ruta]

    generador_gemini = _obtener_generadores(
        PROVEEDOR_GEMINI
    )[ruta]

    config = config_ejecucion(
        "generar_activos",
        intento=1,
        id_interaccion=identificador,
        ruta=ruta,
    )

    def primario(entrada):
        return generador_nvidia.invoke(
            entrada,
            config=config,
        )

    primario.__name__ = PROVEEDOR_NVIDIA_NIM

    def respaldo(entrada):
        return generador_gemini.invoke(
            entrada,
            config=config,
        )

    respaldo.__name__ = PROVEEDOR_GEMINI

    with contexto_llamada_ia(
        id_interaccion=identificador,
        ruta=ruta,
    ):
        salida = invocar_modelo_con_fallback(
            contexto,
            primario=primario,
            respaldo=respaldo,
        )
    _registrar_traza_generacion(
        salida["traza"],
        identificador=identificador,
        ruta=ruta,
    )

    return cast(
        BaseModel,
        salida["resultado"],
    )


def _contexto(estado: EstadoAgente) -> dict:
    from src.datos.metadatos import valor_publico

    return {
        "autor": valor_publico(estado.get("autor")),
        "texto": estado["texto"],
        "tema_principal": valor_publico(estado.get("tema_principal")),
        "subtema": valor_publico(estado.get("subtema")),
        "tipo_detectado": valor_publico(estado.get("tipo_detectado")),
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

    try:
        contexto = _contexto(state)
    except Exception as error:
        for ruta in rutas:
            errores.append(
                describir_error("generar_activos", error, ruta)
            )
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

    try:
        proveedor = obtener_proveedor_generacion()

        generadores = _obtener_generadores(proveedor)
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

        def invocar(
            intento: int,
            cadena=cadena,
            ruta=ruta,
        ) -> BaseModel:
            if proveedor == PROVEEDOR_NVIDIA_NIM:
                return _invocar_generador_con_fallback(
                    ruta=ruta,
                    contexto=contexto,
                    identificador=identificador,
                )

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
                max_intentos=(
                    1
                    if proveedor == PROVEEDOR_NVIDIA_NIM
                    else None
                ),
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
