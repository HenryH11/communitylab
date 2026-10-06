# Evidencia de generación real de contenido con Gemini

## Objetivo

> Esta evidencia conserva las salidas literales de una ejecución anterior. En
> esa versión la ruta `faq` se llamaba así; la implementación actual usa
> `preguntas_frecuentes`.

Validar que el flujo de Ciencia de Datos puede analizar una interacción,
determinar las rutas correspondientes mediante LangGraph y generar activos
reales utilizando Gemini.

Esta prueba reemplaza la etapa anterior en la que los nodos generadores
devolvían contenido SIMULADO.

---

## Flujo validado

```text
Mensaje
  ↓
EstadoAgente
  ↓
LangChain + Gemini
  ↓
Análisis semántico
  ↓
LangGraph
  ↓
Enrutador
  ↓
Generadores con Gemini
  ↓
Activos estructurados
```

Para reproducir la integración actual, ejecutar
`python -m scripts.demostracion_lotes_ciencia_datos` desde la raíz del repositorio.

Caso 1 — int-022

Autor: Mariana Souza
Canal: #logros-y-empleos

Mensaje original:

Comunidad, quede seleccionada para el puesto de Desarrolladora Junior de IA! El proyecto del curso de LangChain y OCI que construi en mi portfolio marco toda la diferencia en la entrevista tecnica. Muy agradecida con la comunidad por todo el apoyo!

Datos provenientes del módulo de relevancia:

Tipo original: testimonio
Puntaje relevancia: 95

Desglose:
tipo: 40
longitud: 20
palabras_clave: 25
frescura: 10
Resultado del análisis con el modelo de lenguaje
Sentimiento: muy_positivo
Tema principal: empleabilidad
Subtema: empleo Desarrolladora Junior de IA
Tipo detectado: testimonio

El análisis mantuvo correctamente la clasificación semántica del mensaje como testimonio y detectó su relación con empleabilidad.

Enrutamiento

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

`#ONEG10 #IA #DesarrolloProfesional #Empleabilidad`
`#OrgulloComunidad #Tech`

Canal recomendado:
LinkedIn Oficial

Resultado de ejecución:

Errores: []

Por lo tanto:

int-022
→ puntaje relevancia 95
→ testimonio
→ muy_positivo
→ empleabilidad
→ caso_exito ✅
→ linkedin ✅
Caso 2 — int-002

Autor: Diego Fernández
Canal: #dudas-langgraph

Mensaje original:
Resultado del análisis con el modelo de lenguaje
Tengo dudas sobre cómo estructurar los nodos condicionales en LangGraph cuando la respuesta del LLM necesita reintento. ¿Alguien tiene un ejemplo práctico de enrutador?

Datos provenientes del módulo de relevancia:

Tipo original: pregunta_tecnica
Puntaje relevancia: 80

Desglose:
tipo: 40
longitud: 20
palabras_clave: 10
frescura: 10
Resultado del análisis con el modelo de lenguaje
Sentimiento: neutral
Tema principal: datos_ia
Subtema: nodos condicionales LangGraph
Tipo detectado: pregunta_tecnica

El modelo identificó correctamente una consulta relacionada con una
implementación técnica de LangGraph.

Enrutamiento
LangGraph determinó:

['faq']

Por tanto, únicamente se ejecutó el generador de preguntas frecuentes.

FAQ generada
Tema:
Tip Rápido: Nodos condicionales y reintentos en LangGraph

Respuesta:
En LangGraph, un enrutador condicional evalúa el estado actual (por ejemplo,
la respuesta de un modelo de lenguaje) mediante una función de decisión. Si
la respuesta no es válida o requiere corrección, la función dirige al nodo de
reintento (`nodo_reintento`); si es correcta, continúa al nodo final
(`nodo_final`). Esto se implementa con `add_conditional_edges`, conectando
el nodo del modelo de lenguaje con el enrutador.

Resultado de ejecución:

Errores: []

Por lo tanto:

int-002
→ puntaje relevancia 80
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
EstadoAgente
  ↓
Gemini
  ↓
LangGraph
  ↓
Enrutamiento
  ↓
Generación real

Resultados obtenidos:

int-022
├── caso_exito ✅
└── linkedin ✅

int-002
└── faq ✅

Errores: []

Esta prueba valida además el comportamiento de multienrutamiento, ya que
int-022 produjo dos activos diferentes a partir de una sola interacción.

También confirma que el score_relevancia calculado por el módulo de Datos
es consumido por el flujo de IA sin ser recalculado por el modelo de lenguaje.
