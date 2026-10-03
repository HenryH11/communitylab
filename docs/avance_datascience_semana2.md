# Avance Data Science — Semana 2

## 1. Objetivo de la semana

Desarrollar, calibrar y validar los nodos cognitivos del flujo de Data Science para analizar interacciones de comunidad, enrutar resultados con LangGraph y generar activos estructurados utilizando Gemini, prompts especializados y Few-Shot Learning.

Los activos trabajados durante la semana son:

- LinkedIn
- Boletín / Community Highlight
- Preguntas frecuentes (FAQ)
- Caso de éxito
- Insight de mejora

También se consolidó el contrato oficial de salida de Data Science para facilitar el consumo posterior por interfaz, reportes u OCI.

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
    ↓
Contrato oficial de salida DS
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

Los tipos detectados actualmente son:

- `testimonio`
- `pregunta_tecnica`
- `pregunta_programa`
- `feedback`
- `comentario`

La categoría `pregunta_programa` se incorporó para diferenciar preguntas administrativas o relacionadas con el funcionamiento del programa, por ejemplo:

- costo de certificados;
- fechas de inscripción;
- acceso a grabaciones;
- diferencias entre rutas de especialidad;
- alianzas con empresas;
- consultas generales del programa.

Estas preguntas son identificadas correctamente por Data Science, pero por ahora no generan FAQ hasta que Data entregue un criterio específico como `elegible_faq`.

El resultado del procesamiento se mantiene como una estructura de Python serializable a JSON, facilitando su uso posterior en interfaz, API, reporting u OCI.

Ejemplo conceptual:

```json
{
  "id": "int-022",
  "sentimiento": "muy_positivo",
  "tema_principal": "empleabilidad",
  "subtema": "Desarrolladora Junior de IA",
  "tipo_original": "testimonio",
  "tipo_detectado": "testimonio",
  "score_relevancia": 95,
  "elegible_contenido": true,
  "rutas": [
    "caso_exito",
    "boletin",
    "linkedin"
  ],
  "activos_generados": {
    "caso_exito": {
      "titular": "...",
      "resumen": "..."
    },
    "boletin": {
      "seccion": "Logro de la comunidad",
      "titular": "...",
      "resumen": "..."
    },
    "linkedin": {
      "titulo": "...",
      "contenido": "...",
      "hashtags": [
        "#LangChain",
        "#OCI",
        "#InteligenciaArtificial"
      ],
      "canal_recomendado": "LinkedIn Oficial"
    }
  },
  "errores": []
}
```

---

## 4. Generación de activos

Los generadores se encuentran en:

`src/agentes/nodos/nodos_generadores.py`

Actualmente se manejan cinco tipos de activos estructurados:

- `PublicacionLinkedIn`
- `DestaqueBoletin`
- `SugerenciaPreguntasFrecuentes`
- `CasoDeExito`
- `InsightMejora`

Cada generador posee un prompt especializado según el objetivo del contenido.

Los prompts incluyen:

- instrucciones de tono;
- formato esperado;
- restricciones contra información inventada;
- ejemplos Few-Shot;
- uso exclusivo de información presente en la interacción;
- reglas de atribución cuando una afirmación corresponde a la percepción del autor;
- control de inferencias causales;
- control de referencias temporales;
- conservación de datos concretos como duración, tecnologías, cargos o resultados.

### LinkedIn

La salida de LinkedIn quedó estructurada en:

- `titulo`
- `contenido`
- `hashtags`
- `canal_recomendado`

Los hashtags se generan como una lista independiente de entre 3 y 4 elementos, facilitando su uso posterior en UI o reporting.

### Boletín / Community Highlight

La ruta técnica se mantiene como `boletin` por compatibilidad, pero su función actual es generar un Community Highlight breve y reutilizable.

La salida contiene:

- `seccion`
- `titular`
- `resumen`

### Insight de mejora

Se incorporó el activo `insight_mejora` para feedback relevante.

Su salida contiene:

- `hallazgo`
- `sugerencia_detectada`
- `area`

El campo `area` se deriva del `tema_principal` obtenido en el análisis previo y no se vuelve a inferir en el generador.

---

## 5. Few-Shot Learning

Se incorporaron ejemplos de referencia dentro de los prompts para orientar el comportamiento de Gemini.

### LinkedIn

El prompt orienta al modelo hacia:

- voz institucional;
- tercera persona;
- tono profesional y cercano;
- títulos relacionados con el logro real;
- hashtags estructurados;
- prohibición de copiar literalmente el ejemplo de referencia;
- prohibición de inventar causas, impactos, cronologías o circunstancias.

### Boletín / Community Highlight

El prompt define:

- sección;
- titular;
- resumen breve;
- tono informativo;
- síntesis reutilizable;
- atribución correcta de opiniones o percepciones;
- prohibición de transformar agradecimiento en apoyo o impacto no expresado.

### Preguntas frecuentes

El Few-Shot ayuda a generar:

- respuestas técnicas breves;
- explicaciones didácticas;
- respuestas prudentes cuando falta información;
- contenido sin comandos, configuraciones o datos inventados.

Por ahora este generador se utiliza únicamente con `pregunta_tecnica`.

### Caso de éxito

El prompt diferencia entre:

- hechos presentes en el mensaje;
- interpretaciones expresadas por la persona;
- relaciones causales explícitas;
- inferencias que no deben añadirse.

Por ejemplo, evita transformar:

`"el proyecto marcó la diferencia"`

en una afirmación más fuerte como:

`"consiguió el puesto gracias al proyecto"`

si esa relación causal no aparece explícitamente en el mensaje original.

### Insight de mejora

El prompt convierte feedback relevante en información interna accionable sin transformarlo en contenido promocional.

Distingue entre:

- hallazgo expresado por la persona;
- sugerencia explícita;
- recomendaciones que el modelo no debe inventar.

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

Reglas principales actuales:

```text
testimonio elegible
    ↓
caso_exito
boletin
linkedin si el sentimiento es positivo o muy_positivo
```

```text
pregunta_tecnica elegible
    ↓
preguntas_frecuentes
```

```text
feedback elegible
    ↓
insight_mejora
```

```text
pregunta_programa
    ↓
sin ruta por ahora
```

Los mensajes que no son elegibles para generación de contenido continúan recibiendo análisis de sentimiento, tema, subtema y tipo detectado, pero no generan rutas ni activos.

---

## 7. Control de cuota y estabilidad de Gemini

Durante las pruebas E2E se detectó un error `429 RESOURCE_EXHAUSTED` debido al límite de solicitudes por minuto del modelo Gemini utilizado.

Para estabilizar las ejecuciones se actualizó el cliente compartido de Gemini en:

`src/agentes/modelo_ia.py`

Se incorporaron:

- `InMemoryRateLimiter`
- límite aproximado de 12 solicitudes por minuto;
- `max_retries=6`;
- cliente compartido mediante `lru_cache`.

El objetivo es evitar ráfagas de solicitudes y permitir que el flujo completo finalice sin errores de cuota.

Después del ajuste, la prueba completa de 23 interacciones finalizó con:

```text
0 errores
```

---

## 8. Tests específicos de prompts

Se utiliza:

`tests/agents/test_prompts_generadores.py`

Los tests verifican:

- presencia de Few-Shot;
- uso de ejemplos de referencia;
- renderizado correcto de variables;
- reglas contra información inventada;
- estructura de los prompts;
- comportamiento esperado de LinkedIn, Boletín, FAQ y Caso de Éxito.

Comando:

```powershell
python -m pytest tests\agents\test_prompts_generadores.py -q
```

Resultado obtenido:

```text
5 passed
```

---

## 9. Tests del enrutador

Se actualizaron las pruebas del router para incluir:

