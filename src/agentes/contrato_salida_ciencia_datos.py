"""Contrato estructurado de salida de Data Science.

Este módulo define la forma estable que Data Science entrega a los
consumidores posteriores del proyecto (UI, persistencia OCI, reportes
u otras capas de aplicación).

No ejecuta Gemini, LangGraph ni escritura de archivos.
"""

from typing import Required, TypedDict

from src.agentes.estado_agente import Ruta


VERSION_CONTRATO_SALIDA_DS = "1.3"


class TemaPrincipalResumen(TypedDict):
    tema: str
    cantidad: int


class ResumenComunidad(TypedDict):
    total_interacciones_procesadas: int
    total_pendientes: int
    total_elegibles_contenido: int
    total_elegibles_faq: int
    total_con_activos: int
    total_activos_generados: int
    total_con_errores: int
    total_fallos: int
    total_fallos_reintentables: int
    fallos_por_etapa: dict[str, int]
    sentimiento_predominante: str | None
    sentimientos_predominantes: list[str]
    distribucion_sentimientos: dict[str, int]
    temas_principales: list[TemaPrincipalResumen]
    distribucion_temas: dict[str, int]
    distribucion_tipos_detectados: dict[str, int]


class ResultadoInteraccion(TypedDict, total=False):
    # Identidad y contexto heredados de Data.
    id: Required[str]
    autor: str
    canal: str
    origen: str
    idioma: str
    texto: str

    # Campos provenientes de Data.
    tipo_original: str
    score_relevancia: float | None
    elegible_contenido: bool
    elegible_faq: Required[bool]

    # Resultado de Data Science.
    sentimiento: str
    tema_principal: str
    subtema: str
    tipo_detectado: str

    # Resultado de LangGraph y generadores.
    rutas: Required[list[Ruta]]
    activos_generados: Required[dict[str, dict]]
    errores: Required[list[str]]
    fallos: Required[list[dict]]


class ActivoEntregado(TypedDict):
    id_interaccion: str
    tipo: str
    contenido: dict


class EntregaCienciaDatos(TypedDict):
    version_contrato: str
    id_ejecucion: str | None
    resumen_comunidad: ResumenComunidad
    interacciones: list[ResultadoInteraccion]
    activos: list[ActivoEntregado]
    fallos: list[dict]
    ids_reintentables: list[str]
    pendientes: list[dict]
    ids_pendientes: list[str]
