"""ChatPromptTemplate
       ↓
Gemini
       ↓
cadena_analisis"""

import os

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

from src.agents.models import AnalisisMensaje


load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError(
        "No se encontró GEMINI_API_KEY. "
        "Verifica que exista en el archivo .env."
    )


llm = ChatGoogleGenerativeAI(
    api_key=GEMINI_API_KEY,
    model="gemini-3.5-flash-lite",
)


template_analisis = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
Eres un analista de comunidades digitales.

Tu tarea es analizar mensajes provenientes de comunidades
de aprendizaje y tecnología.

Para cada mensaje debes determinar:

1. El sentimiento principal.
2. El tema principal.
3. El tipo real de interacción.

Para el sentimiento utiliza únicamente:
- muy_positivo
- positivo
- neutral
- negativo
- muy_negativo

Para el sentimiento:
- Clasifica como neutral los mensajes puramente informativos
  que no expresen satisfacción, frustración, entusiasmo,
  rechazo u otra valoración emocional clara.
- No interpretes automáticamente completar una actividad
  como sentimiento positivo.

Para el tema:
- Devuelve una categoría breve y general.
- Evita frases descriptivas largas.
- Utiliza preferentemente entre 1 y 3 palabras.
- Agrupa conceptos equivalentes bajo una misma categoría.

Ejemplos:
"Conseguí mi primer trabajo como desarrollador" -> empleabilidad
"No entiendo los nodos condicionales de LangGraph" -> LangGraph
"El curso me pareció excelente" -> curso
"La plataforma se cae constantemente" -> plataforma

Para el tipo de interacción utiliza únicamente:
- testimonio
- pregunta_tecnica
- feedback
- comentario

Definiciones:

testimonio:
Mensaje en primera persona donde alguien relata una experiencia
personal que produjo un resultado, transformación, hito o impacto
relevante gracias al programa, curso, comunidad o aprendizaje.

Ejemplos:
- conseguir empleo;
- cambiar de carrera;
- aprender algo que antes parecía difícil;
- aplicar conocimientos en un proyecto real;
- completar un proyecto importante;
- explicar cómo el programa produjo un impacto personal concreto.

Si un mensaje contiene al mismo tiempo una valoración del curso
y una transformación personal concreta, prioriza testimonio.


pregunta_tecnica:
Mensaje cuya intención principal es solicitar ayuda o
resolver una duda técnica.

feedback:
Mensaje cuyo objetivo principal es señalar una mejora, problema,
crítica, sugerencia o aspecto que debería modificarse en el curso,
plataforma, comunidad o experiencia.

Un elogio general sin sugerencia, crítica o propuesta de mejora
no debe clasificarse automáticamente como feedback.

comentario:
Observación, reacción, felicitación, elogio o información general
que no presenta una transformación personal relevante, una pregunta
ni una sugerencia o crítica concreta.

Los elogios generales como "Buen material", "Excelente iniciativa"
o "Los mentores responden rápido" deben clasificarse como comentario
si no contienen una propuesta de mejora o una historia personal
de impacto.

IMPORTANTE: Ejemplos de clasificación:

Mensaje:
"Gracias al proyecto que desarrollé durante el curso conseguí
mi primer empleo como desarrollador."

Resultado:
sentimiento: muy_positivo
tema: empleabilidad
tipo_detectado: testimonio


Mensaje:
"No entiendo cómo crear nodos condicionales en LangGraph.
¿Alguien podría ayudarme?"

Resultado:
sentimiento: neutral
tema: LangGraph
tipo_detectado: pregunta_tecnica


Mensaje:
"La plataforma se cae constantemente y deberían mejorar
la estabilidad."

Resultado:
sentimiento: negativo
tema: plataforma
tipo_detectado: feedback


Mensaje:
"Hoy terminé el módulo de Python y mañana comenzaré SQL."

Resultado:
sentimiento: neutral
tema: progreso de estudio
tipo_detectado: comentario

Mensaje:
"Buen material el de la última clase, los ejemplos fueron muy claros."

Resultado:
sentimiento: positivo
tema: curso
tipo_detectado: comentario


Mensaje:
"Sería bueno agregar más ejercicios antes de pasar al siguiente módulo."

Resultado:
sentimiento: neutral
tema: ejercicios prácticos
tipo_detectado: feedback


Mensaje:
"Nunca pensé que podría aprender SQL y Python al mismo tiempo,
pero la metodología del curso lo hizo posible."

Resultado:
sentimiento: muy_positivo
tema: aprendizaje
tipo_detectado: testimonio

Analiza el significado del mensaje y no dependas únicamente
del tipo que pudiera haber sido asignado previamente.
            """,
        ),
        (
            "user",
            """
Analiza el siguiente mensaje:

{texto}
            """,
        ),
    ]
)


llm_estructurado = llm.with_structured_output(AnalisisMensaje)


cadena_analisis = template_analisis | llm_estructurado