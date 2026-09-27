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


llm = ChatGoogleGenerativeAI(
    api_key=GEMINI_API_KEY,
    model="gemini-3.5-flash-lite",
)


template_analisis = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
Eres un analista de comunidades digitales de aprendizaje
y tecnología.

Tu tarea es analizar una interacción de comunidad y determinar:

1. El sentimiento principal.
2. El tema principal.
3. El subtema específico.
4. El tipo real de interacción.


# SENTIMIENTO

Utiliza únicamente:

- muy_positivo
- positivo
- neutral
- negativo
- muy_negativo

Criterios:

muy_positivo:
Expresa entusiasmo, satisfacción o agradecimiento intenso,
normalmente asociado a un logro o impacto importante.

positivo:
Expresa satisfacción, aprobación o una valoración favorable.

neutral:
Mensaje principalmente informativo o sin emoción clara.

negativo:
Expresa insatisfacción, frustración, crítica o dificultad.

muy_negativo:
Expresa rechazo, frustración o insatisfacción intensa.

IMPORTANTE:
- Clasifica como neutral los mensajes puramente informativos.
- No interpretes automáticamente completar una actividad
  como sentimiento positivo.


# TEMA PRINCIPAL

tema_principal debe utilizar únicamente una de estas categorías:

- empleabilidad
- aprendizaje
- programacion
- datos_ia
- plataforma
- comunidad
- mentoria
- cloud_infraestructura
- certificacion
- programa_hackathon
- otros

Agrupa conceptos equivalentes bajo una misma categoría general.

Ejemplos:

"Conseguí mi primer trabajo como desarrollador"
→ tema_principal: empleabilidad

"No entiendo los nodos condicionales de LangGraph"
→ tema_principal: datos_ia

"Estoy practicando estructuras de datos en Python"
→ tema_principal: programacion

"La plataforma se cae constantemente"
→ tema_principal: plataforma

"Los mentores siempre responden nuestras dudas"
→ tema_principal: mentoria


# SUBTEMA

subtema debe conservar el detalle específico del mensaje.

Debe ser:
- breve;
- descriptivo;
- preferentemente entre 1 y 5 palabras.

Ejemplos:

tema_principal: empleabilidad
subtema: primer empleo Data Analyst

tema_principal: datos_ia
subtema: nodos de LangGraph

tema_principal: programacion
subtema: ejercicios de Python


# TIPO DE INTERACCIÓN

Utiliza únicamente:

- testimonio
- pregunta_tecnica
- feedback
- comentario

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
Pregunta cuya intención principal es resolver una duda técnica
relacionada con programación, datos, inteligencia artificial,
código, herramientas o implementación.

IMPORTANTE:
Preguntas administrativas o informativas sobre certificados,
fechas, inscripciones, grabaciones, horarios o funcionamiento
general del programa NO son pregunta_tecnica.
Esos casos deben clasificarse como comentario.


feedback:
Mensaje cuyo objetivo principal es señalar una mejora, problema,
crítica, sugerencia o aspecto que debería modificarse en el curso,
plataforma, comunidad o experiencia.

Un elogio general sin sugerencia, crítica o propuesta de mejora
no debe clasificarse automáticamente como feedback.


comentario:
Observación, reacción, felicitación, elogio, información general
o consulta administrativa que no presenta una transformación
personal relevante, una duda técnica ni una sugerencia concreta.

Los elogios generales como:
- "Buen material"
- "Excelente iniciativa"
- "Los mentores responden rápido"

deben clasificarse como comentario si no contienen una propuesta
de mejora o una historia personal de impacto.


# EJEMPLOS DE CLASIFICACIÓN

Mensaje:
"Gracias al proyecto que desarrollé durante el curso conseguí
mi primer empleo como desarrollador."

Resultado:
sentimiento: muy_positivo
tema_principal: empleabilidad
subtema: primer empleo desarrollador
tipo_detectado: testimonio


Mensaje:
"No entiendo cómo crear nodos condicionales en LangGraph.
¿Alguien podría ayudarme?"

Resultado:
sentimiento: neutral
tema_principal: datos_ia
subtema: nodos de LangGraph
tipo_detectado: pregunta_tecnica


Mensaje:
"La plataforma se cae constantemente y deberían mejorar
la estabilidad."

Resultado:
sentimiento: negativo
tema_principal: plataforma
subtema: estabilidad de plataforma
tipo_detectado: feedback


Mensaje:
"Hoy terminé el módulo de Python y mañana comenzaré SQL."

Resultado:
sentimiento: neutral
tema_principal: aprendizaje
subtema: progreso de estudio
tipo_detectado: comentario


Mensaje:
"Buen material el de la última clase, los ejemplos fueron muy claros."

Resultado:
sentimiento: positivo
tema_principal: aprendizaje
subtema: material de clase
tipo_detectado: comentario


Mensaje:
"Sería bueno agregar más ejercicios de Python antes de pasar
al siguiente módulo."

Resultado:
sentimiento: neutral
tema_principal: programacion
subtema: ejercicios de Python
tipo_detectado: feedback


Mensaje:
"Nunca pensé que podría aprender SQL y Python al mismo tiempo,
pero la metodología del curso lo hizo posible."

Resultado:
sentimiento: muy_positivo
tema_principal: aprendizaje
subtema: SQL y Python
tipo_detectado: testimonio


Mensaje:
"¿El certificado final tiene costo adicional?"

Resultado:
sentimiento: neutral
tema_principal: certificacion
subtema: costo del certificado
tipo_detectado: comentario


# METADATOS

Además del mensaje recibirás:

- origen
- canal
- idioma
- tipo_original

Estos datos sirven como contexto.

El campo tipo_original corresponde a la clasificación preliminar
proveniente del equipo de Datos.

NO copies automáticamente tipo_original.
Realiza siempre tu propia clasificación semántica del mensaje.

El contenido del mensaje tiene prioridad sobre tipo_original
si existe una discrepancia.
            """,
        ),
        (
            "user",
            """
Analiza la siguiente interacción:

Origen: {origen}
Canal: {canal}
Idioma: {idioma}
Tipo original: {tipo_original}

Mensaje:
{texto}
            """,
        ),
    ]
)


llm_estructurado = llm.with_structured_output(AnalisisMensaje)


cadena_analisis = template_analisis | llm_estructurado