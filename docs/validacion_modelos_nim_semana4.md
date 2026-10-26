# CommunityLab – Semana 4
## Validación técnica de proveedores LLM, modelos NVIDIA NIM y trazabilidad de Data Science

**Proyecto:** CommunityLab – Hackathon ONE G10 / Equipo 39  
**Subequipo:** Cerebro de IA – Data Science  
**Rama:** `feature/DS-Semana4`
**Fecha:** 14 de octubre de 2026  
**Estado técnico:** validación local completada; paquete de trazabilidad final preparado para revisión de Data.

---

## 1. Objetivo

Durante Semana 4, Data Science trabajó en cuatro frentes:

1. validar NVIDIA NIM como proveedor principal de IA;
2. mantener Gemini como proveedor de respaldo;
3. mejorar la trazabilidad de análisis, generación y fallback;
4. corregir comportamientos detectados a partir de la retroalimentación recibida desde Data.

Data Science no realiza la auditoría oficial. Su responsabilidad en esta etapa es producir, validar técnicamente y documentar las salidas que Data utilizará posteriormente para su revisión.

---

## 2. Arquitectura de proveedores

La configuración vigente queda:

```text
Proveedor primario:
NVIDIA NIM

Proveedor de respaldo:
Gemini
```

Gemini no fue eliminado del flujo.

Se conserva como respaldo porque ya existía como implementación estable del proyecto y permite recuperar una ejecución cuando NVIDIA NIM presenta un error apto para cambio de proveedor.

El flujo conceptual es:

```text
NVIDIA NIM
→ retry cuando corresponde
→ si persiste un error apto para fallback
→ Gemini
```

Se mantienen separados:

```text
retry
fallback de proveedor
recuperación posterior
```

Un retry no equivale automáticamente a fallback.

---

## 3. Evolución del proveedor principal

El flujo estable anterior del proyecto utilizaba Gemini.

Durante Semana 4 se evaluó NVIDIA NIM como proveedor principal mediante pruebas reales de:

- latencia;
- salida estructurada;
- procesamiento por lotes;
- comportamiento sobre el dataset completo;
- tolerancia a fallos.

La evolución fue:

```text
Gemini
→ se conserva como respaldo estable

NVIDIA NIM
→ pasa a proveedor primario

Dentro de NVIDIA NIM:

Llama 3.1 / 3.3
→ no utilizables por HTTP 410

Gemma
→ no viable en el entorno probado por timeout

DeepSeek
→ no viable en el entorno probado por timeout

Nemotron 3.5 Lightning
→ viable para rápido y estándar

Nemotron 3 Super
→ utilizado para razonamiento
```

---

## 4. Evaluación de Llama 3.1 y Llama 3.3

Modelos evaluados:

```text
meta/llama-3.1-8b-instruct
meta/llama-3.3-70b-instruct
```

Las llamadas reales devolvieron:

```text
HTTP 410 Gone
```

### Decisión

No se mantuvieron como modelos activos.

### Justificación

El endpoint/modelo no estaba disponible para continuar las ejecuciones en las condiciones probadas.

Además, se incorporó reconocimiento explícito de `HTTP 410` como error apto para fallback de proveedor.

---

## 5. Evaluación de Gemma

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

La prueba RAW utilizó únicamente:

```text
Responde únicamente: OK
```

### Decisión

Gemma no se mantuvo como modelo estándar.

### Justificación

El timeout también apareció con una llamada RAW mínima, por lo que el problema observado no podía atribuirse únicamente al esquema estructurado, al tamaño del lote o al prompt completo de CommunityLab.

La conclusión aplica únicamente al entorno probado.

---

## 6. Evaluación de DeepSeek dentro de NVIDIA NIM

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

### Decisión

DeepSeek no se mantuvo como modelo activo.

### Justificación

No respondió dentro del tiempo utilizable para el proyecto en el entorno probado.

DeepSeek fue evaluado como modelo servido mediante NVIDIA NIM, no como proveedor independiente.

---

## 7. Validación de Nemotron 3.5 Lightning

Modelo:

```text
nvidia/nemotron-3.5-lightning-30b-a3b
```

### Prueba individual estructurada

```text
Resultado: OK
Tiempo: 1.24 s
```

Salida observada:

```text
sentimiento: muy_positivo
tema_principal: empleabilidad
subtema: primer trabajo analista datos
tipo_detectado: testimonio
```

