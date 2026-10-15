# CommunityLab – Semana 4
## Validación de proveedores LLM, modelos NVIDIA NIM, trazabilidad y correcciones posteriores a auditoría

**Proyecto:** CommunityLab – Hackathon ONE G10 / Equipo 39  
**Subequipo:** Cerebro de IA – Data Science  
**Rama de trabajo:** `feature/DS-Semana4`
**Fecha:** 14 de octubre de 2026  
**Estado:** validación técnica completada; pendiente únicamente regenerar el artefacto final sobre el SHA integrado y realizar el cierre remoto cuando se autorice.

---

## 1. Objetivo

Durante Semana 4 se trabajó en cuatro frentes principales:

1. validar el uso de NVIDIA NIM como proveedor principal de IA;
2. mantener Gemini como proveedor de respaldo;
3. mejorar la trazabilidad de análisis, generación y fallback;
4. corregir hallazgos detectados por Data en la auditoría del paquete generado por Data Science.

El objetivo no fue reemplazar una solución estable por una experimental sin evidencia, sino probar alternativas de forma controlada, mantener un proveedor de respaldo y conservar la capacidad de reproducir cada ejecución mediante su SHA de código.

---

## 2. Arquitectura de proveedores

La arquitectura vigente queda:

```text
Proveedor primario:
NVIDIA NIM

Proveedor de respaldo:
Gemini
```

Esto implica que Gemini no fue eliminado del flujo.

Gemini se conserva como proveedor de respaldo porque ya existía como implementación estable del proyecto y permite recuperar la ejecución cuando NVIDIA NIM presenta un error apto para fallback.

La lógica conceptual queda:

```text
NVIDIA NIM
→ retry cuando corresponde
→ si persiste un error apto para fallback
→ Gemini
```

Se mantienen diferenciados tres conceptos:

```text
retry
fallback de proveedor
recuperación posterior
```

Un retry no debe registrarse automáticamente como fallback.

---

## 3. Evolución del proveedor principal

El flujo estable anterior del proyecto utilizaba Gemini.

Durante Semana 4 se evaluó NVIDIA NIM como proveedor principal para disponer de modelos especializados y comparar su comportamiento dentro del flujo real de CommunityLab.

La decisión final no se tomó únicamente por disponibilidad del proveedor, sino por pruebas reales de latencia, compatibilidad con salida estructurada, comportamiento por lotes y tolerancia a fallos.

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
→ no viable por timeout

DeepSeek
→ no viable en el entorno probado por timeout

Nemotron 3.5 Lightning
→ viable para rápido y estándar

Nemotron 3 Super
→ utilizado para razonamiento
```

---

## 4. Modelos evaluados dentro de NVIDIA NIM

### 4.1 Llama 3.1 y Llama 3.3

Se evaluaron:

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

El error 410 indica que el endpoint/modelo no estaba disponible para continuar la ejecución en las condiciones probadas.

Además, se incorporó reconocimiento explícito de `HTTP 410` como error apto para activar fallback de proveedor.

---

## 5. Evaluación de Gemma

Modelo evaluado:

```text
google/gemma-4-31b-it
```

Resultados reales:

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

La prueba RAW utilizó un prompt mínimo:

```text
Responde únicamente: OK
```

### Decisión

Gemma no se mantuvo como modelo estándar.

### Justificación

El timeout también apareció con una llamada RAW mínima, por lo que el comportamiento no podía atribuirse únicamente al esquema estructurado, al tamaño del lote o al prompt completo de CommunityLab.

La conclusión es específica al entorno probado: no se afirma que Gemma sea un modelo defectuoso en general.

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

El comportamiento observado no fue utilizable dentro del tiempo definido para el proyecto.

No se considera un proveedor independiente: DeepSeek fue evaluado como modelo servido mediante NVIDIA NIM.

Tampoco se afirma que esté retirado; únicamente que no fue viable en esta sesión y entorno.

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

Fue el modelo que mostró un comportamiento utilizable en las pruebas reales realizadas:

- respuesta individual correcta;
- procesamiento batch correcto;
- procesamiento completo 23/23;
- compatibilidad con el flujo estructurado;
- tiempos de respuesta dentro del timeout configurado.

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

El flujo de CommunityLab diferencia tareas por nivel de complejidad.

Nemotron Super se conserva para las tareas clasificadas como razonamiento, mientras Lightning cubre las tareas rápidas y estándar.

En la auditoría anterior se observó además:

```text
Nemotron Super:
12 activos
0 alertas

