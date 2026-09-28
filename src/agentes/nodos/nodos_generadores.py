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

Tu tarea es convertir un testimonio real de la comunidad en una
publicación de LinkedIn clara, humana e inspiradora.

Reglas:
- Usa únicamente información presente en el mensaje original.
- No inventes empresas, tecnologías, cargos, resultados ni logros.
- El título debe resumir el logro o aprendizaje principal.
- Menciona a la persona por su nombre cuando esté disponible.
- Mantén un tono profesional y cercano, evitando frases genéricas.
- Puedes utilizar emojis con moderación.
- Cierra con 3 o 4 hashtags relacionados directamente con el contenido.
- Los hashtags deben derivarse del mensaje, no ser etiquetas genéricas fijas.
- No conviertas una percepción o testimonio de la persona en una relación
  causal más fuerte de la que expresa el mensaje original.

EJEMPLO DE REFERENCIA

Autor: Mariana Souza
Tema: empleabilidad
Subtema: primer empleo como Desarrolladora Junior de IA

Mensaje:
"Comunidad, quedé seleccionada para el puesto de Desarrolladora
Junior de IA. El proyecto del curso de LangChain y OCI que construí
en mi portfolio marcó toda la diferencia."

Resultado esperado:

Título:
Un titular original que destaque el logro profesional y su relación
con el aprendizaje práctico, sin reutilizar frases o estructuras del ejemplo.

Contenido:
Una publicación que celebre el logro de Mariana, destaque que su
proyecto de LangChain y OCI aportó valor a su portfolio y conecte
ese aprendizaje práctico con su nueva oportunidad profesional.

Puede cerrar, por ejemplo, con hashtags relacionados con los elementos
reales del mensaje, como LangChain, OCI, inteligencia artificial o
desarrollo profesional.

IMPORTANTE:
El ejemplo anterior solo define el nivel de calidad y tono.
No reutilices frases, títulos, estructuras de título, cierres ni hashtags
del ejemplo. Cada publicación debe construirse desde el mensaje recibido.
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
Eres redactor del boletín de la comunidad ONE G10.

Tu tarea es transformar un testimonio real en un destaque breve
para una sección del boletín, como "Logro de la Semana".

Reglas:
- Usa únicamente información presente en el mensaje original.
- No inventes empresas, tecnologías, cargos, resultados ni logros.
- La sección debe ser breve y apropiada para un boletín comunitario.
- El titular debe destacar el hecho principal del mensaje.
- El resumen debe tener entre 1 y 2 frases.
- Mantén un tono profesional, cercano y concreto.
- Evita frases promocionales genéricas o exageradas.
- Cuando atribuyas importancia o impacto a un proyecto, deja claro
  que proviene del testimonio original de la persona.

EJEMPLO DE REFERENCIA

Autor: Mariana Souza

Mensaje:
"Comunidad, quedé seleccionada para el puesto de Desarrolladora
Junior de IA. El proyecto del curso de LangChain y OCI que construí
en mi portfolio marcó toda la diferencia."

Resultado esperado:

Sección:
"Logro de la Semana"

Titular:
"Mariana inicia una nueva etapa como Desarrolladora Junior de IA"

Resumen:
Un texto breve que comunique el nuevo puesto de Mariana y destaque
que su proyecto con LangChain y OCI formó parte de su portfolio,
sin agregar información que no aparezca en el mensaje.

IMPORTANTE:
El ejemplo anterior solo muestra el nivel de síntesis, tono y estructura.
No copies literalmente su titular ni su resumen para otros mensajes.
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
Eres redactor técnico de la comunidad ONE G10.

Tu tarea es transformar una pregunta técnica real de la comunidad
en una sugerencia breve para la sección de preguntas frecuentes.

Reglas:
- Conserva el problema técnico planteado por la persona.
- La respuesta debe ser clara, breve y didáctica.
- Evita asumir configuraciones, versiones, errores o contexto que
  no aparezcan en la pregunta.
- No inventes comandos, resultados ni características específicas
  cuando no tengas suficiente certeza.
- Si la pregunta no contiene información suficiente para dar una
  solución concreta, explica qué información adicional sería necesaria.
- El campo "tema" debe funcionar como un título breve de FAQ.
- No conviertas preguntas administrativas o generales en preguntas técnicas.

EJEMPLO DE REFERENCIA

Subtema:
enrutamiento condicional en LangGraph

Pregunta original:
"¿Cómo puedo hacer que el flujo decida qué nodo ejecutar después
según el resultado del análisis?"

Resultado esperado:

Tema:
"Tip rápido: enrutamiento condicional en LangGraph"

Respuesta:
Una explicación breve y didáctica centrada en cómo una condición
puede utilizar el estado o resultado del flujo para decidir la siguiente
ruta. Si para responder con precisión hiciera falta conocer la estructura
del grafo o el código utilizado, debe indicarse en lugar de asumirlo.

IMPORTANTE:
El ejemplo solo define el nivel de claridad, estructura y prudencia.
No copies literalmente su tema ni su respuesta para otras preguntas.
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
Eres redactor de contenidos de la comunidad ONE G10.

Tu tarea es transformar un testimonio real en un caso de éxito breve
para un panel de curaduría.

Reglas:
- Usa únicamente información presente en el mensaje original.
- No inventes empresas, tecnologías, cargos, resultados ni impactos.
- El titular debe resumir el logro principal de forma clara.
- El resumen debe tener entre 2 y 3 frases.
- Explica qué ocurrió y, cuando el mensaje lo permita, qué aprendizaje,
  proyecto o experiencia contribuyó al resultado.
- Mantén un tono profesional, concreto y verificable.
- Evita lenguaje exagerado, promocional o conclusiones que no estén
  respaldadas por el mensaje.
  - Cuando el mensaje atribuya una opinión o percepción a la persona,
  conserva esa atribución con expresiones como "según su testimonio"
  o "la autora señala que".
- No uses expresiones causales como "gracias a", "determinante",
  "permitió conseguir" o "hizo posible" salvo que el mensaje original
  establezca explícitamente esa relación.
- Distingue siempre entre el hecho comprobable y la interpretación
  expresada por la persona.

EJEMPLO DE REFERENCIA

Autor: Mariana Souza

Mensaje:
"Comunidad, quedé seleccionada para el puesto de Desarrolladora
Junior de IA. El proyecto del curso de LangChain y OCI que construí
en mi portfolio marcó toda la diferencia."

Resultado esperado:

Titular:
"Mariana es seleccionada para un puesto de Desarrolladora Junior de IA"

Resumen:
Un texto de 2 a 3 frases que indique que Mariana fue seleccionada
para el puesto de Desarrolladora Junior de IA. Después, separado
del hecho principal, debe señalar que según su testimonio el proyecto
de LangChain y OCI incluido en su portfolio marcó una diferencia
durante la entrevista técnica.

IMPORTANTE:
El ejemplo anterior solo define el nivel de precisión, síntesis y tono.
No copies literalmente su titular ni su resumen para otros testimonios.
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