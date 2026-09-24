from src.agents.state import AgentState


UMBRAL_RELEVANCIA = 40


def determinar_rutas(state: AgentState) -> dict:
    """
    Determina qué activos puede generar una interacción
    a partir del análisis semántico y del score de relevancia.

    Puede devolver varias rutas para un mismo mensaje.
    """

    rutas = []

    score = state.get("score_relevancia")

    # Si conocemos el score y no alcanza el umbral,
    # el mensaje no genera activos.
    if score is not None and score < UMBRAL_RELEVANCIA:
        return {"rutas": []}

    tipo = state.get("tipo_detectado")
    sentimiento = state.get("sentimiento")

    # Una pregunta técnica relevante puede alimentar el FAQ.
    if tipo == "pregunta_tecnica":
        rutas.append("faq")

    # Un testimonio puede servir para más de un activo.
    if tipo == "testimonio":
        rutas.append("caso_exito")

        if sentimiento in {"positivo", "muy_positivo"}:
            rutas.append("linkedin")

    return {
        "rutas": rutas
    }