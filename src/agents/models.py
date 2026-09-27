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