Nemotron Lightning:
14 activos
1 alerta
```

Estos valores se utilizan como evidencia operativa de esa ejecución, no como ground truth humano ni como benchmark universal entre modelos.

---

## 9. Configuración final de modelos

| Tier | Modelo |
|---|---|
| rápido | `nvidia/nemotron-3.5-lightning-30b-a3b` |
| estándar | `nvidia/nemotron-3.5-lightning-30b-a3b` |
| razonamiento | `nvidia/nemotron-3-super-120b-a12b` |

Timeout NVIDIA:

```text
15 segundos
```

Proveedor primario:

```text
NVIDIA NIM
```

Proveedor de respaldo:

```text
Gemini
```

No se modificaron nuevamente proveedor, modelos ni timeout durante la corrección posterior a la auditoría de Data.

---

## 10. Fallback y tolerancia a fallos

El flujo conserva:

```text
NVIDIA NIM
→ retry
→ error apto para fallback
→ Gemini
```

Se agregó soporte explícito para:

```text
HTTP 410
```

como causa válida de fallback.

Una ejecución histórica mostró:

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

antes de activar Gemini.

### Interpretación

Esta ejecución demuestra que el mecanismo funcionó.

No debe presentarse como el resultado final vigente.

Las ejecuciones históricas se conservan como evidencia de estabilidad y regresión, no como ground truth humano.

---

## 11. Corrección de métricas de fallback

La métrica inicial:

```text
Fallbacks en análisis: 23
```

era ambigua porque podía confundirse el número de interacciones afectadas con la cantidad real de eventos de cambio de proveedor.

Se separó en:

```text
interacciones_con_fallback_analisis
eventos_fallback_analisis
activos_con_fallback
eventos_fallback_generacion
```

### Justificación

Esto permite distinguir:

- cuántas interacciones fueron afectadas;
- cuántas veces realmente ocurrió un cambio de proveedor;
- cuántos activos fueron generados mediante fallback.

---

## 12. Paquete de trazabilidad de Semana 4

Se creó un paquete específico de auditoría/trazabilidad en:

```text
salida/auditoria_semana4/auditoria_semana4.json
```

El paquete incluye por interacción:

```text
datos de entrada
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

También conserva el resumen analítico general.

---

## 13. Recuperación del resumen analítico

En una versión inicial del paquete se conservó la trazabilidad por interacción, pero se perdió parte del resumen analítico que ya existía en el flujo.

Se corrigió reutilizando la lógica estable de:

```text
src/agentes/resumen_entrega.py
```

El resumen incluye:

```text
sentimiento_predominante
sentimientos_predominantes
distribucion_sentimientos
temas_principales
distribucion_temas
distribucion_tipos_detectados
```

### Justificación

No se duplicó la lógica del producto.

Se reutilizó la implementación existente para mantener consistencia entre la entrega normal y el paquete de auditoría.

---

## 14. Responsabilidades entre Data y Data Science

Se mantienen los límites de ownership.

Data es fuente de verdad para:

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

El flujo conceptual es:

```text
texto
→ análisis semántico
→ tipo_detectado
→ router
```

y no:

```text
tipo_original
→ forzar tipo_detectado
→ forzar routing
```

Esto evita convertir la clasificación original de Data en ground truth humano automático.

---

## 15. Auditoría recibida desde Data

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

Los hallazgos principales fueron:

### Hallazgo 1 — `int-015`

La FAQ producía una salida similar a:

```text
Una redacción breve que indique...
```

La respuesta era una instrucción sobre cómo redactar, no una respuesta final publicable.

### Hallazgo 2 — `int-011`, `int-014`, `int-018`

Data reportó estos registros con:

```text
tipo_original = testimonio
```

mientras DS había producido:

```text
tipo_detectado = comentario
```

Esto no se corrigió copiando `tipo_original`.

Se revisó la frontera semántica entre comentario y testimonio.

### Hallazgo 3 — `int-023`

Se detectó como caso casi duplicado de `int-002`.

Este punto queda reservado para Semana 5.

No se implementó deduplicación en esta tarea.

---

## 16. Corrección del prompt de FAQ