- testimonio positivo → `caso_exito`, `boletin`, `linkedin`;
- testimonio neutral → `caso_exito`, `boletin`;
- feedback relevante → `insight_mejora`;
- feedback de baja relevancia → sin ruta;
- preguntas técnicas → `preguntas_frecuentes`.

Comando utilizado:

```powershell
python -m pytest tests\agents\test_enrutador.py -q
```

Resultado obtenido:

```text
8 passed
```

---

## 10. Suite de regresión

Después de incorporar los cambios de Semana 2 se ejecutó la suite completa del proyecto.

Comando:

```powershell
python -m pytest -q
```

Resultado:

```text
93 passed
106 subtests passed
0 failures
```

Puede aparecer un warning proveniente de la dependencia `google.genai`, sin afectar la ejecución funcional del proyecto.

---

## 11. Validación funcional con Gemini

Se realizaron pruebas individuales con Gemini para validar clasificación, routing y generación.

### Preguntas de programa

Se validaron ejemplos como:

- costo del certificado;
- inscripción al hackathon;
- acceso a grabaciones;
- diferencias entre Data Analyst y Data Scientist.

Resultado esperado:

```text
tipo_detectado: pregunta_programa
rutas: []
```

Este comportamiento es temporal hasta integrar el futuro criterio `elegible_faq` proveniente de Data.

### Feedback

Ejemplo:

```text
"Sugiero agregar más ejercicios prácticos antes de pasar al módulo
de estructuras de datos, se siente un salto grande."
```

Resultado:

```text
tipo_detectado: feedback
ruta:
- insight_mejora
```

Activo generado:

```text
hallazgo: Se percibe un salto importante antes del módulo de estructuras de datos.
sugerencia_detectada: Agregar más ejercicios prácticos antes de avanzar al módulo.
area: programacion
```

### Testimonio

Los testimonios elegibles pueden generar:

```text
caso_exito
boletin
linkedin
```

LinkedIn entrega hashtags como estructura independiente.

---

## 12. Prueba E2E del paquete completo de Data

La prueba de integración:

`tests/integracion/prueba_paquete_completo_datos.py`

valida el flujo completo:

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

Resultado final validado:

```text
Estados recibidos de Data: 23
Estados procesados por Data Science: 23
Estados pendientes: 0
Elegibles para contenido: 14
Con activos generados: 14
Con errores de ejecución: 0
```

Distribución observada en la ejecución final:

```text
Tipos detectados:
- testimonio: 8
- pregunta_tecnica: 4
- pregunta_programa: 5
- comentario: 4
- feedback: 2
```

Rutas ejecutadas:

```text
- caso_exito: 8
- boletin: 8
- linkedin: 8
- preguntas_frecuentes: 4
- insight_mejora: 2
```

Activos generados:

```text
- caso_exito: 8
- boletin: 8
- linkedin: 8
- preguntas_frecuentes: 4
- insight_mejora: 2

TOTAL: 30 activos
```

La ejecución E2E finalizó correctamente con:

```text
1 passed
0 errores
```

La prueba confirmó además que los mensajes no elegibles para contenido igualmente reciben análisis de Data Science, pero no generan rutas ni activos.

---

## 13. Contrato oficial de salida de Data Science

Se consolidó un contrato de salida versionado para desacoplar el procesamiento interno de DS de los consumidores posteriores.

Archivos principales:

`src/agentes/contrato_salida_ciencia_datos.py`

`src/agentes/entrega_resultados.py`

Versión actual:

```text
1.0
```

La estructura principal del contrato es:

```json
{
  "version_contrato": "1.0",
  "resumen_comunidad": {},
  "interacciones": [],
  "activos": [],
  "pendientes": [],
  "ids_pendientes": []
}
```

### resumen_comunidad

Incluye, entre otros:

- total de interacciones procesadas;
- total de pendientes;
- total de elegibles;
- total con activos;
- total de activos generados;
- total con errores;
- sentimiento predominante;
- distribución de sentimientos;
- distribución de temas;
- temas principales;
- distribución de tipos detectados.

### interacciones

Cada interacción mantiene trazabilidad de:

