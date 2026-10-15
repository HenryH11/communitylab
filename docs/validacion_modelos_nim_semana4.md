# CommunityLab – Semana 4
## Validación de modelos NVIDIA NIM, trazabilidad y correcciones posteriores a auditoría

**Proyecto:** CommunityLab – Hackathon ONE G10 / Equipo 39  
**Subequipo:** Cerebro de IA – Data Science  
**Rama:** `feature/DS-Semana4`  
**Fecha:** 14 de octubre de 2026  
**Versión del paquete de auditoría:** `1.2`

---

## 1. Propósito

Este documento registra la validación técnica realizada por Data Science durante Semana 4, incluyendo:

- validación de modelos NVIDIA NIM;
- fallback NVIDIA → Gemini;
- trazabilidad por proveedor, modelo y tier;
- paquete reproducible para auditoría;
- correcciones realizadas a partir de la auditoría de Data;
- nueva ejecución completa del lote de 23 interacciones.

La auditoría oficial corresponde al equipo de Data. Data Science entrega el paquete de evidencia y trazabilidad necesario para esa revisión.

---

## 2. Configuración vigente de IA

Proveedor primario:

```text
NVIDIA NIM
```

Proveedor de respaldo:

```text
Gemini
```

Modelos:

| Tier | Modelo |
|---|---|
| rápido | `nvidia/nemotron-3.5-lightning-30b-a3b` |
| estándar | `nvidia/nemotron-3.5-lightning-30b-a3b` |
| razonamiento | `nvidia/nemotron-3-super-120b-a12b` |

Timeout NVIDIA:

```text
15 segundos
```

Se mantienen diferenciados:

```text
retry
fallback de proveedor
recuperación posterior
```

---

## 3. Evidencia de selección de modelos

### 3.1 Llama 3.1 / 3.3

Los modelos:

```text
meta/llama-3.1-8b-instruct
meta/llama-3.3-70b-instruct
```

devolvieron `HTTP 410 Gone` en llamadas reales a NVIDIA NIM.

Por ello se añadió `HTTP 410` como causa válida para activar fallback de proveedor.

### 3.2 Gemma

Modelo evaluado:

```text
google/gemma-4-31b-it
```

Resultados observados:

```text
Batch, timeout 15 s
→ OpenAITimeoutError
→ 15.25 s

Individual, timeout 15 s
→ OpenAITimeoutError
→ 15.26 s

RAW mínimo, timeout 30 s
→ OpenAITimeoutError
→ 30.36 s
```

No resultó viable en el entorno probado.

### 3.3 DeepSeek dentro de NVIDIA NIM

Modelo evaluado:

```text
deepseek-ai/deepseek-v4.1-flash
```

Resultados:

```text
Análisis estructurado, timeout 15 s
→ OpenAITimeoutError
→ 15.25 s

RAW, timeout 30 s
→ OpenAITimeoutError
→ 30.25 s
```

No se afirma que el modelo esté retirado. Solo se concluye que no fue viable en el entorno probado durante esta sesión.

### 3.4 Nemotron 3.5 Lightning

Prueba individual estructurada:

```text
Resultado: OK
Tiempo: 1.24 s
```

Lote de 10 mensajes:

```text
10 enviados
10 recibidos
Tiempo: 8.56 s
```

Dataset completo de análisis:

```text
Lote 1: 10/10 | 7.63 s
Lote 2: 10/10 | 9.04 s
Lote 3: 3/3   | 10.09 s

Total: 23/23
```

Esta evidencia sustentó su uso para los tiers rápido y estándar.

---

## 4. Fallback y tolerancia a fallos

El flujo mantiene:

```text
NVIDIA NIM
→ error apto para fallback
→ Gemini
```

Una ejecución anterior permitió comprobar el mecanismo real:

```text
Interacciones de entrada: 23
Resultados DS: 23
Interacciones con fallback en análisis: 23
Eventos de fallback en análisis: 4
Activos con fallback: 0
Eventos de fallback en generación: 0
```

La observabilidad registró:

```text
12 llm_error
```

consistentes con:

```text
4 lotes × 3 intentos NVIDIA
```

antes de activar Gemini.

Esta ejecución se conserva únicamente como evidencia histórica de funcionamiento del fallback.

---

## 5. Métricas de fallback

La auditoría diferencia:

```text
interacciones_con_fallback_analisis
eventos_fallback_analisis
activos_con_fallback
eventos_fallback_generacion
```

Esto evita confundir:

- interacciones afectadas por fallback;
- eventos reales de cambio de proveedor.

---

## 6. Paquete de auditoría v1.2

El paquete mantiene el resumen analítico y la trazabilidad operativa.

### Resumen analítico

```text
sentimiento_predominante
sentimientos_predominantes
distribucion_sentimientos
temas_principales
distribucion_temas
distribucion_tipos_detectados
```

### Trazabilidad

Por análisis y activo se conserva:

```text
proveedor
modelo
tier
fallback
motivo_fallback
errores
fallos
SHA
```

El artefacto sigue siendo:

```text
salida/auditoria_semana4/auditoria_semana4.json
```

