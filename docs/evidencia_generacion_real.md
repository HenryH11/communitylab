# Evidencia de generación real de activos con LLM

## Objetivo

Validar que el pipeline de Data Science puede analizar una interacción,
determinar las rutas correspondientes mediante LangGraph y generar activos
reales utilizando Gemini.

Esta prueba reemplaza la etapa anterior en la que los nodos generadores
devolvían contenido MOCK.

---

## Flujo validado

```text
Mensaje
  ↓
AgentState
  ↓
LangChain + Gemini
  ↓
Análisis semántico
  ↓
LangGraph
  ↓
Router
  ↓
Generadores con Gemini
  ↓
Activos estructurados



""esto se logra ejecutnado  python -m scripts.probar_grafo_2_mensajes_reales" IMPORTANTE

Caso 1 — int-022

Autor: Mariana Souza
Canal: #logros-y-empleos

Mensaje original:

Comunidad, quede seleccionada para el puesto de Desarrolladora Junior de IA! El proyecto del curso de LangChain y OCI que construi en mi portfolio marco toda la diferencia en la entrevista tecnica. Muy agradecida con la comunidad por todo el apoyo!

Datos provenientes del módulo de relevancia:

Tipo original: testimonio
Score relevancia: 95

Desglose:
tipo: 40
longitud: 20
palabras_clave: 25
frescura: 10
Resultado del análisis con LLM
Sentimiento: muy_positivo
Tema principal: empleabilidad
Subtema: empleo Desarrolladora Junior de IA
Tipo detectado: testimonio

El análisis mantuvo correctamente la clasificación semántica del mensaje como testimonio y detectó su relación con empleabilidad.

Routing

LangGraph determinó:

['caso_exito', 'linkedin']

Por tanto, una misma interacción activó dos generadores diferentes.

Caso de éxito generado
Titular:
De proyecto en el portfolio a Desarrolladora Junior de IA

Resumen:
Mariana Souza consiguió el puesto de Desarrolladora Junior de IA gracias
a un proyecto de LangChain y OCI en su portfolio, el cual fue clave en
su entrevista técnica.
Publicación de LinkedIn generada
Título:
¡Nueva Desarrolladora Junior de IA en la comunidad! 🤖✨

Contenido:
¡Una gran noticia para nuestra comunidad! 🎉

Mariana Souza ha sido seleccionada para el puesto de Desarrolladora
Junior de IA.

Ella misma nos comparte que el proyecto del curso de LangChain y OCI
que construyó para su portfolio marcó toda la diferencia en su
entrevista técnica.

¡Muchas felicidades, Mariana! Tu dedicación y esfuerzo están dando
frutos. Gracias por ser parte de ONE G10 y compartir tu logro con
nosotros. 🚀

#ONEG10 #IA #DesarrolloProfesional #Empleabilidad
#OrgulloComunidad #Tech

Canal recomendado:
LinkedIn Oficial

Resultado de ejecución:

Errores: []

Por lo tanto:

int-022
→ score relevancia 95
→ testimonio
→ muy_positivo
→ empleabilidad
→ caso_exito ✅
→ linkedin ✅
Caso 2 — int-002

Autor: Diego Fernández
Canal: #dudas-langgraph

Mensaje original:

Tengo dudas sobre cómo estructurar los nodos condicionales en LangGraph cuando la respuesta del LLM necesita reintento. ¿Alguien tiene un ejemplo práctico de router?

Datos provenientes del módulo de relevancia:

Tipo original: pregunta_tecnica
Score relevancia: 80

Desglose:
tipo: 40
longitud: 20
palabras_clave: 10
frescura: 10
Resultado del análisis con LLM
Sentimiento: neutral
Tema principal: datos_ia
Subtema: nodos condicionales LangGraph
Tipo detectado: pregunta_tecnica

El modelo identificó correctamente una consulta relacionada con una
implementación técnica de LangGraph.

Routing

LangGraph determinó:

['faq']

Por tanto, únicamente se ejecutó el generador correspondiente a FAQ.

FAQ generada
Tema:
Tip Rápido: Nodos condicionales y reintentos en LangGraph

Respuesta:
En LangGraph, un router condicional evalúa el estado actual (por ejemplo,
la respuesta de un LLM) mediante una función de decisión. Si la respuesta
no es válida o necesita corrección, la función devuelve elnombre del nodo
de reintento ("retry_node"); si es correcta, dirige al nodo final
("end_node"). Esto se implementa usando 'add_conditional_edges' conectando
el nodo del LLM con el router.

Resultado de ejecución:

Errores: []

Por lo tanto:

int-002
→ score relevancia 80
→ pregunta_tecnica
→ neutral
→ datos_ia
→ faq ✅
Resultado de la prueba

Los dos mensajes completaron correctamente el flujo:

Datos
  ↓
Relevancia
  ↓
AgentState
  ↓
Gemini
  ↓
LangGraph
  ↓
Routing
  ↓
Generación real

Resultados obtenidos:

int-022
├── caso_exito ✅
└── linkedin ✅

int-002
└── faq ✅

Errores: []

Esta prueba valida además el comportamiento de multirouting, ya que
int-022 produjo dos activos diferentes a partir de una sola interacción.

También confirma que el score_relevancia calculado por el módulo de Datos
es consumido por el flujo de IA sin ser recalculado por el LLM.