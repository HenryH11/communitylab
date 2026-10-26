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
- `elegible_faq`
- `ids_contenido`
- ciclos de procesamiento
- estados pendientes

La responsabilidad de Data Science comienza a partir del paquete recibido.

---

## 3. Análisis estructurado

El análisis realizado con Gemini produce campos estructurados utilizados posteriormente por LangGraph.

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

### Preguntas del programa

La categoría `pregunta_programa` diferencia preguntas administrativas o relacionadas con el funcionamiento del programa, por ejemplo:

- costo de certificados;
- fechas de inscripción;
- acceso a grabaciones;
- diferencias entre rutas de especialidad;
- alianzas con empresas;
- consultas generales del programa.

Data incorpora el campo `elegible_faq`, calculado previamente a partir de sus reglas de relevancia. Data Science consume este valor sin recalcularlo y lo utiliza como criterio específico para decidir si una pregunta del programa puede generar una FAQ.

La regla integrada es:

```text
pregunta_programa + elegible_faq = true
    ↓
preguntas_frecuentes
```

El campo `elegible_faq` se conserva también en el contrato de salida para mantener trazabilidad sobre la decisión tomada por Data.

El resultado del procesamiento se mantiene como una estructura de Python serializable a JSON, facilitando su uso posterior en interfaz, API, reporting u OCI.

Ejemplo conceptual:

```json
{
  "id": "int-004",
  "tipo_original": "pregunta_programa",
  "score_relevancia": 62,
  "elegible_contenido": true,
  "elegible_faq": true,
  "sentimiento": "neutral",
  "tema_principal": "certificacion",
  "subtema": "costo del certificado",
  "tipo_detectado": "pregunta_programa",
  "rutas": [
    "preguntas_frecuentes"
  ],
  "activos_generados": {
    "preguntas_frecuentes": {
      "tema": "Costo del certificado final",
      "respuesta": "..."
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
- uso exclusivo de información disponible en la interacción cuando corresponde;
- reglas de atribución cuando una afirmación corresponde a la percepción del autor;
- control de inferencias causales;
- control de referencias temporales;
- conservación de datos concretos como duración, tecnologías, cargos o resultados.

### LinkedIn

La salida de LinkedIn está estructurada en:

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

### Preguntas frecuentes

El generador de FAQ soporta actualmente dos tipos de interacción:

- `pregunta_tecnica`
- `pregunta_programa`

Para preguntas técnicas, el prompt busca producir respuestas breves y didácticas.

Para `pregunta_programa`, se incorporaron reglas adicionales de seguridad:

- no inventar precios, fechas, condiciones, beneficios o procedimientos;
- no asumir características institucionales no proporcionadas;
- indicar cuando la información debe confirmarse mediante una fuente oficial vigente;
- mantener la respuesta como propuesta sujeta a posterior validación humana.

El prompt incluye ejemplos Few-Shot diferenciados para preguntas técnicas y preguntas del programa.

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
- contenido sin comandos, configuraciones o datos inventados;
- comportamiento diferenciado entre `pregunta_tecnica` y `pregunta_programa`;
- respuestas institucionales prudentes y sujetas a validación oficial cuando corresponde.

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
pregunta_programa + elegible_faq = true
    ↓
preguntas_frecuentes
```

Para `pregunta_programa`, la elegibilidad específica `elegible_faq` controla esta ruta. Si el campo no existe o es `false`, no se genera una FAQ.

La decisión de `elegible_faq` pertenece a Data; Data Science únicamente la consume durante el routing.

Los mensajes que no son elegibles para generación de contenido continúan recibiendo análisis de sentimiento, tema, subtema y tipo detectado, pero no generan rutas ni activos.

---

## 7. Control de cuota y estabilidad de Gemini

Durante las pruebas E2E se detectó previamente un error `429 RESOURCE_EXHAUSTED` debido al límite de solicitudes por minuto del modelo Gemini utilizado.

Para estabilizar las ejecuciones se actualizó el cliente compartido de Gemini en:

`src/agentes/modelo_ia.py`

Se incorporaron:

- `InMemoryRateLimiter`;
- límite aproximado de 12 solicitudes por minuto;
- `max_retries=6`;
- cliente compartido mediante `lru_cache`.