`salida/` permanece ignorada por Git y el JSON se comparte directamente como artefacto de ejecución.

---

## 7. Auditoría de Data recibida

Data revisó el paquete anterior generado sobre:

```text
4331b6eb866b05062e189a4ee937c72531771513
```

Resultado reportado:

```text
26 activos
0 fallback
1 activo con alerta
```

Hallazgos relevantes para Data Science:

1. `int-015` produjo una FAQ redactada como metainstrucción y no como respuesta publicable.
2. `int-011`, `int-014` e `int-018` fueron detectados como `comentario`, aunque sus textos describen experiencias personales con impactos concretos.
3. `int-023`, prácticamente duplicado de `int-002`, queda reservado para Semana 5.

No se utilizó `tipo_original` como ground truth automático para corregir estos casos.

---

## 8. Diagnóstico de `int-015`

Archivo revisado:

```text
src/agentes/prompts/preguntas_frecuentes.py
```

La causa estaba en los ejemplos few-shot del prompt.

El ejemplo incluía respuestas del tipo:

```text
Una redacción breve que indique que...
```

y:

```text
Una explicación breve centrada en...
```

Estas frases son metainstrucciones, no respuestas finales.

Aunque el prompt indicaba posteriormente que los ejemplos no debían copiarse literalmente, el modelo podía imitar su estructura.

### Corrección

Los ejemplos se transformaron en respuestas finales y publicables.

Además se añadió una regla explícita:

```text
Entrega directamente una respuesta final lista para publicar.
No describas cómo debería redactarse la respuesta ni expliques qué debería decir.
```

No fue necesario implementar regeneración automática ni validadores adicionales.

---

## 9. Diagnóstico de testimonio vs comentario

Archivo revisado:

```text
src/agentes/prompts/analisis.py
```

La definición previa ya indicaba:

```text
La persona relata una experiencia propia con un resultado,
transformación, hito o impacto concreto.
```

Sin embargo, el modelo estaba siendo conservador cuando el impacto no era un logro extraordinario como empleo o cambio profesional.

Se realizó una aclaración semántica general:

```text
Un testimonio no requiere necesariamente empleo, certificación
ni un logro extraordinario.
```

También se aclaró que puede existir cuando la persona describe impactos concretos como:

- aplicar lo aprendido;
- comprender algo que antes resultaba difícil;
- acceder a una colaboración u oportunidad;
- mejorar una habilidad o capacidad.

Se conserva la frontera negativa:

```text
Un elogio, agradecimiento u opinión sin experiencia propia
con resultado, transformación o impacto concreto
no debe clasificarse como testimonio.
```

No se añadieron reglas especiales por ID.

---

## 10. Principios preservados

Durante la corrección:

- no se modificó `src/datos/*`;
- no se modificó el router para copiar la clasificación de Data;
- `tipo_original` no se envía al LLM;
- `tipo_original` no se usa como ground truth automático;
- no se modificaron modelos;
- no se modificó timeout;
- no se modificó fallback;
- no se implementó deduplicación;
- `int-023` quedó fuera de alcance.

El flujo continúa siendo:

```text
texto
→ análisis semántico
→ tipo_detectado
→ router
```

y no:

```text
tipo_original
→ forzar routing
```

---

## 11. Validación focalizada después del cambio

### `int-011`

```text
Sentimiento: positivo
Tipo detectado: testimonio
Rutas:
- caso_exito
- boletin
- linkedin
```

La decisión es coherente con una experiencia propia donde el networking produjo una oportunidad concreta de colaboración.

### `int-014`

```text
Sentimiento: positivo
Tema: mentoria
Tipo detectado: testimonio
Rutas:
- caso_exito
- boletin
- linkedin
```

Es el caso más fronterizo, pero expresa un impacto concreto: el acompañamiento permitió comprender conceptos que anteriormente resultaban difíciles.

### `int-015`

```text
Tipo detectado: pregunta_programa
Ruta:
- preguntas_frecuentes
```

FAQ generada:

> La diferencia entre las rutas de especialización debe confirmarse con la información oficial del programa, ya que la pregunta no especifica los planes de estudio ni los contenidos específicos de cada ruta.

La salida ya es final, prudente y publicable.

### `int-018`

```text
Sentimiento: positivo
Tema: aprendizaje
Tipo detectado: testimonio
Rutas:
- caso_exito
- boletin
- linkedin
```

La persona describe formación terminada y aplicación real de lo aprendido en su trabajo.

---

## 12. Pruebas de regresión

Se añadieron pruebas orientadas a las propiedades generales de los prompts.

No se hardcodearon IDs para obligar al modelo a coincidir con `tipo_original`.

Las pruebas verifican:

- que el prompt de FAQ use respuestas finales;
- que no conserve metainstrucciones como `"Una redacción breve que indique..."`;
- que la definición de testimonio contemple impactos personales concretos sin requerir logros extraordinarios.

Prueba focalizada del prompt:

```text
9 passed
```

La batería relevante posterior quedó verde.

---

## 13. Nueva ejecución completa

Commit exacto del código que produjo el nuevo JSON:

```text
204b29d9870c0a0fd70f0d626efaa14479c4c4ff
```

