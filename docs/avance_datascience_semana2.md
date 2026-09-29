# Avance Data Science — Semana 2

## 1. Objetivo de la semana

Desarrollar y validar los nodos cognitivos de generación de activos del flujo de Data Science, utilizando prompts especializados, Few-Shot Learning y salidas estructuradas.

Los activos trabajados durante la semana son:

- LinkedIn
- Boletín / Newsletter
- Preguntas frecuentes (FAQ)
- Caso de éxito como activo adicional

---

## 2. Arquitectura utilizada

El flujo mantiene la separación acordada entre Data y Data Science:

```text
DATA
    ↓
preparar_paquete_ia(...)
    ↓
Paquete estructurado
    ├── estados
    ├── plan
    └── informe
    ↓
DATA SCIENCE
    ↓
procesar_paquete_entrega(...)
    ↓
Gemini
    ↓
Análisis estructurado
    ↓
LangGraph
    ↓
Routing determinista
    ↓
Generación de activos
```

Data Science consume la salida preparada por Data y no recalcula:

- `score_relevancia`
- `tipo_original`
- `ids_contenido`
- ciclos de procesamiento
- estados pendientes

La responsabilidad de Data Science comienza a partir del paquete recibido.

---

## 3. Análisis estructurado

El análisis realizado con Gemini produce campos estructurados que luego son utilizados por LangGraph.

Entre los campos principales se encuentran:

- `sentimiento`
- `tema_principal`
- `subtema`
- `tipo_detectado`

Los niveles de sentimiento utilizados son:

- `muy_positivo`
- `positivo`
- `neutral`
- `negativo`
- `muy_negativo`

El resultado del procesamiento se mantiene como una estructura de Python serializable a JSON, lo que facilita su uso posterior en una interfaz, API u OCI.

Ejemplo conceptual:

```json
{
  "id": "int-022",
  "sentimiento": "muy_positivo",
  "tema_principal": "empleabilidad",
  "subtema": "empleo de desarrolladora junior",
  "tipo_original": "testimonio",
  "tipo_detectado": "testimonio",
  "score_relevancia": 95,
  "rutas": [
    "caso_exito",
    "linkedin"
  ],
  "activos_generados": {
    "caso_exito": {
      "titular": "...",
      "resumen": "..."
    },
    "linkedin": {
      "titulo": "...",
      "contenido": "...",
      "canal_recomendado": "LinkedIn Oficial"
    }
  }
}
```

---

## 4. Generación de activos

Los generadores se encuentran en:

`src/agentes/nodos/nodos_generadores.py`

Actualmente se manejan cuatro tipos de activos estructurados:

- `PublicacionLinkedIn`
- `DestaqueBoletin`
- `SugerenciaPreguntasFrecuentes`
- `CasoDeExito`

Cada generador posee un prompt especializado según el canal y el objetivo del contenido.

Los prompts incluyen:

- instrucciones de tono;
- formato esperado;
- restricciones contra información inventada;
- ejemplos Few-Shot;
- uso exclusivo de información presente en la interacción;
- reglas de atribución cuando una afirmación corresponde a la percepción del autor.

---

## 5. Few-Shot Learning

Se incorporaron ejemplos de referencia dentro de los prompts para orientar el comportamiento de Gemini.

### LinkedIn

El prompt orienta al modelo hacia:

- tono profesional y cercano;
- títulos relacionados con el logro real;
- hashtags derivados del contenido;
- uso moderado de emojis;
- prohibición de copiar literalmente el ejemplo de referencia.

### Boletín

El prompt define:

- sección;
- titular;
- resumen breve;
- tono informativo;
- atribución correcta de opiniones o percepciones.

### Preguntas frecuentes

El Few-Shot ayuda a generar:

- respuestas técnicas breves;
- explicaciones didácticas;
- respuestas prudentes cuando falta información;
- contenido sin comandos o datos inventados.

### Caso de éxito

El prompt diferencia entre:

- hechos presentes en el mensaje;
- interpretaciones expresadas por la persona.

Por ejemplo, evita transformar:

`"el proyecto marcó la diferencia"`

en una afirmación más fuerte como:

`"consiguió el puesto gracias al proyecto"`

si esa relación causal no aparece explícitamente en el mensaje original.

---

## 6. Integración con LangGraph

La generación de activos no decide qué contenido debe producirse.

El flujo se mantiene separado:

```text
Análisis IA
    ↓
Router determinista
    ↓
Rutas
    ↓
Generadores
```

Ejemplos:

```text
testimonio positivo y elegible
    ↓
caso_exito
linkedin
```

```text
pregunta_tecnica y elegible
    ↓
preguntas_frecuentes
```

Los mensajes que no son elegibles para generación de contenido continúan recibiendo análisis de sentimiento, tema, subtema y tipo detectado, pero no generan rutas ni activos.