El objetivo es evitar ráfagas de solicitudes y permitir que el flujo completo finalice sin errores de cuota.

La prueba E2E integrada de 23 interacciones finalizó sin errores de ejecución.

---

## 8. Tests específicos de prompts

Se utiliza:

`tests/agents/test_prompts_generadores.py`

Los tests verifican:

- presencia de Few-Shot;
- renderizado correcto de variables;
- reglas contra información inventada;
- estructura de los prompts;
- comportamiento esperado de LinkedIn, Boletín, FAQ y Caso de Éxito;
- comportamiento diferenciado entre `pregunta_tecnica` y `pregunta_programa`;
- prohibición de inventar información institucional en FAQ de programa.

Comando:

```powershell
python -m pytest tests\agents\test_prompts_generadores.py -q
```

Resultado validado:

```text
6 passed
```

---

## 9. Tests del enrutador

Se actualizaron las pruebas del router para incluir:

- testimonio positivo → `caso_exito`, `boletin`, `linkedin`;
- testimonio neutral → `caso_exito`, `boletin`;
- feedback relevante → `insight_mejora`;
- feedback de baja relevancia → sin ruta;
- pregunta técnica elegible → `preguntas_frecuentes`;
- `pregunta_programa` + `elegible_faq=true` → `preguntas_frecuentes`;
- `pregunta_programa` + `elegible_faq=false` → sin ruta;
- compatibilidad cuando `elegible_faq` no está presente.

Comando:

```powershell
python -m pytest tests\agents\test_enrutador.py -q
```

Resultado validado:

```text
11 passed
```

La validación conjunta de router y prompts produjo:

```text
17 passed
```

---

## 10. Suite de regresión

Después de incorporar los cambios de `elegible_faq`, routing y contrato 1.1 se ejecutó la suite completa del proyecto con:

```powershell
python -m pytest -q
```

La suite finalizó correctamente sin fallos.

Puede aparecer un `DeprecationWarning` proveniente de la dependencia `google.genai`. La advertencia es externa y no afecta la ejecución funcional del proyecto.

---

## 11. Validación funcional con Gemini

Se realizaron pruebas con Gemini para validar clasificación, routing y generación.

### Preguntas de programa

Se validó la integración real entre la rama de Data y Data Science utilizando cinco preguntas de programa:

- `int-004`: costo del certificado;
- `int-007`: fecha límite de inscripción al hackathon;
- `int-010`: alianzas con empresas para prácticas;
- `int-013`: acceso a grabaciones;
- `int-015`: diferencias entre rutas de aprendizaje.

Los cinco estados fueron entregados por Data con:

```text
tipo_original: pregunta_programa
elegible_faq: true
```

Data Science los clasificó también como `pregunta_programa` y ejecutó:

```text
rutas:
- preguntas_frecuentes
```

Las respuestas generadas mantuvieron un comportamiento prudente: no inventaron precios, fechas, alianzas, procedimientos ni características institucionales y recomendaron consultar información oficial vigente cuando los datos no estaban disponibles en la interacción.

### Feedback

Los mensajes de feedback elegibles generan:

```text
tipo_detectado: feedback
ruta:
- insight_mejora
```

El activo conserva el hallazgo, la sugerencia explícita cuando existe y el área asociada.

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

La prueba funcional utiliza el flujo:

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
    ↓
contrato DS 1.1
```

Antes de ejecutar Gemini se validó directamente el paquete generado por Data:

```text
Total estados: 23
Elegibles contenido: 19
Elegibles FAQ: 5
```

Estados con `elegible_faq=true`:

```text
int-004 | pregunta_programa | score 62
int-007 | pregunta_programa | score 59
int-010 | pregunta_programa | score 55
int-013 | pregunta_programa | score 61
int-015 | pregunta_programa | score 61
```

Resultado final del E2E:

```text
Estados recibidos de Data: 23
Estados procesados por Data Science: 23
Estados pendientes: 0
Elegibles para contenido: 19
Elegibles para FAQ: 5
Activos individuales generados: 35
Resultados con errores: 0
Contrato: 1.1
```

Distribución funcional de activos:

```text
- caso_exito: 8
- boletin: 8
- linkedin: 8
- preguntas_frecuentes: 9
- insight_mejora: 2