Archivo:

```text
src/agentes/prompts/preguntas_frecuentes.py
```

### Causa identificada

Los ejemplos few-shot incluían respuestas redactadas como metainstrucciones:

```text
Una redacción breve que indique...
```

```text
Una explicación breve centrada...
```

El modelo podía imitar esa estructura.

### Corrección

Se reemplazaron los ejemplos por respuestas finales y publicables.

También se añadió una regla explícita:

```text
Entrega directamente una respuesta final lista para publicar.
No describas cómo debería redactarse la respuesta ni expliques qué debería decir.
```

### Justificación

El problema no estaba en el router ni en el proveedor.

Era una señal incorrecta introducida por el propio prompt.

Por ello se corrigió la fuente del comportamiento en vez de añadir lógica posterior de parcheo.

---

## 17. Corrección de la frontera testimonio/comentario

Archivo:

```text
src/agentes/prompts/analisis.py
```

La definición previa de testimonio ya establecía:

```text
La persona relata una experiencia propia con un resultado,
transformación, hito o impacto concreto.
```

Sin embargo, el modelo tendía a interpretar como testimonio principalmente los logros más evidentes.

Se aclaró:

```text
Un testimonio no requiere necesariamente empleo, certificación
ni un logro extraordinario.
```

También se incorporaron ejemplos conceptuales de impacto:

```text
aplicar lo aprendido en una situación real
comprender algo que antes resultaba difícil
acceder a una colaboración u oportunidad
mejorar una habilidad o capacidad
```

Y se mantuvo la frontera negativa:

```text
No clasificar como testimonio un elogio, agradecimiento u opinión
si no existe una experiencia propia con resultado,
transformación o impacto concreto.
```

### Justificación

La corrección se diseñó como una regla semántica general.

No se añadieron instrucciones especiales por ID.

No se utilizó:

```text
int-011 → testimonio
int-014 → testimonio
int-018 → testimonio
```

como regla hardcodeada.

---

## 18. Validación focalizada después de los cambios

### `int-011`

Resultado:

```text
Sentimiento: positivo
Tema: empleabilidad
Tipo detectado: testimonio
Rutas:
- caso_exito
- boletin
- linkedin
```

### Razón semántica

La persona relata una experiencia propia donde el networking produjo una oportunidad concreta de colaboración.

---

### `int-014`

Resultado:

```text
Sentimiento: positivo
Tema: mentoria
Tipo detectado: testimonio
Rutas:
- caso_exito
- boletin
- linkedin
```

### Razón semántica

Es un caso fronterizo, pero existe impacto concreto: el acompañamiento permitió comprender conceptos que anteriormente resultaban difíciles.

No es únicamente una opinión positiva sobre el mentor.

---

### `int-015`

Resultado:

```text
Sentimiento: neutral
Tema: programa_hackathon
Tipo detectado: pregunta_programa
Ruta:
- preguntas_frecuentes
```

FAQ final:

> La diferencia entre las rutas de especialización debe confirmarse con la información oficial del programa, ya que la pregunta no especifica los planes de estudio ni los contenidos específicos de cada ruta.

### Razón de aceptación

La salida:

- responde directamente;
- no inventa diferencias específicas;
- remite a la fuente oficial cuando faltan datos;
- ya no reproduce una metainstrucción.

---

### `int-018`

Resultado:

```text
Sentimiento: positivo
Tema: aprendizaje
Tipo detectado: testimonio
Rutas:
- caso_exito
- boletin
- linkedin
```

### Razón semántica

La persona describe:

```text
formación terminada
+
aplicación real de lo aprendido en su trabajo
```

Existe una experiencia propia con resultado concreto.

---

## 19. Pruebas añadidas para los prompts

Se añadieron pruebas en:

```text
tests/agents/test_prompts_generadores.py
```

Estas pruebas no llaman a un modelo real.

Verifican propiedades generales del prompt:

- que las FAQ pidan una respuesta final;
- que ya no existan metainstrucciones problemáticas;
- que el concepto de testimonio incluya impactos concretos;
- que no sea obligatorio tener empleo, certificación o un logro extraordinario.

Resultado:

```text
9 passed
```

### Justificación

No se hardcodearon IDs ni resultados esperados del dataset.

