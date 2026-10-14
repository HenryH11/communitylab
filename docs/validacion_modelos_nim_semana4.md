# CommunityLab – Semana 4
## Validación de modelos NVIDIA NIM y tolerancia a fallos

**Proyecto:** CommunityLab – Hackathon ONE G10 / Equipo 39  
**Subequipo:** Cerebro de IA – Data Science  
**Rama:** `feature/DS-Semana4`  
**Fecha:** 14 de octubre de 2026

---

## 1. Propósito

Este documento registra la validación técnica realizada sobre los modelos usados por CommunityLab en NVIDIA NIM, los cambios aplicados durante Semana 4 y la evidencia obtenida mediante pruebas reales y automatizadas.

El objetivo principal fue asegurar que:

- NVIDIA NIM continúe como proveedor primario.
- Gemini se mantenga únicamente como proveedor de respaldo.
- Los modelos configurados respondan correctamente en análisis y generación.
- El fallback se active por causas válidas y quede trazado.
- La auditoría distinga entre interacciones afectadas y eventos reales de fallback.
- La configuración final quede respaldada por pruebas reproducibles.

---

## 2. Problemas detectados

Durante las pruebas reales se identificaron tres problemas principales.

### 2.1 Modelos Llama retirados

Los modelos:

```text
meta/llama-3.1-8b-instruct
meta/llama-3.3-70b-instruct
```

devolvieron:

```text
HTTP 410 Gone
```

en llamadas reales a NVIDIA NIM.

Esto impedía completar rutas de generación.

### 2.2 Gemma no respondía de forma utilizable

El modelo estándar:

```text
google/gemma-4-31b-it
```

agotaba el timeout configurado y provocaba que todos los lotes de análisis terminaran en Gemini.

### 2.3 Métrica de fallback ambigua

La auditoría inicial mostraba:

```text
Fallbacks en análisis: 23
```

pero el detalle de observabilidad mostró que realmente existieron:

```text
23 interacciones afectadas
4 eventos reales de fallback batch
```

La métrica fue corregida para separar ambos conceptos.

---

## 3. Cambios aplicados

### 3.1 Fallback ante HTTP 410

Se añadió soporte explícito para reconocer:

```text
HTTP 410
```

como motivo válido de fallback de proveedor.

Esto permite:

```text
NVIDIA NIM
→ HTTP 410
→ fallback
→ Gemini
```

sin confundir este caso con un retry normal.

---

### 3.2 Modelos NVIDIA NIM actualizados

La configuración final propuesta queda:

| Tier | Modelo |
|---|---|
| rápido | `nvidia/nemotron-3.5-lightning-30b-a3b` |
| estándar | `nvidia/nemotron-3.5-lightning-30b-a3b` |
| razonamiento | `nvidia/nemotron-3-super-120b-a12b` |

Proveedor primario:

```text
NVIDIA NIM
```

Proveedor de respaldo:

```text
Gemini
```

---

### 3.3 Timeout NVIDIA actualizado

El timeout pasó de:

```text
3 s
```

a:

```text
15 s
```

El cambio fue definido a partir de tiempos reales observados con Nemotron Lightning.

---

## 4. Evidencia real de disponibilidad

### 4.1 Gemma – análisis batch

Prueba real con 10 mensajes:

```text
NVIDIA/GEMMA: ERROR
OpenAITimeoutError
Request timed out.
Tiempo: 15.25 s
```

### 4.2 Gemma – análisis individual

```text
NVIDIA/GEMMA INDIVIDUAL: ERROR
OpenAITimeoutError
Request timed out.
Tiempo: 15.26 s
```

### 4.3 Gemma – llamada RAW mínima

Prompt:

```text
Responde únicamente: OK
```

Resultado:

```text
GEMMA RAW: ERROR
OpenAITimeoutError
Request timed out.
Tiempo: 30.36 s
```

La prueba RAW descarta que el problema dependa únicamente del prompt estructurado o del tamaño del lote.

---

## 5. Evaluación de DeepSeek

Se probó:

```text
deepseek-ai/deepseek-v4.1-flash
```

dentro de NVIDIA NIM.

### Análisis estructurado

```text
DEEPSEEK V4.1 FLASH ANALISIS: ERROR
OpenAITimeoutError
Request timed out.
Tiempo: 15.25 s
```

### Llamada RAW

```text
DEEPSEEK RAW: ERROR
OpenAITimeoutError
Request timed out.
Tiempo: 30.25 s
```

Resultado:

```text
No viable en el entorno probado durante esta sesión.
```

No se afirma que el modelo esté retirado; únicamente que no respondió de forma utilizable en las pruebas ejecutadas.

---

## 6. Validación real de Nemotron 3.5 Lightning

Modelo:

```text
nvidia/nemotron-3.5-lightning-30b-a3b
```

### 6.1 Análisis individual estructurado

Resultado:

```text
OK
```

Salida:

```text
sentimiento: muy_positivo
tema_principal: empleabilidad
subtema: primer trabajo analista datos
tipo_detectado: testimonio
```

Tiempo:

```text
1.24 s
```

### 6.2 Lote de 10 mensajes

Resultado:

```text
10 enviados
10 recibidos
```

Tiempo:

```text
8.56 s
```

### 6.3 Dataset completo

Se procesaron los 23 mensajes reales en lotes:

```text
10 / 10 / 3
```

Resultados:

