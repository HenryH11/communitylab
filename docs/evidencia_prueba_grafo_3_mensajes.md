# Evidencia de integración Data + LangChain + LangGraph

## Objetivo

Validar el flujo de Data Science utilizando mensajes del dataset real de prueba:

`src/data/mensajes_comunidad_simulados.json`

El dataset contiene:

- 4 lotes
- 23 mensajes
- 19 mensajes que superan actualmente los criterios de relevancia

Para esta validación se procesaron 3 mensajes relevantes.

## Flujo probado

```text
Dataset
  ↓
relevancia.py
  ↓
score_relevancia
  ↓
AgentState
  ↓
LangChain + Gemini
  ↓
sentimiento + tema + subtema + tipo_detectado
  ↓
LangGraph
  ↓
routing
  ↓
activos MOCK

#Resultado prueba
================================================================================
PRUEBA DE 3 MENSAJES DEL DATASET
================================================================================

Lotes encontrados: 4
Mensajes encontrados: 23
Fecha de referencia: 2026-09-16T16:00:00+00:00
Mensajes que superaron relevancia: 19
Mensajes enviados al grafo: 3

================================================================================
MENSAJE 1 DE 3
================================================================================
ID: int-022
Origen: Discord_Grupo_ONE_G10
Periodo: Semana_00
Autor: Mariana Souza
Canal: #logros-y-empleos
Texto: Comunidad, quede seleccionada para el puesto de Desarrolladora Junior de IA! El proyecto del curso de LangChain y OCI que construi en mi portfolio marco toda la diferencia en la entrevista tecnica. Muy agradecida con la comunidad por todo el apoyo!

DATOS / RELEVANCIA
--------------------------------------------------------------------------------
Tipo original: testimonio
Score relevancia: 95
Desglose: {'tipo': 40, 'longitud': 20, 'palabras_clave': 25, 'frescura': 10}
Palabras clave: ['curso', 'langchain', 'oci', 'portfolio', 'proyecto']

Procesando con LangChain + LangGraph...

RESULTADO IA
--------------------------------------------------------------------------------
Sentimiento: muy_positivo
Tema principal: empleabilidad
Subtema: empleo Desarrolladora Junior IA
Tipo detectado: testimonio

ROUTING
--------------------------------------------------------------------------------
Rutas: ['caso_exito', 'linkedin']
Activos: {'caso_exito': {'status': 'mock', 'mensaje': 'Aquí se generará un caso de éxito.'}, 'linkedin': {'status': 'mock', 'mensaje': 'Aquí se generará un post de LinkedIn.'}}Errores: []

================================================================================
MENSAJE 2 DE 3
================================================================================
ID: int-001
Origen: Discord_Grupo_ONE_G10
Periodo: Semana_00
Autor: Camila Restrepo
Canal: #logros-y-empleos
Texto: Comunidad, gracias a este programa conseguí mi primer trabajo como analista de datos en menos de 3 meses. El proyecto final de mi portfolio fue clave en la entrevista técnica.

DATOS / RELEVANCIA
--------------------------------------------------------------------------------
Tipo original: testimonio
Score relevancia: 90
Desglose: {'tipo': 40, 'longitud': 20, 'palabras_clave': 20, 'frescura': 10}
Palabras clave: ['datos', 'portfolio', 'proyecto', 'trabajo']

Procesando con LangChain + LangGraph...

RESULTADO IA
--------------------------------------------------------------------------------
Sentimiento: muy_positivo
Tema principal: empleabilidad
Subtema: primer empleo analista de datos
Tipo detectado: testimonio

ROUTING
--------------------------------------------------------------------------------
Rutas: ['caso_exito', 'linkedin']
Activos: {'caso_exito': {'status': 'mock', 'mensaje': 'Aquí se generará un caso de éxito.'}, 'linkedin': {'status': 'mock', 'mensaje': 'Aquí se generará un post de LinkedIn.'}}Errores: []

================================================================================
MENSAJE 3 DE 3
================================================================================
ID: int-002
Origen: Discord_Grupo_ONE_G10
Periodo: Semana_00
Autor: Diego Fernández
Canal: #dudas-langgraph
Texto: Tengo dudas sobre cómo estructurar los nodos condicionales en LangGraph cuando la respuesta del LLM necesita reintento. ¿Alguien tiene un ejemplo práctico de router?

DATOS / RELEVANCIA
--------------------------------------------------------------------------------
Tipo original: pregunta_tecnica
Score relevancia: 80
Desglose: {'tipo': 40, 'longitud': 20, 'palabras_clave': 10, 'frescura': 10}
Palabras clave: ['langgraph', 'llm']

Procesando con LangChain + LangGraph...

RESULTADO IA
--------------------------------------------------------------------------------
Sentimiento: neutral
Tema principal: datos_ia
Subtema: nodos condicionales LangGraph
Tipo detectado: pregunta_tecnica

ROUTING
--------------------------------------------------------------------------------
Rutas: ['faq']
Activos: {'faq': {'status': 'mock', 'mensaje': 'Aquí se generará una FAQ.'}}
Errores: []

================================================================================
PRUEBA FINALIZADA
================================================================================

# Para realizar esta prueba ejecutar
"python -m scripts.probar_grafo_3_mensajes"