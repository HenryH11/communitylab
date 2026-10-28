"""Plan semántico de una petición antes de consultar los datos de la sesión."""

from datetime import date
from functools import lru_cache
import json
from typing import Literal

from langchain_core.exceptions import OutputParserException
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from src.agentes.configuracion_ia import (
    PROVEEDOR_GEMINI,
    PROVEEDOR_NVIDIA_NIM,
    obtener_modelo_nvidia_interpretacion,
    obtener_proveedor_generacion,
)
from src.agentes.modelo_ia import (
    invocar_modelo_con_fallback,
    obtener_modelo_generacion_estructurado,
)
from src.agentes.observabilidad import config_ejecucion
from src.agentes.contexto import obtener_presupuesto_contexto
from src.agentes.plataformas import PlataformaPublicacion
from src.agentes.prompts.interpretacion import prompt_interpretacion


class ErrorInterpretacion(RuntimeError):
    """La respuesta del intérprete no cumple el contrato de búsqueda."""


class PlanConsulta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intencion: Literal[
        "consulta", "borrador", "conversacion", "aclaracion", "fuera_de_alcance"
    ]
    terminos: list[str] = Field(
        default_factory=list, max_length=12,
        description="Solo temas de búsqueda. Sin saludos, instrucciones ni filtros.",
    )
    sentimiento: Literal[
        "positivo", "muy_positivo", "neutral", "negativo", "muy_negativo"
    ] | None = Field(
        default=None,
        description=(
            "positivo incluye muy_positivo. Top o mejores usa positivo, no "
            "muy_positivo, salvo que el usuario pida explícitamente muy positivos."
        ),
    )
    tipo_detectado: str | None = Field(default=None, max_length=250)
    tipos_detectados: list[str] = Field(
        default_factory=list, max_length=32,
        description=(
            "Alternativas de tipo (OR). Para preguntas frecuentes, todos los tipos "
            "de pregunta del vocabulario; no filtrar sentimiento ni buscar 'frecuentes'. "
            "No combinar con tipo_detectado."
        ),
    )
    agrupar_preguntas: bool = Field(
        default=False,
        description="True para identificar o resumir preguntas frecuentes y agrupar dudas por sus fuentes.",
    )
    listar_autores: bool = Field(
        default=False,
        description="True para listar nombres de autores presentes en los datos, sin redactar mensajes.",
    )
    campos_listado: list[Literal[
        "id", "autor", "canal", "sentimiento", "tema", "tipo", "fecha", "contenido_textual",
    ]] = Field(
        default_factory=list,
        description="Campos de la base solicitados como listado literal, sin análisis ni redacción.",
    )
    canal: str | None = Field(default=None, max_length=250)
    fecha_desde: date | None = None
    fecha_hasta: date | None = None
    plataforma: PlataformaPublicacion | None = None
    nueva_version: bool = Field(
        default=False,
        description=(
            "True si pide otro enfoque o acepta una oferta de otro enfoque del "
            "último borrador (por ejemplo, 'dale'). False si solo cambia tono, "
            "longitud o plataforma; 'más cercano' por sí solo es cambio de tono."
        ),
    )
    cantidad: int | None = Field(default=None, ge=1, strict=True)
    respuesta: str = Field(default="", max_length=1_200)

    @model_validator(mode="after")
    def validar_plan(self) -> "PlanConsulta":
        if self.nueva_version and self.intencion != "borrador":
            raise ValueError("Una nueva versión requiere una petición de borrador.")
        if self.agrupar_preguntas and self.intencion != "consulta":
            raise ValueError("Agrupar preguntas requiere una consulta, no un borrador.")
        if self.listar_autores and (self.intencion != "consulta" or self.agrupar_preguntas):
            raise ValueError("Listar autores requiere una consulta sin agrupación de preguntas.")
        if self.campos_listado and (
            self.intencion != "consulta" or self.agrupar_preguntas or self.listar_autores
        ):
            raise ValueError("Listar campos requiere una consulta sin agrupación ni listar_autores.")
        self.campos_listado = list(dict.fromkeys(self.campos_listado))
        if self.tipo_detectado and self.tipos_detectados:
            raise ValueError("Usa tipo_detectado o tipos_detectados, no ambos.")
        self.tipos_detectados = list(dict.fromkeys(t.strip() for t in self.tipos_detectados))
        if any(not t or len(t) > 250 for t in self.tipos_detectados):
            raise ValueError("Cada tipo debe tener entre 1 y 250 caracteres.")
        self.terminos = [termino.strip() for termino in self.terminos]
        if any(not termino or len(termino) > 120 for termino in self.terminos):
            raise ValueError("Los términos deben tener entre 1 y 120 caracteres.")
        if self.fecha_desde and self.fecha_hasta and self.fecha_desde > self.fecha_hasta:
            raise ValueError("El inicio del período no puede ser posterior al final.")
        if self.intencion == "borrador" and self.plataforma is None:
            raise ValueError("Un borrador requiere una plataforma.")
        if self.intencion not in {"consulta", "borrador"}:
            if not self.respuesta.strip():
                raise ValueError("Una interacción sin búsqueda requiere una respuesta.")
            if self.terminos or self.tipos_detectados or self.agrupar_preguntas or any(
                valor is not None
                for valor in (
                    self.sentimiento, self.tipo_detectado, self.canal,
                    self.fecha_desde, self.fecha_hasta, self.plataforma, self.cantidad,
                )
            ):
                raise ValueError("Una interacción sin búsqueda no puede incluir filtros.")
        return self


