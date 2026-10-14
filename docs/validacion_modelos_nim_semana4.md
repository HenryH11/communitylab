# CommunityLab – Semana 4
## Validación de modelos NVIDIA NIM y paquete de trazabilidad para auditoría

**Proyecto:** CommunityLab – Hackathon ONE G10 / Equipo 39  
**Subequipo:** Cerebro de IA – Data Science  
**Rama:** `feature/DS-Semana4`  
**Fecha:** 14 de octubre de 2026  
**Versión de auditoría:** `1.2`

---

## 1. Propósito

Este documento registra la validación técnica realizada por Data Science sobre los modelos usados en NVIDIA NIM y la preparación del paquete de trazabilidad que será utilizado por el equipo encargado de la auditoría.

El objetivo fue asegurar que:

- NVIDIA NIM continúe como proveedor primario.
- Gemini se mantenga como proveedor de respaldo.
- Los modelos configurados respondan correctamente en análisis y generación.
- Cada análisis y activo generado registre proveedor, modelo, tier y fallback.
- El JSON de salida conserve también el resumen analítico de la comunidad.
- La ejecución quede asociada a un SHA exacto y reproducible.

---

## 2. Problemas detectados durante Semana 4

### 2.1 Modelos retirados

Los modelos:

```text
meta/llama-3.1-8b-instruct
meta/llama-3.3-70b-instruct
```

devolvieron `HTTP 410 Gone` en llamadas reales a NVIDIA NIM.

Esto impedía completar correctamente varias rutas de generación.

### 2.2 Gemma no resultó viable en el entorno probado

El modelo estándar:

```text
google/gemma-4-31b-it
```

agotaba el tiempo disponible y activaba Gemini como proveedor de respaldo.

Se realizaron pruebas controladas:

```text
Gemma batch, timeout 15 s
→ OpenAITimeoutError
→ 15.25 s

Gemma individual, timeout 15 s
→ OpenAITimeoutError
→ 15.26 s

Gemma RAW mínimo, timeout 30 s
→ OpenAITimeoutError
→ 30.36 s
```

La llamada RAW utilizó únicamente:

```text
Responde únicamente: OK
```

por lo que el problema observado no dependía solamente del esquema estructurado o del tamaño del lote.

### 2.3 DeepSeek tampoco respondió de forma utilizable

Se evaluó:

```text
deepseek-ai/deepseek-v4.1-flash
```

dentro de NVIDIA NIM.

Resultados:

```text
Análisis estructurado, timeout 15 s
→ OpenAITimeoutError
→ 15.25 s

RAW, timeout 30 s
→ OpenAITimeoutError
→ 30.25 s
```

No se asumió que el modelo estuviera retirado; únicamente se concluyó que no fue viable en el entorno probado durante esta sesión.

---

## 3. Modelos seleccionados

La configuración validada quedó:

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

Timeout NVIDIA:

```text
15 segundos
```

---

## 4. Evidencia real de Nemotron 3.5 Lightning

### Análisis individual estructurado

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

### Dataset completo

Se procesaron 23 mensajes en lotes de `10 / 10 / 3`.

```text
Lote 1: 10/10 | 7.63 s
Lote 2: 10/10 | 9.04 s
Lote 3: 3/3   | 10.09 s

Total: 23/23
```

Esta evidencia sustentó el reemplazo de Gemma por Nemotron Lightning como modelo estándar y el aumento del timeout de `3 s` a `15 s`.

---

## 5. Fallback y tolerancia a fallos

Se añadió soporte explícito para reconocer:

```text
HTTP 410
```

como motivo válido para fallback de proveedor.

El flujo queda:

```text
NVIDIA NIM
→ error apto para fallback
→ Gemini
```

manteniendo separados los conceptos de:

```text
retry
fallback de proveedor
recuperación posterior
```

---

## 6. Evidencia real del fallback de análisis

Antes del cambio final de modelo estándar, una ejecución real produjo:

```text
Interacciones de entrada: 23
Resultados DS: 23
Interacciones con fallback en análisis: 23
Eventos de fallback en análisis: 4
Activos con fallback: 0
Eventos de fallback en generación: 0
```

La observabilidad mostró además:

```text
12 llm_error
```

consistentes con:

```text
4 lotes × 3 intentos NVIDIA
```

antes de utilizar Gemini.

Esta ejecución se conserva como evidencia real de que el mecanismo de fallback funcionó.

---

## 7. Corrección de las métricas de fallback

La auditoría inicial mostraba de forma ambigua:

```text
Fallbacks en análisis: 23
```

Se corrigió para diferenciar:

```text
interacciones_con_fallback_analisis
eventos_fallback_analisis
activos_con_fallback
eventos_fallback_generacion
```

De esta manera se distingue entre:

- cantidad de interacciones afectadas;
- cantidad real de eventos de cambio de proveedor.

---

## 8. Recuperación del resumen analítico

La versión inicial del paquete de Semana 4 conservaba toda la información por interacción, pero había dejado fuera del bloque `resumen` las agregaciones analíticas que existían previamente.

En la versión `1.2` se recuperaron mediante la lógica estable de:

```text
src/agentes/resumen_entrega.py
```

El JSON vuelve a incluir:

```text
sentimiento_predominante
sentimientos_predominantes
distribucion_sentimientos
temas_principales
distribucion_temas
distribucion_tipos_detectados
```

Estas métricas se calculan automáticamente a partir de los resultados reales de la ejecución y no están hardcodeadas.

La versión `1.2` conserva simultáneamente:

### Resumen analítico

```text
sentimiento predominante
distribución de sentimientos
temas principales
distribución de temas
distribución de tipos detectados
```

### Trazabilidad operativa

```text
proveedor
modelo
tier
fallback
motivo de fallback
SHA
errores
fallos
```

---

## 9. Pruebas automatizadas

Resultados obtenidos durante la validación:

```text
Pruebas específicas de fallback HTTP 410:
57 passed

Batería relevante previa:
115 passed

Batería relevante final:
116 passed

Proveedor NVIDIA:
13 passed

Entrega IA:
18 passed

Auditoría Semana 4 v1.2:
9 passed
```

Suite completa:

```text
439 passed
132 subtests passed
1 fallo conocido
1 warning externo
```

El único fallo conocido corresponde a:

```text
tests/agents/test_tolerancia_estados_manuales.py::
test_enrutador_tolera_estado_sin_campos
```

El test espera únicamente:

```python
{"rutas": []}
```

mientras el router actual devuelve además:

```python
{"tier_modelo": "rapido"}
```

Este fallo no corresponde a los cambios de modelos, fallback o auditoría realizados en esta tarea.

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

Data Science:

- conserva `tipo_original`;
- genera `tipo_detectado`;
- no utiliza `tipo_original` como ground truth humano para el análisis LLM.

---

## 11. Ejecución final vigente

**IMPORTANTE:** esta ejecución reemplaza las salidas anteriores de Semana 4 para efectos del paquete que se entregará al equipo de auditoría.

SHA exacto utilizado:

```text
4331b6eb866b05062e189a4ee937c72531771513
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
Activos generados: 26

Interacciones con fallback en análisis: 0
Eventos de fallback en análisis: 0

Activos con fallback: 0
Eventos de fallback en generación: 0
```

El archivo generado es:

```text
salida/auditoria_semana4/auditoria_semana4.json
```

La carpeta `salida/` está ignorada por Git, por lo que este archivo debe compartirse directamente como artefacto de ejecución y no forzarse al repositorio.

---

## 12. Sobre la variación en la cantidad de activos

El número de activos puede variar entre ejecuciones porque la clasificación producida por el LLM puede modificar `tipo_detectado` y, en consecuencia, las rutas resultantes.

Las ejecuciones históricas se conservan como evidencia de regresión y estabilidad, pero no se consideran ground truth humano.

Para auditoría debe utilizarse únicamente el JSON asociado al SHA exacto de la ejecución que se está revisando.

La ejecución vigente es:

```text
4331b6eb866b05062e189a4ee937c72531771513
```

con:

```text
26 activos generados
```

---

## 13. Commits relevantes

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

---

## 14. Archivo que debe utilizar el equipo de auditoría

El archivo vigente es:

```text
salida/auditoria_semana4/auditoria_semana4.json
```

Generado sobre:

```text
4331b6eb866b05062e189a4ee937c72531771513
```

Este archivo reemplaza los JSON generados en ejecuciones anteriores.

Contiene:

- interacciones de entrada;
- decisiones provenientes de Data;
- análisis de DS;
- sentimiento, tema, subtema y tipo detectado;
- rutas;
- activos generados;
- resumen analítico;
- proveedor y modelo por análisis;
- proveedor y modelo por activo;
- tier utilizado;
- información de fallback;
- errores y fallos;
- configuración de IA;
- SHA del dataset;
- SHA exacto del código.

---

## 15. Estado final

La configuración final mantiene:

```text
NVIDIA NIM como proveedor primario
Gemini como proveedor de respaldo
Nemotron Lightning para rápido/estándar
Nemotron Super para razonamiento
timeout NVIDIA de 15 s
```

El paquete de trazabilidad `1.2` recupera el resumen analítico previo y añade la información necesaria para separar resultados por proveedor/modelo en la auditoría.

La salida vigente para revisión es exclusivamente la generada sobre:

```text
4331b6eb866b05062e189a4ee937c72531771513
```
