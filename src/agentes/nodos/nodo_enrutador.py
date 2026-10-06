from src.agentes.estado_agente import EstadoAgente


UMBRAL_RELEVANCIA = 40


def determinar_rutas(state: EstadoAgente) -> dict:
    """
    Determina qué activos puede generar una interacción
    a partir del análisis semántico y de las decisiones
    de elegibilidad recibidas desde Data.

    Puede devolver varias rutas para un mismo mensaje.
    """

    rutas = []

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

        return {"rutas": rutas}

    # Para el resto de activos se mantiene elegible_contenido.
    if elegible_contenido is False:
        return {"rutas": []}

    # Estados antiguos sin la decisión por ID conservan
    # el umbral de respaldo.
    if (
        elegible_contenido is None
        and puntaje is not None
        and puntaje < UMBRAL_RELEVANCIA
    ):
        return {"rutas": []}

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

        if sentimiento in {"positivo", "muy_positivo"}:
            rutas.append("linkedin")

    return {
        "rutas": rutas
    }