from src.agentes.estado_agente import EstadoAgente


UMBRAL_RELEVANCIA = 40


def determinar_rutas(estado: EstadoAgente) -> dict:
    """
    Determina qué activos puede generar una interacción
    a partir del análisis semántico y del puntaje de relevancia.

    Puede devolver varias rutas para un mismo mensaje.
    """

    rutas = []

    elegible_contenido = estado.get("elegible_contenido")
    if elegible_contenido is False:
        return {"rutas": []}

    puntaje = estado.get("score_relevancia")

    # Estados antiguos sin la decisión por ID conservan el umbral de respaldo.
    if (
        elegible_contenido is None
        and puntaje is not None
        and puntaje < UMBRAL_RELEVANCIA
    ):
        return {"rutas": []}

    tipo = estado.get("tipo_detectado")
    sentimiento = estado.get("sentimiento")

    # Una pregunta técnica relevante puede alimentar las preguntas frecuentes.
    if tipo == "pregunta_tecnica":
        rutas.append("preguntas_frecuentes")

    # El feedback relevante se transforma en un insight accionable
    # para el equipo responsable de la comunidad o del programa.
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