### Lote de 10 mensajes

```text
10 enviados
10 recibidos
Tiempo: 8.56 s
```

### Dataset completo de análisis

```text
Lote 1: 10/10 | 7.63 s
Lote 2: 10/10 | 9.04 s
Lote 3: 3/3   | 10.09 s

Total: 23/23
```

### Decisión

Nemotron Lightning quedó configurado para:

```text
tier rápido
tier estándar
```

### Justificación

Fue el modelo que mostró comportamiento utilizable en las pruebas reales:

- respuesta individual correcta;
- procesamiento batch correcto;
- procesamiento completo 23/23;
- compatibilidad con salida estructurada;
- tiempos compatibles con el timeout configurado.

---

## 8. Nemotron Super para razonamiento

Modelo:

```text
nvidia/nemotron-3-super-120b-a12b
```

Se mantiene para:

```text
tier razonamiento
```

### Justificación

CommunityLab diferencia tareas por nivel de complejidad.

Nemotron Super se conserva para tareas de razonamiento, mientras Lightning cubre tareas rápidas y estándar.

Las distribuciones observadas por modelo sirven como evidencia operativa de cada ejecución, no como ground truth ni como benchmark universal.

---

## 9. Configuración final de IA

| Tier | Modelo |
|---|---|
| rápido | `nvidia/nemotron-3.5-lightning-30b-a3b` |
| estándar | `nvidia/nemotron-3.5-lightning-30b-a3b` |
| razonamiento | `nvidia/nemotron-3-super-120b-a12b` |

```text
Proveedor primario: NVIDIA NIM
Proveedor de respaldo: Gemini
Timeout NVIDIA: 15 segundos
```

Durante las correcciones posteriores no se modificaron nuevamente proveedor, modelos ni timeout.

---

## 10. Fallback y tolerancia a fallos

Se añadió soporte explícito para reconocer:

```text
HTTP 410
```

como causa válida de fallback de proveedor.

Una ejecución histórica permitió comprobar el mecanismo:

```text
Interacciones de entrada: 23
Resultados DS: 23
Interacciones con fallback en análisis: 23
Eventos de fallback en análisis: 4
Activos con fallback: 0
Eventos de fallback en generación: 0
```

También se observaron:

```text
12 llm_error
```

consistentes con:

```text
4 lotes × 3 intentos NVIDIA
```

antes de utilizar Gemini.

Esta ejecución se conserva como evidencia histórica del funcionamiento del mecanismo.

No representa el resultado final vigente.

---

## 11. Métricas de fallback

Las métricas se separaron en:

```text
interacciones_con_fallback_analisis
eventos_fallback_analisis
activos_con_fallback
eventos_fallback_generacion
```

### Justificación

Esto evita confundir:

- cantidad de interacciones afectadas;
- cantidad real de cambios de proveedor;
- cantidad de activos generados mediante fallback.

---

## 12. Paquete de trazabilidad de Data Science

El artefacto principal generado por DS es:

```text
salida/auditoria_semana4/auditoria_semana4.json
```

Aunque el nombre del archivo conserva `auditoria_semana4` por compatibilidad con la implementación existente, para Data Science este archivo debe entenderse como un **paquete de trazabilidad y evidencia de ejecución**.

Contiene:

```text
entrada
decisiones provenientes de Data
análisis DS
sentimiento
tema
subtema
tipo_detectado
rutas
activos
proveedor
modelo
tier
fallback
motivo_fallback
errores
fallos
SHA
```

La carpeta `salida/` está ignorada por Git y el archivo se comparte directamente como artefacto de ejecución.

---

## 13. Recuperación del resumen analítico

Una versión inicial del paquete conservaba la trazabilidad por interacción, pero había perdido parte del resumen analítico estable.

Se recuperó reutilizando:

```text
src/agentes/resumen_entrega.py
```

El paquete vuelve a incluir:

```text
sentimiento_predominante
sentimientos_predominantes
distribucion_sentimientos
temas_principales
distribucion_temas
distribucion_tipos_detectados
```

### Justificación

Se reutilizó la lógica estable del producto en lugar de duplicarla.

---

## 14. Responsabilidades entre Data y Data Science

Data continúa siendo fuente de verdad para:

```text
score_relevancia
tipo_original
elegible_contenido
elegible_faq
```

