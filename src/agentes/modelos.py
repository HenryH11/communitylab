from typing import Literal

from pydantic import BaseModel, Field


Sentimiento = Literal[
    "muy_positivo",
    "positivo",
    "neutral",
    "negativo",
    "muy_negativo",
]


TipoInteraccion = Literal[
    "testimonio",
    "pregunta_tecnica",
    "pregunta_programa",
    "feedback",
    "comentario",
]


TemaPrincipal = Literal[
    "empleabilidad",
    "aprendizaje",
    "programacion",
    "datos_ia",
    "plataforma",
    "comunidad",
    "mentoria",
    "cloud_infraestructura",
    "certificacion",
    "programa_hackathon",
    "otros",
]


class AnalisisMensaje(BaseModel):
    sentimiento: Sentimiento = Field(
        description="Sentimiento principal expresado en el mensaje."
    )

    tema_principal: TemaPrincipal = Field(
        description="Categoría general y normalizada del tema principal."
    )

    subtema: str = Field(
        description=(
            "Detalle breve y específico del tema principal, "
            "preferentemente entre 1 y 5 palabras."
        ),
        min_length=1,
        max_length=80,
    )

    tipo_detectado: TipoInteraccion = Field(
        description="Clasificación semántica realizada por la IA."
    )


class AnalisisMensajeConId(AnalisisMensaje):
    id: str = Field(
        min_length=1,
        description="ID exacto de la interacción analizada.",
    )


class AnalisisLote(BaseModel):
    resultados: list[AnalisisMensajeConId] = Field(
        description="Un análisis independiente por cada ID recibido."
    )


# --------------------------------------------------
# Activos generados
# --------------------------------------------------

class PublicacionLinkedIn(BaseModel):
    titulo: str = Field(
        description=(
            "Título institucional, natural y fiel al hecho principal "
            "del testimonio."
        )
    )

    contenido: str = Field(
        description=(
            "Texto de la publicación para LinkedIn escrito desde la voz "
            "institucional. No debe incluir hashtags dentro del contenido."
        )
    )

    hashtags: list[str] = Field(
        min_length=3,
        max_length=4,
        description=(
            "Entre 3 y 4 hashtags directamente relacionados con el mensaje, "
            "tema o subtema. Cada elemento debe comenzar con #."
        ),
    )


class DestaqueBoletin(BaseModel):
    seccion: str = Field(
        description=(
            'Categoría breve del destaque, por ejemplo '
            '"Logro de la comunidad", "Aprendizaje destacado" '
            'o "Proyecto destacado".'
        )
    )

    titular: str = Field(
        description="Titular breve que destaque el hecho principal."
    )

    resumen: str = Field(
        description=(
            "Resumen de 1 a 2 frases preparado para un Community Highlight."
        )
    )


class SugerenciaPreguntasFrecuentes(BaseModel):
    tema: str = Field(
        description="Título breve y descriptivo para la entrada de FAQ."
    )

    respuesta: str = Field(
        description=(
            "Respuesta breve, didáctica y prudente. "
            "No debe inventar información técnica, administrativa "
            "o institucional que no esté sustentada."
        )
    )


class CasoDeExito(BaseModel):
    titular: str = Field(
        description="Titular factual que resuma el logro principal."
    )

    resumen: str = Field(
        description=(
            "Historia breve de 2 a 3 frases basada únicamente "
            "en el mensaje original."
        )
    )


class InsightMejora(BaseModel):
    hallazgo: str = Field(
        description=(
            "Hallazgo breve y objetivo identificado a partir del feedback."
        )
    )

    sugerencia_detectada: str | None = Field(
        default=None,
        description=(
            "Sugerencia expresada explícitamente por la persona. "
            "Debe ser None si el mensaje no propone una mejora concreta."
        ),
    )