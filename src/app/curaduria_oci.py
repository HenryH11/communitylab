"""Adaptador entre la revisión humana de Streamlit y el guardado de Cloud."""

from copy import deepcopy
from uuid import uuid4

from src.agentes.modelos import (
    CasoDeExito,
    DestaqueBoletin,
    InsightMejora,
    PublicacionLinkedIn,
    SugerenciaPreguntasFrecuentes,
)
from src.app.guardado import guardar_resultado_aprobado


MODELOS_ACTIVO = {
    "linkedin": PublicacionLinkedIn,
    "boletin": DestaqueBoletin,
    "caso_exito": CasoDeExito,
    "preguntas_frecuentes": SugerenciaPreguntasFrecuentes,
    "insight_mejora": InsightMejora,
}


def contexto_curaduria(sesion, resultado):
    """Cada resultado nuevo tiene editores, aprobaciones y recibos propios."""
    contexto = sesion.get("_curaduria_oci")
    if contexto is None or contexto["resultado"] is not resultado:
        contexto = {
            "resultado": resultado,
            "lote": uuid4().hex,
            "aprobados": {},
            "guardados": {},
            "informe": None,
        }
        sesion["_curaduria_oci"] = contexto
    return contexto


def validar_activo_curado(tipo, contenido):
    """Valida sin normalizar silenciosamente el texto que se aprobó."""
    if tipo not in MODELOS_ACTIVO or not isinstance(contenido, dict):
        raise ValueError("Tipo o contenido de activo no válido")
    for valor in contenido.values():
        if isinstance(valor, str) and not valor.strip():
            raise ValueError("Completa los campos de texto antes de aprobar")
        if isinstance(valor, list) and any(
            not isinstance(item, str) or not item.strip() for item in valor
        ):
            raise ValueError("Las listas deben contener textos no vacíos")
    modelo = MODELOS_ACTIVO[tipo].model_validate(contenido, strict=True)
    if modelo.model_dump() != contenido:
        raise ValueError(
            "Revisa el formato del activo antes de aprobar; "
            "los hashtags deben comenzar con #"
        )


async def guardar_curaduria(resultado, ediciones, *, periodo, bucket):
    """Sustituye solo los activos seleccionados en una copia de la salida DS."""
    salida = deepcopy(resultado)
    disponibles = {
        (item["id"], tipo): item
        for item in salida["resultados"]
        for tipo in item.get("activos_generados", {})
    }
    if not set(ediciones).issubset(disponibles):
        raise ValueError("La aprobación no corresponde al resultado actual")
    for clave, contenido in ediciones.items():
        validar_activo_curado(clave[1], contenido)
        disponibles[clave]["activos_generados"][clave[1]] = deepcopy(contenido)
    return await guardar_resultado_aprobado(
        salida, aprobados=set(ediciones), periodo=periodo, bucket=bucket
    )
