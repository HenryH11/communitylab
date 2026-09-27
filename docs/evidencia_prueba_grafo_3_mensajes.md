# Evidencia de integración Datos + LangChain + LangGraph

## Objetivo

> Esta evidencia conserva las salidas literales de una ejecución anterior. En
> esa versión la ruta `faq` se llamaba así; la implementación actual usa
> `preguntas_frecuentes`.

Validar el flujo de Ciencia de Datos utilizando mensajes del conjunto de datos real de prueba:

`src/datos/mensajes_comunidad_simulados.json`

El conjunto de datos contiene:

- 4 lotes
- 23 mensajes
- 19 mensajes que superan actualmente los criterios de relevancia

Para esta validación se procesaron 3 mensajes relevantes.

## Flujo probado

```text
Conjunto de datos
  ↓
relevancia.py
  ↓
score_relevancia
  ↓
EstadoAgente
  ↓
LangChain + Gemini
  ↓
sentimiento + tema + subtema + tipo_detectado
  ↓
LangGraph
  ↓
enrutamiento
  ↓
activos simulados

#Resultado de la prueba
================================================================================
PRUEBA DE 3 MENSAJES DEL CONJUNTO DE DATOS
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
Puntaje relevancia: 95
Desglose: {'tipo': 40, 'longitud': 20, 'palabras_clave': 25, 'frescura': 10}
Palabras clave: ['curso', 'langchain', 'oci', 'portfolio', 'proyecto']

Procesando con LangChain + LangGraph...

RESULTADO IA
--------------------------------------------------------------------------------
Sentimiento: muy_positivo
Tema principal: empleabilidad
Subtema: empleo Desarrolladora Junior IA
Tipo detectado: testimonio

ENRUTAMIENTO
--------------------------------------------------------------------------------
Rutas: ['caso_exito', 'linkedin']
Activos: {'caso_exito': {'estado': 'simulado', 'mensaje': 'Aquí se generará un caso de éxito.'}, 'linkedin': {'estado': 'simulado', 'mensaje': 'Aquí se generará una publicación de LinkedIn.'}}Errores: []

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
Puntaje relevancia: 90
Desglose: {'tipo': 40, 'longitud': 20, 'palabras_clave': 20, 'frescura': 10}
Palabras clave: ['datos', 'portfolio', 'proyecto', 'trabajo']

Procesando con LangChain + LangGraph...

RESULTADO IA
--------------------------------------------------------------------------------
Sentimiento: muy_positivo
Tema principal: empleabilidad
Subtema: primer empleo analista de datos
Tipo detectado: testimonio

ENRUTAMIENTO
--------------------------------------------------------------------------------
Rutas: ['caso_exito', 'linkedin']
Activos: {'caso_exito': {'estado': 'simulado', 'mensaje': 'Aquí se generará un caso de éxito.'}, 'linkedin': {'estado': 'simulado', 'mensaje': 'Aquí se generará una publicación de LinkedIn.'}}Errores: []

================================================================================
MENSAJE 3 DE 3
================================================================================
ID: int-002
Origen: Discord_Grupo_ONE_G10
Periodo: Semana_00
Autor: Diego Fernández
Canal: #dudas-langgraph
Texto: Tengo dudas sobre cómo estructurar los nodos condicionales en LangGraph cuando la respuesta del LLM necesita reintento. ¿Alguien tiene un ejemplo práctico de enrutador?

DATOS / RELEVANCIA
--------------------------------------------------------------------------------
Tipo original: pregunta_tecnica
Puntaje relevancia: 80
Desglose: {'tipo': 40, 'longitud': 20, 'palabras_clave': 10, 'frescura': 10}
Palabras clave: ['langgraph', 'llm']

Procesando con LangChain + LangGraph...

RESULTADO IA
--------------------------------------------------------------------------------
Sentimiento: neutral
Tema principal: datos_ia
Subtema: nodos condicionales LangGraph
Tipo detectado: pregunta_tecnica

ENRUTAMIENTO
--------------------------------------------------------------------------------
Rutas: ['faq']
Activos: {'faq': {'estado': 'simulado', 'mensaje': 'Aquí se generará una FAQ.'}}
Errores: []

================================================================================
PRUEBA FINALIZADA
================================================================================

Este documento conserva la evidencia histórica del flujo simulado de tres mensajes;
el script mencionado ya no forma parte del árbol actual. Para reproducir la
integración vigente de dos mensajes con análisis lote y generación real:

```powershell
python -m scripts.demostracion_lotes_ciencia_datos
```
