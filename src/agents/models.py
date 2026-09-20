"AnalisisMensaje"
"AgentState"

from typing import Literal

from pydantic import BaseModel, Field


class AnalisisMensaje(BaseModel):
    sentimiento: Literal[
        "muy_positivo",
        "positivo",
        "neutral",
        "negativo",
        "muy_negativo",
    ] = Field(
        description="Sentimiento principal expresado en el mensaje."
    )

    tema: str = Field(
        description=(
            "Tema principal del mensaje expresado como una categoría "
            "breve, general y normalizada, preferentemente entre 1 y 3 palabras."
        )
    )

    tipo_detectado: Literal[
        "testimonio",
        "pregunta_tecnica",
        "feedback",
        "comentario",
    ] = Field(
        description="Clasificación semántica del tipo de interacción."
    )

    #Ejemplo de salida de la clase AnalisisMensaje
    """AnalisisMensaje(
        sentimiento="muy_positivo",
        tema="empleabilidad",
        tipo_detectado="testimonio"
    )"""