```text
Lote 1: 10/10 | 7.63 s
Lote 2: 10/10 | 9.04 s
Lote 3: 3/3   | 10.09 s
```

Total:

```text
23/23
```

Esta evidencia sustenta el uso de Nemotron Lightning como modelo estándar.

---

## 7. Evidencia real del fallback de análisis

Antes del cambio final de modelo estándar, la auditoría real produjo:

```text
Interacciones de entrada: 23
Excluidas por Data: 0
Resultados DS: 23
Activos generados: 35
Interacciones con fallback en análisis: 23
Eventos de fallback en análisis: 4
Activos con fallback: 0
Eventos de fallback en generación: 0
```

La observabilidad mostró:

```text
4 eventos:
analizar_lote
tier: estandar
proveedor_primario: nvidia_nim
proveedor_final: gemini
fallback: true
motivo: timeout
```

También se registraron:

```text
12 llm_error
```

consistentes con:

```text
4 lotes × 3 intentos NVIDIA
```

antes de activar Gemini.

Esto constituye evidencia real de que el mecanismo de retry y fallback funcionó.

---

## 8. Auditoría de generación

Tras reemplazar los modelos retirados, una ejecución real produjo:

```text
23 interacciones procesadas
35 activos generados
0 activos con fallback
0 eventos de fallback en generación
```

Ejemplos de trazabilidad:

### `int-001` – caso de éxito

```text
tier: razonamiento
proveedor_primario: nvidia_nim
proveedor_usado: nvidia_nim
modelo: nvidia/nemotron-3-super-120b-a12b
fallback_activado: false
```

### `int-002` – FAQ

```text
tier: rapido
proveedor_primario: nvidia_nim
proveedor_usado: nvidia_nim
modelo: nvidia/nemotron-3.5-lightning-30b-a3b
fallback_activado: false
```

---

## 9. Pruebas automatizadas

### Pruebas específicas de fallback 410

```text
57 passed
```

### Batería relevante previa

```text
115 passed
```

### Batería relevante después del cambio estándar

```text
116 passed
```

### Pruebas del proveedor NVIDIA

```text
13 passed
```

### Pruebas de entrega IA

```text
18 passed
```

### Suite completa

```text
439 passed
132 subtests passed
1 failed
1 warning
```

El único fallo restante es:

```text
tests/agents/test_tolerancia_estados_manuales.py::
test_enrutador_tolera_estado_sin_campos
```

El test espera:

```python
{"rutas": []}
```

mientras el router actual devuelve adicionalmente:

```python
{"tier_modelo": "rapido"}
```

Este fallo no corresponde al cambio de modelos de esta tarea.

---

## 10. Relación con Data

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

El informe de Data consulta la configuración efectiva del modelo a través de:

```python
obtener_configuracion_modelo()
```

Por ello, al cambiar el modelo estándar de DS, solamente fue necesario actualizar la expectativa del test que todavía esperaba Gemma.

---

## 11. Commits relevantes

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

---

## 12. Auditoría real final

La auditoría final debe ejecutarse con:

```powershell
python scripts\generar_auditoria_semana4.py --fecha-referencia "2026-10-14T10:14:00-05:00"
```

Configuración esperada:

```text
estándar → nvidia/nemotron-3.5-lightning-30b-a3b
rápido → nvidia/nemotron-3.5-lightning-30b-a3b
razonamiento → nvidia/nemotron-3-super-120b-a12b
timeout NVIDIA → 15 s
fallback → Gemini
```

### Resultado final

Auditoría Semana 4 generada correctamente.
Archivo: D:\ALURA\HackatonG39-Semana1\salida\auditoria_semana4\auditoria_semana4.json
Commit: 65e64a36baa79689e686c6cdb1cf926c91634d56
Rama: feature/DS-Semana4
Working tree limpio: True
Interacciones de entrada: 23
Excluidas por Data: 0
Resultados DS: 23
Activos generados: 32
Interacciones con fallback en análisis: 0
Eventos de fallback en análisis: 0
Activos con fallback: 0
Eventos de fallback en generación: 0

No debe reemplazarse esta sección con valores estimados.

---

## 13. Criterio de cierre

La tarea puede considerarse técnicamente cerrada cuando:

- el SHA ejecutado coincide con el commit final;
- el working tree está limpio;
- la auditoría final se genera correctamente;
- las trazas identifican proveedor, modelo, tier y fallback;
- no existen errores finales no explicados;
- las exclusiones corresponden a Data;
- el JSON de auditoría queda disponible para revisión;
- la documentación conserva también la ejecución anterior como evidencia del funcionamiento real del fallback.

---

## 14. Resumen

La decisión final se sustenta en pruebas reales:

```text
Llama 3.1 / 3.3
→ HTTP 410
→ reemplazo

Gemma
→ timeout 3 s
→ timeout 15 s
→ timeout RAW 30 s
→ no viable en esta ejecución

DeepSeek V4.1 Flash
→ timeout 15 s
→ timeout RAW 30 s
→ no viable en esta ejecución

Nemotron 3.5 Lightning
→ individual OK
→ lote 10/10 OK
→ dataset 23/23 OK
→ adoptado para estándar y rápido

Nemotron 3 Super
→ generación estructurada OK
→ mantenido para razonamiento
```

La arquitectura mantiene separadas las responsabilidades de:

```text
retry
fallback de proveedor
recuperación posterior
```

y conserva NVIDIA NIM como proveedor principal.