El objetivo de estas pruebas es proteger la semántica del prompt, no convertir la salida histórica del LLM en verdad absoluta.

---

## 20. Nueva ejecución completa posterior a la corrección

Commit del código utilizado para esta ejecución:

```text
204b29d9870c0a0fd70f0d626efaa14479c4c4ff
```

Commit:

```text
204b29d
fix(ds): refinar prompts de analisis y FAQ
```

Resultado:

```text
Interacciones de entrada: 23
Excluidas por Data: 0
Resultados DS: 23
Activos generados: 35

Interacciones con fallback en análisis: 0
Eventos de fallback en análisis: 0
Activos con fallback: 0
Eventos de fallback en generación: 0
```

Validación adicional:

```text
Errores: 0
Fallos: 0
Inconsistencias: 0
```

---

## 21. Explicación del cambio de 26 a 35 activos

Ejecución anterior:

```text
26 activos
```

Nueva ejecución:

```text
35 activos
```

Diferencia:

```text
+9 activos
```

Los tres casos recuperados como testimonio producen tres rutas cada uno:

```text
caso_exito
boletin
linkedin
```

Por tanto:

```text
int-011 → +3
int-014 → +3
int-018 → +3

Total adicional = 9
```

Entonces:

```text
26 + 9 = 35
```

### Justificación

El aumento no se produjo por cambios en el router.

Tampoco se produjo por copiar `tipo_original`.

Se produjo porque el análisis semántico detectó correctamente tres testimonios que antes estaban en el lado conservador de la frontera `comentario/testimonio`.

---

## 22. Distribución del nuevo lote

### Tipos detectados

```text
testimonio: 8
pregunta_programa: 5
comentario: 4
pregunta_tecnica: 4
feedback: 2
```

### Sentimientos

```text
neutral: 11
positivo: 7
muy_positivo: 5
```

Sentimiento predominante:

```text
neutral
```

### Rutas

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

### Temas

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

## 23. Validación de encoding de `int-015`

Durante una inspección con PowerShell se observaron caracteres como:

```text
especializaciÃ³n
```

Se verificó el archivo con Python utilizando:

```text
encoding="utf-8"
```

y el contenido real del JSON fue correcto:

```text
especialización
```

### Conclusión

El problema observado correspondía a la representación de PowerShell, no a corrupción del JSON.

No se realizó una modificación adicional por este punto.

---

## 24. Suite completa antes de integrar cambios externos

Resultado previo:

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

El test esperaba:

```python
{"rutas": []}
```

pero el router devolvía correctamente:

```python
{
    "rutas": [],
    "tier_modelo": "rapido",
}
```

No se modificó el router para satisfacer ese test.

---

## 25. Revisión de cambios nuevos en `develop`

Después de finalizar las correcciones de DS se revisó el estado de GitHub.

Se encontraron ya fusionados:

```text
PR #30
test(datos): preparar auditoria de Semana 4 y compatibilidad con tiers
```

y:

```text
PR #31
feat(datos): auditor de coherencia semantica y auditoria de la entrega de DS
```

El PR #30 incluye la corrección del test:

Antes:

```python
assert determinar_rutas({}) == {"rutas": []}
```

Después:

```python
assert determinar_rutas({})["rutas"] == []
```

### Justificación

El campo:

```text
tier_modelo
```

forma parte válida del resultado del router.

Por tanto, el problema estaba en la expectativa desactualizada del test y no en la implementación del router.

---

## 26. Integración local de `develop`

Se hizo:

```text
git fetch origin
```

y posteriormente se integró localmente:

```text
origin/develop
→ feature/DS-Semana4
```

El merge utilizó:

```text
ort
```

y no produjo conflictos.

Archivos incorporados desde Data/Gustavo:

```text
docs/reporte_consistencia_semana4.md
scripts/auditoria_consistencia.py
tests/agents/test_consistencia_semana4.py
tests/agents/test_tolerancia_estados_manuales.py
tests/fixtures/casos_consistencia_semana4.json
tests/test_auditoria_consistencia.py
tests/test_tolerancia_persistencia_oci.py
```

No fue necesario modificar manualmente archivos de ownership de Data.

---

## 27. Suite completa después de integrar `develop`

Resultado final de la suite integrada:

```text
475 passed
132 subtests passed
0 failed
1 warning
```

Warning:

```text
DeprecationWarning en dependencia externa google-genai
```

### Conclusión

El fallo anterior quedó resuelto al incorporar la actualización oficial del test desde Data.

No se modificó el router para conseguir este resultado.

La suite integrada queda completamente verde.

---

## 28. Auditor semántico de Data/Gustavo

La integración añadió:

```text
scripts/auditoria_consistencia.py
```

junto con:

```text
tests/agents/test_consistencia_semana4.py
tests/test_auditoria_consistencia.py
tests/fixtures/casos_consistencia_semana4.json
docs/reporte_consistencia_semana4.md
```

### Importancia

El auditor de Data es independiente del paquete de trazabilidad generado por DS.

Data conserva la responsabilidad de revisar consistencia y alertas.

DS no debe presentar su propia salida de trazabilidad como auditoría oficial de Data.

---

## 29. Estado de `int-023`

`int-023` permanece fuera del alcance de esta corrección.

Es un caso casi duplicado de:

```text
int-002
```

con diferencias de acentuación.

Queda reservado para Semana 5.

No se implementó:

```text
deduplicación
normalización específica por tildes
reglas especiales para duplicados
```

---

## 30. Cambios que deliberadamente NO se realizaron

Durante esta tarea no se modificó:

```text
src/datos/*
```

Tampoco se realizó:

```text
hardcoding por ID
uso de tipo_original como ground truth
cambio del router para forzar rutas
cambio de proveedor después de la auditoría
cambio de modelos después de la auditoría
cambio del timeout después de la auditoría
deduplicación de int-023
```

### Justificación

El objetivo era corregir la causa mínima de cada hallazgo sin alterar responsabilidades entre subequipos ni introducir arquitectura nueva innecesariamente.

---

## 31. Commits relevantes de Data Science

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

También existe un commit local posterior de documentación y un merge local de `origin/develop`.

El SHA definitivo del código integrado debe registrarse después de consultar `HEAD` y regenerar la salida final.

---

## 32. Estado reproducible del paquete anterior a la integración

El paquete de 35 activos fue generado sobre:

```text
204b29d9870c0a0fd70f0d626efaa14479c4c4ff
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

Este paquete sirve como evidencia válida de la corrección de prompts.

Sin embargo, después de integrar `develop`, debe generarse una última salida sobre el nuevo SHA para que el artefacto final de Semana 4 represente exactamente el código integrado.

---

## 33. Paso final pendiente antes del cierre

Antes de cerrar y compartir el paquete definitivo con Data se debe:

```text
1. confirmar que el working tree está limpio;
2. obtener el SHA actual de feature/DS-Semana4;
3. regenerar las 23 interacciones;
4. ejecutar el auditor de consistencia incorporado desde Data;
5. confirmar activos, fallback, errores, fallos e inconsistencias;
6. registrar el nuevo SHA y los resultados en este documento;
7. realizar únicamente después el push remoto, previa confirmación.
```

No debe reutilizarse como salida final el SHA `204b29d` después de haber integrado nuevos commits desde `develop`.

---

## 34. Conclusión técnica

La Semana 4 permitió estabilizar el flujo de IA alrededor de:

```text
NVIDIA NIM como proveedor primario
Gemini como proveedor de respaldo
Nemotron Lightning para rápido/estándar
Nemotron Super para razonamiento
timeout NVIDIA de 15 s
```

La selección se basó en pruebas reales y no únicamente en preferencia de modelo.

Se descartaron configuraciones que presentaron:

```text
HTTP 410
timeouts persistentes
```

y se mantuvieron aquellas que completaron correctamente las pruebas reales.

Posteriormente, la auditoría de Data permitió identificar dos problemas semánticos:

```text
FAQ generada como metainstrucción
frontera demasiado conservadora entre comentario y testimonio
```

Ambos se corrigieron en los prompts, sin tocar el router ni utilizar `tipo_original` como ground truth.

La ejecución posterior consiguió:

```text
23/23 interacciones
35 activos
0 fallback
0 errores
0 fallos
0 inconsistencias
```

y la integración con los cambios recientes de Data dejó la suite completa en:

```text
475 passed
132 subtests passed
0 failed
1 warning externo
```

El único paso técnico pendiente es regenerar el artefacto definitivo sobre el SHA integrado actual y registrar esos datos finales antes de publicar la rama.