Commit:

```text
204b29d
fix(ds): refinar prompts de analisis y FAQ
```

Rama:

```text
feature/DS-Semana4
```

Resultado:

```text
Auditoría Semana 4 generada correctamente.

Working tree limpio: True
Interacciones de entrada: 23
Excluidas por Data: 0
Resultados DS: 23
Activos generados: 35

Interacciones con fallback en análisis: 0
Eventos de fallback en análisis: 0

Activos con fallback: 0
Eventos de fallback en generación: 0
```

Validación adicional del JSON:

```text
Errores: 0
Fallos: 0
Inconsistencias: 0
```

---

## 14. Comparación contra la ejecución anterior

Ejecución anterior:

```text
23 interacciones
26 activos
```

Nueva ejecución:

```text
23 interacciones
35 activos
```

Diferencia:

```text
+9 activos
```

La diferencia se explica completamente por:

```text
int-011
comentario → testimonio
0 activos → 3 activos

int-014
comentario → testimonio
0 activos → 3 activos

int-018
comentario → testimonio
0 activos → 3 activos
```

Por tanto:

```text
26 + 3 + 3 + 3 = 35
```

No se produjo un aumento por cambio del router ni por uso de `tipo_original`.

---

## 15. Distribución de rutas y resultados

Distribución de rutas:

```text
caso_exito: 8
boletin: 8
linkedin: 8
preguntas_frecuentes: 9
insight_mejora: 2
```

Total:

```text
35 activos
```

Distribución de tipos detectados:

```text
testimonio: 8
pregunta_programa: 5
comentario: 4
pregunta_tecnica: 4
feedback: 2
```

Distribución de sentimientos:

```text
neutral: 11
positivo: 7
muy_positivo: 5
```

Sentimiento predominante:

```text
neutral
```

Temas principales:

```text
programacion: 6
empleabilidad: 5
programa_hackathon: 4
aprendizaje: 3
comunidad: 2
mentoria: 2
certificacion: 1
```

---

## 16. Suite completa posterior

Resultado:

```text
441 passed
132 subtests passed
1 failed
1 warning
```

Único fallo:

```text
tests/agents/test_tolerancia_estados_manuales.py::
test_enrutador_tolera_estado_sin_campos
```

El test espera:

```python
{"rutas": []}
```

mientras el router actual devuelve:

```python
{
    "rutas": [],
    "tier_modelo": "rapido",
}
```

Este fallo ya existía antes de la corrección de prompts y no fue introducido por `204b29d`.

El warning corresponde a una advertencia deprecada en una dependencia externa de `google-genai`.

---

## 17. Ownership de Data

No se modificó lógica dentro de:

```text
src/datos/*
```

Data continúa siendo fuente de verdad para:

```text
score_relevancia
tipo_original
elegible_contenido
elegible_faq
```

Data Science:

- conserva `tipo_original`;
- genera `tipo_detectado`;
- no envía `tipo_original` al LLM;
- no utiliza ejecuciones históricas como ground truth humano.

---

## 18. Commits relevantes de Data Science

```text
a21e646
feat(ds): agregar exportador de auditoria Semana 4
```

```text
dcb464d
fix(ds): permitir ejecutar runner de auditoria desde scripts
```

```text
abaaa87
fix(ds): actualizar modelos NIM y fallback ante 410
```

```text
ed435c1
fix(ds): aclarar metricas de fallback en auditoria
```

```text
65e64a3
fix(ds): reemplazar modelo estandar y ajustar timeout NIM
```

```text
c8f4e1c
docs(ds): documentar validacion real de modelos NIM Semana 4
```

```text
4331b6e
fix(ds): recuperar resumen analitico en auditoria Semana 4
```

```text
d1b2ba3
docs(ds): actualizar evidencia final de auditoria Semana 4
```

```text
204b29d
fix(ds): refinar prompts de analisis y FAQ
```

---

## 19. Artefacto vigente para Data

Archivo:

```text
salida/auditoria_semana4/auditoria_semana4.json
```

SHA exacto del código que lo produjo:

```text
204b29d9870c0a0fd70f0d626efaa14479c4c4ff
```

Resultado vigente:

```text
23 interacciones
35 activos
0 fallback de análisis
0 fallback de generación
0 errores
0 fallos
0 inconsistencias
```

Este JSON reemplaza al paquete anterior de 26 activos para una nueva revisión de Data.

---

## 20. Pendiente separado

`int-023` permanece reservado para Semana 5.

No resolver dentro de esta tarea:

```text
deduplicación
normalización específica por tildes
reglas especiales para duplicados
```

---

## 21. Estado de cierre técnico

La corrección posterior a auditoría consiguió:

```text
int-015 → FAQ publicable
int-011 → testimonio
int-014 → testimonio
int-018 → testimonio
```

sin utilizar `tipo_original` como ground truth y sin modificar el router.

La ejecución completa produjo:

```text
35 activos
0 errores
0 fallos
0 inconsistencias
```

Antes del cierre definitivo queda revisar e incorporar, si corresponde, cambios externos recientemente integrados en `develop`, volver a ejecutar la suite y confirmar que no introducen regresiones.
