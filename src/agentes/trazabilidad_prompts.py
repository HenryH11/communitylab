"""Genera huellas estables para las plantillas de análisis y generación."""

import hashlib
import json

from src.agentes.cadenas import template_analisis, template_analisis_lote
from src.agentes.nodos.nodos_generadores import (
    _prompt_boletin,
    _prompt_caso_exito,
    _prompt_insight_mejora,
    _prompt_linkedin,
    _prompt_preguntas_frecuentes,
)


PLANTILLAS = {
    "analisis_individual": template_analisis,
    "analisis_lote": template_analisis_lote,
    "boletin": _prompt_boletin,
    "caso_exito": _prompt_caso_exito,
    "insight_mejora": _prompt_insight_mejora,
    "linkedin": _prompt_linkedin,
    "preguntas_frecuentes": _prompt_preguntas_frecuentes,
}


def _serializar_plantilla(plantilla) -> str:
    mensajes = []
    for mensaje in plantilla.messages:
        prompt = getattr(mensaje, "prompt", None)
        texto = getattr(prompt, "template", None)
        if not isinstance(texto, str):
            raise TypeError(
                f"No se puede calcular la huella de {type(mensaje).__name__}"
            )
        mensajes.append(
            {
                "tipo": type(mensaje).__name__,
                "rol": getattr(mensaje, "role", None),
                "formato": getattr(prompt, "template_format", None),
                "variables": sorted(getattr(prompt, "input_variables", [])),
                "texto": texto,
            }
        )
    return json.dumps(
        mensajes,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def calcular_hash_prompt(plantilla) -> str:
    """Calcula SHA-256 sobre roles, formatos, variables y texto de la plantilla."""
    contenido = _serializar_plantilla(plantilla).encode("utf-8")
    return hashlib.sha256(contenido).hexdigest()


def obtener_huellas_prompts() -> dict:
    """Devuelve huellas por tarea y una huella conjunta, sin valores de ejecución."""
    por_tarea = {
        nombre: calcular_hash_prompt(plantilla)
        for nombre, plantilla in sorted(PLANTILLAS.items())
    }
    contenido = json.dumps(
        por_tarea,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return {
        "algoritmo": "sha256",
        "hash_global": hashlib.sha256(contenido).hexdigest(),
        "por_tarea": por_tarea,
    }