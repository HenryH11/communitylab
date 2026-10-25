from typing import Literal, Required, TypedDict


Ruta = Literal[
    "preguntas_frecuentes",
    "caso_exito",
    "linkedin",
    "boletin",
    "insight_mejora",
]


class EstadoAgente(TypedDict, total=False):
    # -----------------------------
    # Datos de entrada
    # -----------------------------
    id: Required[str]
    autor: str
    canal: str
    origen: str
    idioma: str
    texto: Required[str]

    # Clasificación proveniente de Datos
    tipo_original: str | None

    # Relevancia calculada por el equipo de Datos
    score_relevancia: float | None
    elegible_contenido: bool
    elegible_faq: bool

    # -----------------------------
    # Resultado de LangChain / Gemini
    # -----------------------------
    sentimiento: str
    tema_principal: str
    subtema: str
    tipo_detectado: str
    es_spam_detectado: bool
    motivo_spam: str | None

    # -----------------------------
    # Resultado de LangGraph
    # -----------------------------
    rutas: list[Ruta]
    tier_modelo: str

    # Semana 2: contenido generado
    activos_generados: dict

    # Control de errores
    errores: list[str]
    fallos: list[dict]