- datos originales;
- `tipo_original`;
- `score_relevancia`;
- `elegible_contenido`;
- análisis DS;
- rutas;
- activos generados;
- errores.

### activos

Además de encontrarse anidados dentro de cada interacción, los activos se entregan en una colección plana con:

- `id_interaccion`
- `tipo`
- `contenido`

Esto facilita su consumo por UI, reporting u OCI.

---

## 14. Prueba funcional del contrato de salida

La prueba:

`tests/integracion/prueba_entrega_resultados_funcional.py`

ejecuta:

```text
Data
    ↓
procesar_paquete_entrega(...)
    ↓
resultado interno DS
    ↓
entrega_resultados.py
    ↓
contrato oficial DS v1.0
```

Al finalizar genera:

```text
output\entrega_ciencia_datos_completa.json
output\resumen_entrega_ciencia_datos.txt
```

Resultado validado en la ejecución final:

```text
total_interacciones_procesadas: 23
total_pendientes: 0
total_elegibles_contenido: 14
total_con_activos: 14
total_activos_generados: 30
total_con_errores: 0
```

El JSON final contiene:

```text
resumen_comunidad
interacciones
activos
pendientes
ids_pendientes
```

y representa la salida oficial actual del módulo de Data Science.

---

## 15. Estado del entregable de Semana 2

| Componente | Estado |
|---|---|
| Prompt LinkedIn | Completado |
| Prompt Boletín / Community Highlight | Completado |
| Prompt FAQ técnica | Completado |
| Prompt Caso de Éxito | Completado |
| Prompt Insight de Mejora | Completado |
| Few-Shot Learning | Completado |
| Clasificación `pregunta_programa` | Completado |
| Salidas estructuradas | Completado |
| Hashtags estructurados en LinkedIn | Completado |
| Integración con LangGraph | Completado |
| Routing de testimonios | Completado |
| Routing de feedback | Completado |
| Tests específicos de prompts | Completado |
| Tests del router | Completado |
| Suite de regresión | Completado |
| Validación funcional con Gemini | Completado |
| Rate limiting / retries | Completado |
| Prueba Data → Data Science sobre paquete completo | Completado |
| Contrato oficial de salida DS v1.0 | Completado |
| Prueba funcional del contrato | Completado |

---

## 16. Pendientes inmediatos

### 1. Integración de preguntas de programa con FAQ

Esperar el ajuste del equipo de Data para incorporar un criterio específico como:

`elegible_faq`

Una vez disponible, Data Science podrá evaluar el routing:

```text
pregunta_programa + elegible_faq
    ↓
preguntas_frecuentes
```

El generador de FAQ deberá adaptarse para manejar preguntas del programa sin inventar información institucional.

### 2. Deduplicación o agrupación de FAQ

Se identificaron preguntas técnicas prácticamente equivalentes en el dataset.

Como mejora posterior puede evaluarse:

```text
preguntas similares
    ↓
agrupación / deduplicación
    ↓
FAQ canónica
    ↓
frecuencia
```

Esto permitiría generar una FAQ consolidada en lugar de una respuesta independiente por cada interacción repetida.

### 3. Integración posterior con UI y OCI

El contrato de salida v1.0 ya deja preparado el módulo de Data Science para ser consumido por:

- interfaz de curaduría;
- reportes;
- persistencia en OCI Object Storage;
- servicios posteriores del proyecto.

---

## 17. Resultado general de Semana 2

El módulo de Data Science ya cuenta con:

```text
Análisis semántico estructurado
        ↓
Clasificación de interacción
        ↓
Routing determinista con LangGraph
        ↓
Generación de activos especializados
        ↓
Contrato oficial de salida DS v1.0
```

Validación final:

```text
23 interacciones procesadas
0 pendientes
14 interacciones con activos
30 activos generados
0 errores

93 tests passed
106 subtests passed
```

Con esto, el flujo de Data Science queda funcionalmente validado para la etapa actual del proyecto.