Data Science:

```text
conserva tipo_original
produce tipo_detectado
```

`tipo_original` no se envía al LLM.

Tampoco se utiliza como ground truth automático.

El flujo es:

```text
texto
→ análisis semántico
→ tipo_detectado
→ router
```

No:

```text
tipo_original
→ forzar tipo_detectado
→ forzar routing
```

---

## 15. Retroalimentación recibida desde Data

Data revisó una entrega anterior generada sobre:

```text
4331b6eb866b05062e189a4ee937c72531771513
```

En esa revisión se reportaron tres puntos relevantes para DS:

### `int-015`

La FAQ se generaba como una metainstrucción:

```text
Una redacción breve que indique...
```

en lugar de producir una respuesta final publicable.

### `int-011`, `int-014`, `int-018`

Data tenía:

```text
tipo_original = testimonio
```

mientras DS había producido:

```text
tipo_detectado = comentario
```

Esto motivó revisar la frontera semántica entre ambos tipos.

No se corrigió copiando `tipo_original`.

### `int-023`

Caso casi duplicado de `int-002`.

Se dejó reservado para Semana 5.

---

## 16. Corrección del prompt de FAQ

Archivo:

```text
src/agentes/prompts/preguntas_frecuentes.py
```

### Causa

Los ejemplos few-shot incluían respuestas redactadas como instrucciones:

```text
Una redacción breve que indique...
Una explicación breve centrada...
```

### Cambio

Se reemplazaron por respuestas finales y se añadió:

```text
Entrega directamente una respuesta final lista para publicar.
No describas cómo debería redactarse la respuesta ni expliques qué debería decir.
```

### Justificación

La causa estaba en el prompt.

No era necesario modificar router, proveedor ni arquitectura.

---

## 17. Refinamiento testimonio / comentario

Archivo:

```text
src/agentes/prompts/analisis.py
```

La definición previa ya indicaba:

```text
La persona relata una experiencia propia con un resultado,
transformación, hito o impacto concreto.
```

Se aclaró:

```text
Un testimonio no requiere necesariamente empleo, certificación
ni un logro extraordinario.
```

También se añadieron ejemplos conceptuales:

```text
aplicar lo aprendido en una situación real
comprender algo que antes resultaba difícil
acceder a una colaboración u oportunidad
mejorar una habilidad o capacidad
```

Y se mantuvo la frontera negativa:

```text
No clasificar como testimonio un elogio, agradecimiento u opinión
si no existe experiencia propia con resultado,
transformación o impacto concreto.
```

### Justificación

La mejora es semántica y general.

No se añadieron reglas especiales por ID.

---

## 18. Validación focalizada de los casos revisados

### `int-011`

```text
Sentimiento: positivo
Tema: empleabilidad
Tipo detectado: testimonio
Rutas:
- caso_exito
- boletin
- linkedin
```

La persona relata una experiencia propia donde el networking produjo una oportunidad concreta de colaboración.

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

Existe impacto concreto: el acompañamiento permitió comprender conceptos anteriormente difíciles.

### `int-015`

```text
Sentimiento: neutral
Tema: programa_hackathon
Tipo detectado: pregunta_programa
Ruta:
- preguntas_frecuentes
```

Respuesta generada:

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

Existe formación completada y aplicación real de lo aprendido.

---

## 19. Pruebas de regresión de prompts

Se añadieron pruebas en:

```text
tests/agents/test_prompts_generadores.py
```

Verifican propiedades generales:

- que FAQ pida respuestas finales;
- que desaparezcan metainstrucciones problemáticas;
- que testimonio contemple impactos concretos;
- que no requiera logros extraordinarios.

Resultado focalizado:

```text
9 passed
```

No se hardcodearon IDs ni resultados concretos del dataset.

---

## 20. Primera ejecución completa posterior a la corrección

SHA:

```text
204b29d9870c0a0fd70f0d626efaa14479c4c4ff
```

Resultado:

```text
23 interacciones
0 excluidas por Data
23 resultados DS
35 activos

0 fallback de análisis
0 fallback de generación
0 errores
0 fallos
0 inconsistencias
```

---

## 21. Explicación del cambio de 26 a 35 activos

La ejecución anterior generaba:

```text
26 activos
```

Después del refinamiento:

```text
35 activos
```

Los tres casos recuperados como testimonio generan tres rutas cada uno:

```text
int-011 → +3
int-014 → +3
int-018 → +3
```

Por tanto:

```text
26 + 9 = 35
```

El aumento no se produjo por cambios en el router ni por uso de `tipo_original`.

---

## 22. Distribución observada

Tipos detectados:

```text
testimonio: 8
pregunta_programa: 5
comentario: 4
pregunta_tecnica: 4
feedback: 2
```

Sentimientos:

```text
neutral: 11
positivo: 7
muy_positivo: 5
```

Rutas:

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

---

## 23. Verificación de encoding

PowerShell mostró temporalmente textos como:

```text
especializaciÃ³n
```

Se verificó el JSON con Python utilizando UTF-8 y el contenido real era correcto:

```text
especialización
```

No fue necesario realizar cambios por este punto.

---

## 24. Integración de cambios recientes de `develop`

Después de completar las correcciones de DS se revisaron cambios nuevos ya integrados en `develop`.

Entre ellos se encontraba la actualización del test de tolerancia del router.

Antes:

```python
assert determinar_rutas({}) == {"rutas": []}
```

Después:

```python
assert determinar_rutas({})["rutas"] == []
```

### Justificación

`tier_modelo` es un campo válido del router.

El fallo estaba en una expectativa desactualizada del test, no en la implementación del router.

Por ello no se modificó el router.

---

## 25. Merge local de `origin/develop`

Se integró localmente:

```text
origin/develop
→ feature/DS-Semana4
```

El merge utilizó la estrategia:

```text
ort
```

y no produjo conflictos.

Se incorporaron pruebas y archivos de soporte provenientes de otros subequipos sin modificar manualmente su lógica.

---

## 26. Suite completa integrada

Resultado:

```text
475 passed
132 subtests passed
0 failed
1 warning
```

El warning corresponde a una deprecación externa de `google-genai`.

### Conclusión

La suite integrada quedó completamente verde.

---

## 27. Ejecución final vigente

El paquete final fue regenerado después de integrar `develop` y consolidar la documentación.

SHA exacto del código:

```text
8f32be8d8ef51d41a04b251ec9e719b258e94f88
```

Rama:

```text
feature/DS-Semana4
```

Resultado:

