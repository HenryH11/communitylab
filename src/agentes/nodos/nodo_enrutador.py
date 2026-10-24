from typing import TypedDict

from src.agentes.configuracion_ia import (
    TIER_RAPIDO,
    TIER_RAZONAMIENTO,
    obtener_tier_por_ruta,
)
from src.agentes.estado_agente import EstadoAgente, Ruta


UMBRAL_RELEVANCIA = 40


class ResultadoRutas(TypedDict):
    rutas: list[Ruta]
    tier_modelo: str


def clasificar_tier_rutas(rutas: list[Ruta]) -> str:
    """Determina el tier de mayor exigencia entre las rutas seleccionadas."""
    if any(obtener_tier_por_ruta(r) == TIER_RAZONAMIENTO for r in rutas):
        return TIER_RAZONAMIENTO
    if any(obtener_tier_por_ruta(r) == TIER_RAPIDO for r in rutas):
        return TIER_RAPIDO
    return TIER_RAPIDO


def determinar_rutas(state: EstadoAgente) -> ResultadoRutas:
    """
    Determina qué activos puede generar una interacción
    a partir del análisis semántico y de las decisiones
    de elegibilidad recibidas desde Data.

    Puede devolver varias rutas para un mismo mensaje.
    """
    # DS bloquea la transformación de spam antes de evaluar
    # las rutas o elegibilidades provenientes de Data.
    if state.get("es_spam_detectado") is True:
        return {
            "rutas": [],
            "tier_modelo": TIER_RAPIDO,
        }

    rutas: list[Ruta] = []

    tipo = state.get("tipo_detectado")
    sentimiento = state.get("sentimiento")

    elegible_contenido = state.get("elegible_contenido")
    elegible_faq = state.get("elegible_faq", False)
    puntaje = state.get("score_relevancia")

    # Las preguntas del programa utilizan una elegibilidad específica
    # definida por Data. No dependen de la ruta general de contenido.
    if tipo == "pregunta_programa":
        if elegible_faq:
            rutas.append("preguntas_frecuentes")

        return {
            "rutas": rutas,
            "tier_modelo": clasificar_tier_rutas(rutas),
        }

    # Para el resto de activos se mantiene elegible_contenido.
    if elegible_contenido is False:
        return {
            "rutas": [],
            "tier_modelo": TIER_RAPIDO,
        }

    # Estados antiguos sin la decisión por ID conservan
    # el umbral de respaldo.
    if (
        elegible_contenido is None
        and isinstance(puntaje, (int, float))
        and not isinstance(puntaje, bool)
        and puntaje < UMBRAL_RELEVANCIA
    ):
        return {
            "rutas": [],
            "tier_modelo": TIER_RAPIDO,
        }

    # Una pregunta técnica relevante puede alimentar
    # las preguntas frecuentes.
    if tipo == "pregunta_tecnica":
        rutas.append("preguntas_frecuentes")

    # El feedback relevante se transforma en un insight accionable.
    if tipo == "feedback":
        rutas.append("insight_mejora")

    # Un testimonio puede servir para más de un activo.
    if tipo == "testimonio":
        rutas.append("caso_exito")
        rutas.append("boletin")

        if (
            isinstance(sentimiento, str)
            and sentimiento in {"positivo", "muy_positivo"}
        ):
            rutas.append("linkedin")

    return {
        "rutas": rutas,
        "tier_modelo": clasificar_tier_rutas(rutas),
    }