---

## 7. Tests específicos de prompts

Se agregó:

`tests/agents/test_prompts_generadores.py`

Los tests verifican:

- presencia de Few-Shot;
- uso de ejemplos de referencia;
- renderizado correcto de variables;
- reglas contra información inventada;
- estructura de los prompts de LinkedIn, Boletín, FAQ y Caso de Éxito.

Comando:

```powershell
python -B -m pytest tests/agents/test_prompts_generadores.py -v -p no:cacheprovider
```

Resultado obtenido:

```text
5 passed
```

---

## 8. Suite de regresión

Después de incorporar los tests de Semana 2 se ejecutó la suite completa del proyecto.

Comando:

```powershell
python -B -m pytest -q -p no:cacheprovider
```

Resultado:

```text
92 passed
106 subtests passed
0 failures
```

Puede aparecer un warning proveniente de la dependencia `google.genai`, sin afectar la ejecución funcional del proyecto.

---

## 9. Validación funcional con Gemini

Se ejecutó la demostración del flujo:

```powershell
python -m scripts.demostracion_lotes_ciencia_datos
```

### Caso `int-022`

Entrada:

```text
testimonio
score_relevancia = 95
```

Resultado:

```text
sentimiento: muy_positivo
tema_principal: empleabilidad
tipo_detectado: testimonio
rutas:
- caso_exito
- linkedin
```

Los activos fueron generados correctamente y el resultado final no presentó errores.

### Caso `int-002`

Entrada:

```text
pregunta_tecnica
score_relevancia = 80
```

Resultado:

```text
sentimiento: neutral
tema_principal: datos_ia
tipo_detectado: pregunta_tecnica
rutas:
- preguntas_frecuentes
```

La FAQ fue generada correctamente y el resultado final no presentó errores.

### Boletín

También se realizó una ejecución directa del generador de Boletín con Gemini.

Resultado:

```text
seccion: Logro de la Semana
titular: generado correctamente
resumen: generado correctamente
errores: []
```

---

## 10. Prueba E2E del paquete completo de Data

Se creó una prueba de integración para validar el contrato completo entre Data y Data Science:

`tests/integracion/prueba_paquete_completo_datos.py`

La prueba utiliza el paquete generado por:

`src.datos.entrega_ia.preparar_paquete_ia(...)`

a través de:

`cargar_paquete_demostracion(...)`

y posteriormente ejecuta:

`procesar_paquete_entrega(paquete)`

El flujo validado es:

```text
mensajes_comunidad_simulados.json
    ↓
preparar_paquete_ia(...)
    ↓
23 estados entregados por Data
    ↓
procesar_paquete_entrega(...)
    ↓
Gemini
    ↓
análisis estructurado
    ↓
LangGraph
    ↓
routing
    ↓
activos generados
```

Resultados observados:

```text
Estados recibidos de Data: 23
Estados procesados por Data Science: 23
Estados pendientes: 0
Elegibles para contenido: 14
Con activos generados: 12
Con errores de ejecución: 0
```

Distribución obtenida:

```text
Sentimientos:
- muy_positivo: 8
- positivo: 4
- neutral: 11

Tipos detectados:
- testimonio: 8
- pregunta_tecnica: 4
- comentario: 9
- feedback: 2

Rutas ejecutadas:
- caso_exito: 8
- linkedin: 8
- preguntas_frecuentes: 4
```

La prueba confirmó además que los mensajes no elegibles para contenido igualmente reciben análisis de Data Science, pero no generan rutas ni activos.

Durante la primera ejecución se detectó una condición demasiado estricta en el propio test: se exigía que todos los resultados incluyeran físicamente la clave `errores`, aunque el flujo permite interpretar su ausencia como una lista vacía.

Este ajuste corresponde únicamente al test de integración y no requiere cambios en el código de Data ni en el pipeline productivo de Data Science.

---

## 11. Estado del entregable de Semana 2

| Componente | Estado |
|---|---|
| Prompt LinkedIn | Completado |
| Prompt Boletín | Completado |
| Prompt FAQ | Completado |
| Prompt Caso de Éxito | Completado |
| Few-Shot Learning | Completado |
| Salidas estructuradas | Completado |
| Integración con LangGraph | Completado |
| Tests específicos de prompts | Completado |
| Suite de regresión | Completado |
| Validación funcional con Gemini | Completado |
| Prueba Data → Data Science sobre paquete completo | Completado |

---

## 12. Pendiente inmediato

Ajustar la validación del campo opcional `errores` en:

`tests/integracion/prueba_paquete_completo_datos.py`

y repetir la prueba completa para dejarla en estado aprobado.

El cambio debe limitarse al test de integración, sin modificar el contrato de Data ni el flujo productivo de Data Science.
