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
from src.datos.limpieza import detectar_mojibake, reparar_mojibake
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


def reparar_activo_curado(contenido: dict) -> dict:
    """Repara secuencias de mojibake conservando los saltos de línea."""
    reparado = {}
    for clave, valor in contenido.items():
        if isinstance(valor, str):
            reparado[clave] = reparar_mojibake(valor)
        elif isinstance(valor, list):
            reparado[clave] = [
                reparar_mojibake(item) if isinstance(item, str) else item
                for item in valor
            ]
        else:
            reparado[clave] = valor
    return reparado


def validar_activo_curado(tipo: str, contenido: dict) -> None:
    """Valida sin normalizar silenciosamente el texto que se aprobó."""
    if tipo not in MODELOS_ACTIVO or not isinstance(contenido, dict):
        raise ValueError("Tipo o contenido de activo no válido")
    for valor in contenido.values():
        if isinstance(valor, str):
            if not valor.strip():
                raise ValueError("Completa los campos de texto antes de aprobar")
            if detectar_mojibake(valor):
                sugerencia = reparar_mojibake(valor)
                raise ValueError(
                    f"El texto contiene caracteres mal codificados: {valor!r}; "
                    f"Se sugiere reemplazar por: {sugerencia!r}"
                )
        if isinstance(valor, list):
            if any(
                not isinstance(item, str) or not item.strip() for item in valor
            ):
                raise ValueError("Las listas deben contener textos no vacíos")
            if any(
                detectar_mojibake(item) for item in valor
            ):
                raise ValueError(
                    "Las listas contienen caracteres mal codificados; "
                    "Revisa cada elemento antes de aprobar"
                )
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