@lru_cache(maxsize=8)
def _obtener_cadena_interpretacion(proveedor: str, max_tokens: int = 4096):
    modelo = obtener_modelo_generacion_estructurado(
        PlanConsulta,
        proveedor=proveedor,
        ruta="conversacion",
        temperatura=0.0,
        max_tokens=max_tokens,
        modelo=(
            obtener_modelo_nvidia_interpretacion()
            if proveedor == PROVEEDOR_NVIDIA_NIM else None
        ),
    )
    return prompt_interpretacion | modelo


def interpretar_consulta(
    *,
    consulta: str,
    hoy: date,
    historial: list[dict[str, str]],
    consulta_anterior: dict | None,
    vocabulario: dict[str, list[str]],
) -> PlanConsulta:
    entrada = {
        "consulta": consulta,
        "hoy": hoy.isoformat(),
        "historial": json.dumps(historial, ensure_ascii=False),
        "consulta_anterior": json.dumps(consulta_anterior, ensure_ascii=False),
        "vocabulario": json.dumps(vocabulario, ensure_ascii=False),
        "revision": "",
    }
    proveedor = obtener_proveedor_generacion()
    max_tokens = obtener_presupuesto_contexto().salida
    config = config_ejecucion("interpretar_consulta", intento=1, ruta="conversacion")
    try:
        for intento in range(2):
            if proveedor == PROVEEDOR_NVIDIA_NIM:
                def primario(valor):
                    return _obtener_cadena_interpretacion(PROVEEDOR_NVIDIA_NIM, max_tokens=max_tokens).invoke(
                        valor, config=config
                    )

                def respaldo(valor):
                    return _obtener_cadena_interpretacion(PROVEEDOR_GEMINI, max_tokens=max_tokens).invoke(
                        valor, config=config
                    )

                primario.__name__ = PROVEEDOR_NVIDIA_NIM
                respaldo.__name__ = PROVEEDOR_GEMINI
                resultado = invocar_modelo_con_fallback(
                    entrada, primario=primario, respaldo=respaldo
                )["resultado"]
            else:
                resultado = _obtener_cadena_interpretacion(proveedor, max_tokens=max_tokens).invoke(
                    entrada, config=config
                )
            plan = PlanConsulta.model_validate(resultado)
            anteriores = {
                " ".join(turno["contenido"].casefold().split())
                for turno in historial if turno["rol"] == "asistente"
            }
            if (
                plan.intencion != "aclaracion"
                or " ".join(plan.respuesta.casefold().split()) not in anteriores
            ):
                return plan
            if intento == 0:
                entrada = {
                    **entrada,
                    "revision": (
                        "La aclaración propuesta repite una respuesta anterior. "
                        "Revisa si el historial permite continuar la tarea. Si falta "
                        "un referente, explica cómo aportarlo sin repetir la pregunta "
                        "ni inventar una intención."
                    ),
                }
        raise ErrorInterpretacion(
            "No pude resolver la ambigüedad sin repetir la misma aclaración. "
            "Incluye el texto o el tema al que te refieres."
        )
    except (ValidationError, OutputParserException) as error:
        raise ErrorInterpretacion(
            "No pude interpretar la solicitud de forma fiable. Intenta reformularla."
        ) from error