TOTAL: 35 activos
```

Las 9 FAQ corresponden a:

```text
4 preguntas técnicas
+
5 preguntas del programa
```

La ejecución funcional completa finalizó con:

```text
1 passed
0 errores
```

La integración E2E tardó aproximadamente 3 minutos y 20 segundos debido al rate limiting configurado para proteger la cuota de Gemini.

---

## 13. Contrato oficial de salida de Data Science

Se consolidó un contrato de salida versionado para desacoplar el procesamiento interno de DS de los consumidores posteriores.

Archivos principales:

`src/agentes/contrato_salida_ciencia_datos.py`

`src/agentes/entrega_resultados.py`

Versión actual:

```text
1.1
```

La estructura principal del contrato es:

```json
{
  "version_contrato": "1.1",
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
- total de elegibles para contenido;
- `total_elegibles_faq`;
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
- `elegible_faq`;
- análisis DS;
- rutas;
- activos generados;
- errores.

Para mantener compatibilidad con paquetes anteriores de Data, si `elegible_faq` no está presente se expone como `false` en el contrato de salida.

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
contrato oficial DS v1.1
```

Al finalizar genera:

```text
output\entrega_ciencia_datos_completa.json
output\resumen_entrega_ciencia_datos.txt
```

Resultado validado con Data + Data Science:

```text
total_interacciones_procesadas: 23
total_pendientes: 0
total_elegibles_contenido: 19
total_elegibles_faq: 5
total_con_activos: 19
total_activos_generados: 35
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
| Prompt FAQ técnica y de programa | Completado |
| Prompt Caso de Éxito | Completado |
| Prompt Insight de Mejora | Completado |
| Few-Shot Learning | Completado |
| Clasificación `pregunta_programa` | Completado |
| Salidas estructuradas | Completado |
| Hashtags estructurados en LinkedIn | Completado |
| Integración con LangGraph | Completado |
| Routing de testimonios | Completado |
| Routing de feedback | Completado |
| Routing `pregunta_programa` mediante `elegible_faq` | Completado |
| Integración `elegible_faq` con Data | Validada |
| Tests específicos de prompts | Completado |
| Tests del router | Completado |
| Suite de regresión | Completado |
| Validación funcional con Gemini | Completado |
| Rate limiting / retries | Completado |
| Prueba Data → Data Science sobre paquete completo | Completado |
| Contrato oficial de salida DS v1.1 | Completado |
| Prueba funcional del contrato | Completado |

---

## 16. Pendientes inmediatos

### 1. Integración oficial con la rama de Data

La compatibilidad entre los cambios de Data y Data Science fue validada en una rama temporal de integración utilizando la rama completa:

`feature/gustavo-pregunta-programa`

Primero se verificó la suite correspondiente de Data:

```text
79 passed
124 subtests passed
0 failures
```

Posteriormente se ejecutó el flujo E2E completo con Gemini y contrato DS 1.1:

```text
23 interacciones procesadas
19 elegibles para contenido
5 elegibles para FAQ
19 interacciones con activos
35 activos generados
0 pendientes
0 errores
```

La integración funcional está validada. La incorporación definitiva del código de Data debe realizarse mediante el flujo normal del equipo cuando su PR sea integrado en `develop`.

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

El contrato de salida v1.1 deja preparado el módulo de Data Science para ser consumido por:

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
Contrato oficial de salida DS v1.1
```

Validación funcional final con Data + Data Science:

```text
23 interacciones procesadas
0 pendientes
19 elegibles para contenido
5 elegibles para FAQ
19 interacciones con activos
35 activos generados
0 errores

11 tests de routing passed
6 tests de prompts passed
79 tests de integración Data passed
124 subtests Data passed
1 prueba funcional E2E passed
```

La integración de `pregunta_programa` con `elegible_faq` fue validada utilizando la rama completa del equipo de Data, sin incorporar su implementación directamente en la rama oficial de Data Science.

Con esto, el flujo de Data Science queda preparado para integrarse con el cambio de Data mediante el proceso normal de merge hacia `develop`.
