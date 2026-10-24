# Guía de Benchmark Exploratorio y Resiliencia de Fallback

**Proyecto:** CommunityLab — Equipo 39 ONE G10
**Área:** Data Science / Cerebro de IA
**Rama:** `feature/DS-Semana3-Nvidia`
**Base revisada:** `eeae694`

---

## 1. Objetivo

Este documento describe dos aportes complementarios del componente de Ciencia de Datos:

1. La mejora de resiliencia ante estados degradados de NVIDIA NIM.
2. Un benchmark exploratorio entre NVIDIA NIM y Google Gemini sobre casos semánticamente ambiguos.

Ambos objetivos deben mantenerse separados.

El fallback evalúa **disponibilidad operacional**.

El benchmark explora **diferencias de clasificación semántica**.

Los resultados del benchmark no constituyen ground truth humano y no deben utilizarse por sí solos para declarar que un proveedor es superior a otro.

---

## 2. Aporte proveniente del PR #27

El tratamiento específico de errores HTTP 400 asociados a funciones degradadas de NVIDIA NIM fue propuesto originalmente por **Danny González** en el PR #27.

La integración actual adapta ese aporte a la arquitectura vigente de `feature/DS-Semana3-Nvidia`, que ya incluye selección dinámica de modelos y generación multi-tier.

No se realizó merge ni cherry-pick completo del PR #27. Se integraron únicamente los componentes compatibles con la arquitectura actual.

---

## 3. Resiliencia ante HTTP 400 DEGRADED

### Problema

NVIDIA NIM puede responder con HTTP 400 en escenarios donde una función del servicio se encuentra degradada.

Un HTTP 400 normalmente representa un problema en la petición y, por tanto, no debería activar automáticamente otro proveedor.

Sin embargo, un error que contenga simultáneamente:

- `HTTP 400`
- `FUNCTION`
- `DEGRADED`

se interpreta como una degradación operacional del servicio.

### Política aplicada

En `src/agentes/fallback_ia.py`:

```text
HTTP 400 + FUNCTION + DEGRADED
→ motivo: servicio_degradado
→ activa fallback de proveedor
```

Mientras que:

```text
HTTP 400 genérico
→ no activa fallback
```

Esta distinción evita ocultar errores reales de payload o de programación bajo un cambio automático de proveedor.

---

## 4. Separación entre retry, fallback y recovery

CommunityLab mantiene tres mecanismos diferentes:

### Retry

Reintenta una operación con el mismo proveedor cuando el error se considera transitorio.

### Fallback

Cambia al proveedor alternativo cuando el proveedor primario no puede completar la operación bajo una causa admitida por la política.

### Recovery

Permite recuperar posteriormente interacciones que no pudieron completarse incluso después de aplicar los mecanismos operacionales anteriores.

Estos conceptos no deben utilizarse como sinónimos.

---

## 5. Cobertura de pruebas del fallback DEGRADED

Se añadieron pruebas para los dos flujos principales de IA.

### Análisis

Archivo:

```text
tests/agents/test_fallback_analisis.py
```

Casos cubiertos:

```text
HTTP 400 + DEGRADED + FUNCTION
→ NVIDIA falla
→ Gemini actúa como respaldo

HTTP 400 genérico
→ NVIDIA falla
→ Gemini NO debe ser invocado
```

### Generación

Archivo:

```text
tests/agents/test_fallback_generacion.py
```

Se replica el mismo contrato para la generación de activos.

Esto es importante porque la arquitectura actual utiliza NVIDIA NIM tanto para análisis como para generación, incluyendo enrutamiento multi-tier.

### Resultado focal

La ejecución de los cuatro casos nuevos produjo:

```text
4 passed
```

Posteriormente se ejecutaron las suites completas de fallback:

```text
13 passed
```

No se observaron regresiones en estas pruebas.

---

## 6. Benchmark exploratorio de casos ambiguos

Script:

```text
scripts/benchmark_calibracion_ambiguos.py
```

Evidencia generada:

```text
docs/benchmark_calibracion_casos_ambiguos.json
```

El objetivo es observar diferencias de comportamiento entre proveedores frente a mensajes cuya interpretación admite más de una clasificación razonable.

No se calcula accuracy porque estos cuatro casos no tienen una etiqueta humana validada específicamente para este experimento.

---

## 7. Casos utilizados

Se utilizan cuatro interacciones ambiguas:

```text
int-006
int-011
int-016
int-020
```

Los dilemas incluyen diferencias posibles en:

- sentimiento;
- tema principal;
- subtema;
- tipo_detectado.

Estos casos funcionan como ejemplos de frontera para exploración cualitativa.

No se utilizan como ground truth.

---

## 8. Entrada enviada a los modelos

Ambos proveedores reciben la misma información:

```text
origen
canal
idioma
texto
```

El campo:

```text
tipo_original
```

no se envía al LLM.

`tipo_original` se conserva como dato proveniente del pipeline de Data, mientras que Data Science produce independientemente:

```text
tipo_detectado
```

Por tanto, `tipo_original` tampoco se utiliza como etiqueta humana de referencia para medir la precisión del modelo.

---

## 9. Comparación directa sin fallback

Para evitar contaminar la comparación, el benchmark ejecuta ambos proveedores de manera independiente.

El flujo experimental es:

```text
caso
 ├── NVIDIA NIM
 └── Gemini
```

No es:

```text
NVIDIA
 └── si falla → Gemini
```

Por ello:

```text
sin_fallback = true
```

en la evidencia generada.

Un fallo de un proveedor se registra como parte del experimento y no provoca automáticamente una llamada al otro proveedor.

---

## 10. Modelos ejecutados

La ejecución registrada utilizó:

### NVIDIA NIM

```text
google/gemma-4-31b-it
```

Ruta:

```text
analisis
```

Tier:

```text
estandar
```

### Google Gemini

```text
gemini-3.5-flash-lite
```

Los identificadores se resuelven desde la configuración real del proyecto y no se almacenan de forma fija dentro de la metadata del experimento.

---

## 11. Timeout experimental de NVIDIA

La configuración productiva del proyecto conserva su timeout habitual.

Para el benchmark se utiliza exclusivamente:

```text
30 segundos
```

Este valor se aplica únicamente dentro del proceso experimental mediante:

```text
COMMUNITYLAB_NVIDIA_TIMEOUT_SEGUNDOS
```

sin modificar:

- `.env`;
- `configuracion_ia.py`;
- el timeout productivo permanente.

La evidencia registra explícitamente:

```text
timeout_productivo_modificado = false
```

El objetivo es permitir que el benchmark semántico evalúe la respuesta del modelo sin convertir el timeout productivo en el factor dominante del experimento.

---

## 12. Resultado de la ejecución registrada

La evidencia actual reporta:

```text
Total de casos                 : 4

NVIDIA NIM
Respuestas válidas             : 4/4

Google Gemini
Respuestas válidas             : 3/4

Comparaciones completas        : 3/4
Ejecución completa             : false
```

Gemini presentó un `GoogleAPIError` en `int-016`.

El fallo se conserva en la evidencia y no se repite la ejecución únicamente con el objetivo de obtener artificialmente un resultado 4/4.

---

## 13. Observaciones semánticas

En los tres casos donde ambos proveedores devolvieron una respuesta válida:

```text
int-006
int-011
int-020
```

ambos coincidieron en:

- sentimiento;
- tema principal;
- tipo_detectado.

Las diferencias observadas fueron menores y principalmente relacionadas con el nivel de detalle del subtema.

En `int-016`, NVIDIA produjo una respuesta válida mientras Gemini presentó un error de API, por lo que no existe comparación semántica directa para esa ejecución.

Estas observaciones corresponden únicamente a esta corrida experimental.

No constituyen evidencia suficiente para afirmar que un proveedor sea globalmente mejor que otro.

---

## 14. Trazabilidad

La evidencia fue generada sobre:

```text
commit_head = eeae694
```

con:

```text
working_tree_con_cambios = true
```

Esto es esperado porque el benchmark y la mejora de fallback todavía se encontraban como modificaciones locales al momento de la ejecución.

La metadata se conserva para evitar presentar el JSON como si hubiera sido generado exactamente desde un commit limpio.

---

## 15. Interpretación correcta de la evidencia

El benchmark puede utilizarse para:

- estudiar diferencias semánticas;
- revisar estabilidad entre proveedores;
- descubrir casos de frontera;
- detectar errores operacionales;
- diseñar posteriormente una evaluación controlada más amplia.

No debe utilizarse para:

- calcular accuracy real;
- afirmar que los cuatro casos representan ground truth;
- usar `tipo_original` como respuesta correcta;
- seleccionar definitivamente un proveedor;
- extrapolar cuatro ejemplos al comportamiento completo del sistema.

---

## 16. Relación con evaluaciones posteriores

Este benchmark es complementario a evaluaciones más controladas.

La selección futura del proveedor de análisis debería considerar como mínimo:

- un holdout corregido y reproducible;
- mismas entradas para cada proveedor;
- modelos explícitamente registrados;
- latencia;
- tasa de respuestas válidas;
- estabilidad entre ejecuciones;
- comportamiento de fallback;
- revisión humana cuando se necesite establecer ground truth.

Las ejecuciones históricas sirven como evidencia de regresión, estabilidad y exploración, no como sustituto de una evaluación humana validada.

---

## 17. Reproducción

Para ejecutar únicamente este benchmark:

```powershell
python scripts/benchmark_calibracion_ambiguos.py
```

El script generará o sobrescribirá:

```text
docs/benchmark_calibracion_casos_ambiguos.json
```

La ejecución realiza llamadas reales a NVIDIA NIM y Gemini.

Para validar únicamente las pruebas de fallback:

```powershell
python -m pytest `
  tests/agents/test_fallback_analisis.py `
  tests/agents/test_fallback_generacion.py `
  -q
```

Estas pruebas utilizan mocks y no requieren realizar llamadas reales a los proveedores.

---

## 18. Estado de esta integración

La incorporación del aporte del PR #27 se realiza de forma selectiva:

```text
HTTP 400 DEGRADED
→ integrado y adaptado

Pruebas de análisis
→ integradas

Pruebas equivalentes de generación
→ añadidas para la arquitectura actual

Benchmark de casos ambiguos
→ conservado y actualizado

Metadata histórica hardcodeada
→ eliminada

JSON anterior
→ reemplazado por evidencia regenerada

modelo_ia.py del PR #27
→ no requerido

Com_lab.ipynb
→ no integrado en esta etapa
```

El notebook requiere una actualización separada para reflejar correctamente la arquitectura multi-tier actual y evitar referencias obsoletas.