```text
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

Artefacto final de trazabilidad:

```text
salida/auditoria_semana4/auditoria_semana4.json
```

Este archivo reemplaza la salida anterior para la siguiente revisión de Data.

---

## 28. Estado de `int-023`

`int-023` permanece reservado para Semana 5.

No se implementó en esta tarea:

```text
deduplicación
normalización específica por tildes
reglas especiales para duplicados
```

---

## 29. Cambios que deliberadamente no se realizaron

No se modificó:

```text
src/datos/*
```

Tampoco se realizó:

```text
hardcoding por ID
uso de tipo_original como ground truth automático
cambio del router para forzar rutas
nuevo cambio de proveedor tras la revisión
nuevo cambio de modelos tras la revisión
nuevo cambio de timeout tras la revisión
deduplicación de int-023
```

### Justificación

El objetivo fue corregir las causas mínimas necesarias sin alterar ownership ni introducir arquitectura nueva sin evidencia.

---

## 30. Commits relevantes de Data Science

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

```text
8f32be8
docs(ds): consolidar validacion tecnica de Semana 4
```

---

## 31. Archivo que debe recibir Data

Archivo principal:

```text
salida/auditoria_semana4/auditoria_semana4.json
```

SHA del código que produjo esa salida:

```text
8f32be8d8ef51d41a04b251ec9e719b258e94f88
```

Resultado:

```text
23 interacciones
35 activos
0 fallback de análisis
0 fallback de generación
0 errores
0 fallos
0 inconsistencias
```

Aunque el nombre del archivo mantiene `auditoria_semana4.json`, la responsabilidad de DS es entregar la trazabilidad. La revisión o auditoría posterior corresponde al equipo de Data.

---

## 32. Qué debe revisar Data

Especialmente:

```text
int-011
int-014
int-015
int-018
```

junto con el nuevo resultado global:

```text
35 activos
```

`int-023` queda explícitamente fuera de este cierre y reservado para Semana 5.

---

## 33. Conclusión

Semana 4 deja una configuración estable:

```text
NVIDIA NIM como proveedor primario
Gemini como proveedor de respaldo
Nemotron Lightning para rápido/estándar
Nemotron Super para razonamiento
timeout NVIDIA de 15 s
```

La selección se sustentó en pruebas reales.

Los problemas observados durante la evaluación fueron:

```text
Llama → HTTP 410
Gemma → timeout
DeepSeek dentro de NIM → timeout
```

La retroalimentación de Data permitió corregir:

```text
FAQ redactada como metainstrucción
frontera demasiado conservadora entre comentario y testimonio
```

sin alterar el router ni utilizar `tipo_original` como ground truth.

La integración final deja:

```text
475 passed
132 subtests passed
0 failed
```

y el paquete de trazabilidad final está asociado a:

```text
8f32be8d8ef51d41a04b251ec9e719b258e94f88
```

con:

```text
23/23 interacciones
35 activos
0 fallback
0 errores
0 fallos
0 inconsistencias
```

Este es el estado técnico que Data Science entrega para la siguiente revisión del equipo de Data.

---

## Cierre final de validación de Semana 4

La validación final de Data Science se realizó sobre:

```text
Rama: feature/DS-Semana4
SHA: 5162e6108b4e5ef96d91804c3193b955a0ced69b
Working tree limpio: sí
```

### Resultado de pruebas

Suite completa:

```text
485 passed
132 subtests passed
1 warning
0 failed
```

Pruebas focalizadas de prompts:

```text
19 passed
```

También se verificó que no existan reglas específicas asociadas a los IDs
de las interacciones revisadas. Los ajustes realizados corresponden a reglas
generales de clasificación, fidelidad semántica y generación, acompañadas por
ejemplos de referencia en los prompts.

### Ejecución final sobre el dataset

```text
Interacciones de entrada: 23
Excluidas por Data: 0
Resultados DS: 23
Activos generados: 35

Interacciones con fallback en análisis: 0
Eventos de fallback en análisis: 0
Activos con fallback: 0
Eventos de fallback en generación: 0

Errores: 0
Fallos: 0
Inconsistencias: 0
```

Configuración utilizada:

```text
Proveedor principal: NVIDIA NIM
Proveedor de respaldo: Gemini

rápido:
nvidia/nemotron-3.5-lightning-30b-a3b

estándar:
nvidia/nemotron-3.5-lightning-30b-a3b

razonamiento:
nvidia/nemotron-3-super-120b-a12b

Timeout NVIDIA: 15 s
```

### Ajustes semánticos finales

La calibración final reforzó reglas generales para:

- preservar cantidades, rangos y comparadores como `menos de`, `más de`
  y `al menos`;
- evitar aumentar causalidad, certeza, dificultad o intensidad respecto
  al mensaje original;
- conservar correctamente estados como `seleccionado` frente a
  `contratado`;
- diferenciar `programa_hackathon`, `aprendizaje`, `plataforma`,
  `programacion` y `datos_ia`;
- evitar completar con conocimiento general información institucional
  que debe provenir de fuentes oficiales del programa;
- mantener precisión terminológica en respuestas técnicas;
- generar FAQ directamente publicables, sin instrucciones internas ni
  metacomentarios;
- mantener la información original como fuente factual principal para
  los activos generados.

Los casos señalados durante la revisión de Data en Semana 4 fueron
revisados nuevamente. Las divergencias de clasificación y generación
detectadas en `int-011`, `int-014`, `int-015` e `int-018`, junto con los
casos relacionados encontrados durante la revisión semántica de DS,
quedaron corregidos mediante reglas generales y no mediante condiciones
específicas por interacción.

### Caso reservado para Semana 5

`int-023` continúa intencionalmente sin deduplicación en Semana 4.

Es un caso casi duplicado de `int-002`. La detección y tratamiento de
duplicados se mantiene como trabajo de Semana 5 y no constituye un
bloqueador del cierre actual.

### Commits finales de calibración

```text
7cc4e91  refactor(ds): mejorar prompts y fidelidad semantica
99f1905  fix(ds): reforzar fidelidad semantica de prompts
5162e61  fix(ds): cerrar calibracion final de prompts
```

El archivo:

```text
salida/auditoria_semana4/auditoria_semana4.json
```

conserva ese nombre por compatibilidad, pero desde Data Science se entrega
como paquete de trazabilidad y evidencia de ejecución. La auditoría o revisión
posterior de estos resultados corresponde al equipo de Data.
