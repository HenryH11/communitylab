"""
Generación de activos mediante un modelo de lenguaje según
las rutas seleccionadas por LangGraph.
"""

from functools import lru_cache

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from src.agentes.modelo_ia import obtener_modelo_gemini
from src.agentes.estado_agente import EstadoAgente


# --------------------------------------------------
# Modelos de salida
# --------------------------------------------------

class PublicacionLinkedIn(BaseModel):
    titulo: str = Field(
        description="Título breve y atractivo de la publicación."
    )

    contenido: str = Field(
        description=(
            "Texto completo de la publicación con tono inspirador "
            "y etiquetas apropiadas."
        )
    )


class DestaqueBoletin(BaseModel):
    seccion: str = Field(
        description='Ej. "Logro de la Semana".'
    )

    titular: str

    resumen: str = Field(
        description="Resumen breve de 1 a 2 frases."
    )


class SugerenciaPreguntasFrecuentes(BaseModel):
    tema: str = Field(
        description='Ej. "Tip Rápido: cómo..."'
    )

    respuesta: str = Field(
        description="Explicación breve y didáctica."
    )


class CasoDeExito(BaseModel):
    titular: str

    resumen: str = Field(
        description=(
            "Historia breve de 2 a 3 frases basada "
            "únicamente en el mensaje original."
        )
    )


# --------------------------------------------------
# LinkedIn
# --------------------------------------------------

_prompt_linkedin = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
Eres redactor de la comunidad ONE G10.

Escribe una publicación de LinkedIn inspiradora a partir
de un testimonio real.

No inventes información que no aparezca en el
mensaje original.
            """,
        ),
        (
            "user",
            """
Autor: {autor}
Tema: {tema_principal}
Subtema: {subtema}

Mensaje:
{texto}
            """,
        ),
    ]
)

# --------------------------------------------------
# Boletín
# --------------------------------------------------

_prompt_boletin = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
Resume este testimonio para una posible sección
'Logro de la Semana' de un boletín.

Utiliza un tono conciso y no inventes información.
            """,
        ),
        (
            "user",
            """
Autor: {autor}

Mensaje:
{texto}
            """,
        ),
    ]
)

# --------------------------------------------------
# Preguntas frecuentes
# --------------------------------------------------

_prompt_preguntas_frecuentes = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
Convierte esta pregunta técnica en un contenido
breve de preguntas frecuentes.

La respuesta debe ser clara y didáctica.

Si no puedes responder con suficiente certeza,
indícalo explícitamente en lugar de inventar
información.
            """,
        ),
        (
            "user",
            """
Subtema: {subtema}

Pregunta original:
{texto}
            """,
        ),
    ]
)

# --------------------------------------------------
# Caso de éxito
# --------------------------------------------------

_prompt_caso_exito = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
Redacta un caso de éxito breve para un panel
de curaduría.

Utiliza únicamente información presente en el
mensaje original y no inventes resultados.
            """,
        ),
        (
            "user",
            """
Autor: {autor}

Mensaje:
{texto}
            """,
        ),
    ]
)

# --------------------------------------------------
# Generación
# --------------------------------------------------

@lru_cache(maxsize=1)
def _obtener_generadores():
    modelo = obtener_modelo_gemini()
    return {
        "linkedin": _prompt_linkedin | modelo.with_structured_output(PublicacionLinkedIn),
        "boletin": _prompt_boletin
        | modelo.with_structured_output(DestaqueBoletin),
        "preguntas_frecuentes": _prompt_preguntas_frecuentes
        | modelo.with_structured_output(SugerenciaPreguntasFrecuentes),
        "caso_exito": _prompt_caso_exito
        | modelo.with_structured_output(CasoDeExito),
    }

def _contexto(estado: EstadoAgente) -> dict:
    return {
        "autor": estado.get("autor", "Anónimo"),
        "texto": estado["texto"],
        "tema_principal": estado.get(
            "tema_principal",
            "",
        ),
        "subtema": estado.get(
            "subtema",
            "",
        ),
    }


def generar_activos(estado: EstadoAgente) -> dict:
    """
    Genera contenido real para cada ruta
    seleccionada por LangGraph.

    Si una ruta falla, las demás pueden continuar.
    """

    activos = {}
    errores = list(estado.get("errores", []))
    rutas = estado.get("rutas", [])

    if not rutas:
        return {
            "activos_generados": activos,
            "errores": errores,
        }

    contexto = _contexto(estado)
    generadores = _obtener_generadores()

    for ruta in rutas:
        cadena = generadores.get(ruta)

        if cadena is None:
            continue

        try:
            resultado = cadena.invoke(contexto)

            activo = resultado.model_dump()

            if ruta == "linkedin":
                activo["canal_recomendado"] = "LinkedIn Oficial"

            activos[ruta] = activo

        except Exception as error:
            errores.append(
                f"generar_activos[{ruta}]: "
                f"{type(error).__name__}: {error}"
            )

    return {
        "activos_generados": activos,
        "errores": errores,
    }