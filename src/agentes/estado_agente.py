from typing import Literal, TypedDict


Ruta = Literal[
    "preguntas_frecuentes",
    "caso_exito",
    "linkedin",
    "boletin",
]


class EstadoAgente(TypedDict, total=False):
    # -----------------------------
    # Datos de entrada
    # -----------------------------
    id: str
    autor: str
    canal: str
    origen: str
    idioma: str
    texto: str

    # Clasificación proveniente de Datos
    tipo_original: str

    # Relevancia calculada por el equipo de Datos
    score_relevancia: float | None
    elegible_contenido: bool

    # -----------------------------
    # Resultado de LangChain / Gemini
    # -----------------------------
    sentimiento: str
    tema_principal: str
    subtema: str
    tipo_detectado: str

    # -----------------------------
    # Resultado de LangGraph
    # -----------------------------
    rutas: list[Ruta]

    # Semana 2: contenido generado
    activos_generados: dict

    # Control de errores
    errores: list[str]