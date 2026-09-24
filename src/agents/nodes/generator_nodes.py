"""
Generación de activos mediante LLM según
las rutas seleccionadas por LangGraph.
"""

import os

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from src.agents.state import AgentState


load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError(
        "No se encontró GEMINI_API_KEY. "
        "Verifica que exista en el archivo .env."
    )


llm_generador = ChatGoogleGenerativeAI(
    api_key=GEMINI_API_KEY,
    model="gemini-3.5-flash-lite",
)


# --------------------------------------------------
# Modelos de salida
# --------------------------------------------------

class PostLinkedin(BaseModel):
    titulo: str = Field(
        description="Título corto y atractivo del post."
    )

    contenido: str = Field(
        description=(
            "Texto completo del post con tono inspirador "
            "y hashtags apropiados."
        )
    )

class DestaqueNewsletter(BaseModel):
    seccion: str = Field(
        description='Ej. "Logro de la Semana".'
    )

    titular: str

    resumen: str = Field(
        description="Resumen breve de 1 a 2 frases."
    )


class SugerenciaFAQ(BaseModel):
    tema: str = Field(
        description='Ej. "Tip Rápido: cómo..."'
    )

    respuesta: str = Field(
        description="Explicación breve y didáctica."
    )


class CasoExito(BaseModel):
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
Eres copywriter de la comunidad ONE G10.

Escribe un post de LinkedIn inspirador a partir
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

_cadena_linkedin = (
    _prompt_linkedin
    | llm_generador.with_structured_output(PostLinkedin)
)


# --------------------------------------------------
# Newsletter
# --------------------------------------------------

_prompt_newsletter = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
Resume este testimonio para una posible sección
'Logro de la Semana' de una newsletter.

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

_cadena_newsletter = (
    _prompt_newsletter
    | llm_generador.with_structured_output(
        DestaqueNewsletter
    )
)


# --------------------------------------------------
# FAQ
# --------------------------------------------------

_prompt_faq = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
Convierte esta pregunta técnica en un contenido
breve de FAQ.

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

_cadena_faq = (
    _prompt_faq
    | llm_generador.with_structured_output(
        SugerenciaFAQ
    )
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

_cadena_caso_exito = (
    _prompt_caso_exito
    | llm_generador.with_structured_output(
        CasoExito
    )
)


# --------------------------------------------------
# Generación
# --------------------------------------------------

def _contexto(state: AgentState) -> dict:
    return {
        "autor": state.get("autor", "Anónimo"),
        "texto": state["texto"],
        "tema_principal": state.get(
            "tema_principal",
            "",
        ),
        "subtema": state.get(
            "subtema",
            "",
        ),
    }


def generar_activos(state: AgentState) -> dict:
    """
    Genera contenido real para cada ruta
    seleccionada por LangGraph.

    Si una ruta falla, las demás pueden continuar.
    """

    activos = {}
    errores = list(state.get("errores", []))

    contexto = _contexto(state)

    generadores = {
        "linkedin": _cadena_linkedin,
        "newsletter": _cadena_newsletter,
        "faq": _cadena_faq,
        "caso_exito": _cadena_caso_exito,
    }

    for ruta in state.get("rutas", []):
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