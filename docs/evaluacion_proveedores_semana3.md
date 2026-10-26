# Evaluación comparativa de proveedores de IA — Semana 3

**Proyecto:** CommunityLab — Hackathon ONE G10 / Equipo 39
**Subequipo:** Cerebro de IA / Data Science
**Fecha de cierre:** 12 de octubre de 2026
**Rama:** `feature/DS-Semana3-Nvidia`

## Objetivo

Evaluar si NVIDIA NIM, usando `nvidia/nemotron-3.5-lightning-30b-a3b`, puede sustituir a Gemini como proveedor principal del análisis semántico de CommunityLab sin degradar calidad ni estabilidad.

Se evaluaron:

- `sentimiento`
- `tema_principal`
- `tipo_detectado`

`subtema` se revisó cualitativamente y no por igualdad exacta.

## Contratos respetados

- No se modificó lógica de `src/datos/*`.
- Data sigue siendo fuente de verdad de `score_relevancia`, `tipo_original`, `elegible_contenido` y `elegible_faq`.
- DS conserva `tipo_original` y genera `tipo_detectado`.
- El router sigue siendo determinista.
- Nemotron se evalúa dentro de NVIDIA NIM.
- Retry, fallback y recuperación se mantienen diferenciados.

## Cambios del análisis

### Prompt

`src/agentes/prompts/analisis.py` se refinó para:

- separar las cuatro dimensiones;
- precisar los cinco niveles de sentimiento;
- distinguir polaridad e intensidad;
- definir las 11 categorías de tema;
- documentar fronteras entre categorías próximas;
- incorporar few-shot sintético;
- evitar clasificación por coincidencia simple de palabras.

Los conjuntos usados durante el desarrollo se consideran **development sets**, no ground truth humano definitivo.

### Independencia de `tipo_original`

Se detectó anclaje cuando `tipo_original` era enviado al LLM, especialmente en Nemotron.

| NVIDIA | Accuracy | `tipo_original != esperado` | Copias del original incorrecto |
| --- | ---: | ---: | ---: |
| Con `tipo_original` | 21/25 (84.0%) | 6/10 | 4/10 |
| Sin `tipo_original` | 24/25 (96.0%) | 10/10 | 0/10 |

Decisión:

```text
Data
 ├─ tipo_original ───────────────► EstadoAgente / salida
 └─ texto + origen + canal + idioma
                    │
                    ▼
                   LLM
                    │
                    ▼
             tipo_detectado
```

`tipo_original` se conserva, pero no se envía al LLM.

## Regresión de desarrollo con arquitectura final

| Dimensión | NVIDIA NIM / Nemotron | Gemini |
| --- | ---: | ---: |
| Tema | 31/33 (93.9%) | 33/33 (100.0%) |
| Sentimiento | 22/25 (88.0%) | 24/25 (96.0%) |
| Tipo detectado | 24/25 (96.0%) | 25/25 (100.0%) |

Estos resultados fueron usados para cierre/regresión, no como resultado final.

## Holdout final congelado

Se construyó un holdout nuevo de 30 mensajes y se fijaron sus etiquetas **antes** de ejecutar los proveedores.

SHA-256:

```text
d2958d3cb8232c25151c43596598d549946332c1a8a3562189e71ec8d412622e
```

Distribución de sentimiento:

```text
muy_negativo: 6
muy_positivo: 6
negativo: 6
neutral: 6
positivo: 6
```

Distribución de tipo:

```text
comentario: 6
feedback: 6
pregunta_programa: 6
pregunta_tecnica: 6
testimonio: 6
```

Los 11 temas tuvieron 2–3 casos cada uno.

## Protocolo final

- 3 corridas por proveedor.
- Lotes de 10.
- Mismo prompt.
- Mismos 30 mensajes.
- Sin `tipo_original`.
- Llamadas directas a cada proveedor.
- Sin fallback entre proveedores.
- Accuracy por corrida.
- Resultado por moda de 3 corridas.
- Estabilidad por dimensión.
- `triple_correcto`: sentimiento + tema + tipo correctos simultáneamente.

## Resultado final

### NVIDIA NIM / Nemotron

| Métrica | Corrida 1 | Corrida 2 | Corrida 3 | Moda |
| --- | ---: | ---: | ---: | ---: |
| Sentimiento | 63.3% | 66.7% | 70.0% | **66.7%** |
| Tema | 90.0% | 86.7% | 86.7% | **86.7%** |
| Tipo detectado | 86.7% | 83.3% | 86.7% | **86.7%** |
| Triple correcto | 53.3% | 53.3% | 56.7% | **56.7%** |

Estabilidad:

```text
sentimiento: 28/30 (93.3%)
tema_principal: 29/30 (96.7%)
tipo_detectado: 29/30 (96.7%)
```

Retries externos: `0`
Tiempo acumulado de lotes: `74.4 s`

### Gemini

| Métrica | Corrida 1 | Corrida 2 | Corrida 3 | Moda |
| --- | ---: | ---: | ---: | ---: |
| Sentimiento | 86.7% | 86.7% | 90.0% | **86.7%** |
| Tema | 96.7% | 96.7% | 100.0% | **96.7%** |
| Tipo detectado | 90.0% | 90.0% | 90.0% | **90.0%** |
| Triple correcto | 76.7% | 76.7% | 80.0% | **76.7%** |

Estabilidad:

```text
sentimiento: 27/30 (90.0%)
tema_principal: 29/30 (96.7%)
tipo_detectado: 30/30 (100.0%)
```

Retries externos: `0`
Tiempo acumulado de lotes: `60.9 s`

## Comparación por moda

| Dimensión | NVIDIA | Gemini | Diferencia |
| --- | ---: | ---: | ---: |
| Sentimiento | 66.7% | **86.7%** | +20.0 pp Gemini |
| Tema | 86.7% | **96.7%** | +10.0 pp |
| Tipo detectado | 86.7% | **90.0%** | +3.3 pp |
| Triple correcto | 56.7% | **76.7%** | +20.0 pp |

## Decisión técnica

### Estado de esta rama experimental

La rama `feature/DS-Semana3-Nvidia` **mantiene NVIDIA NIM como proveedor primario por defecto**, tal como fue diseñada para experimentar con Nemotron y validar retry, fallback, observabilidad y tolerancia a fallos.

No se cambia el default de esta rama únicamente por el resultado del benchmark, para evitar mezclar el objetivo experimental de la rama con una decisión de integración estable.

### Propuesta para la reunión / integración estable

El holdout congelado favorece claramente a Gemini en calidad semántica. Por ello, la recomendación para discutir con el equipo es:

```text
línea estable / develop:
Gemini = proveedor primario recomendado

NVIDIA NIM / Nemotron:
proveedor alternativo o respaldo propuesto
```

La propuesta `Gemini -> Nemotron` como fallback **todavía no está implementada en esta rama**. El flujo actual implementado es `NVIDIA NIM -> Gemini`.

Invertir el sentido del fallback requiere un cambio de código y pruebas específicas antes de integrarlo a `develop`.

### Generación

Este holdout evaluó análisis semántico, no la calidad comparativa de boletín, caso de éxito, LinkedIn, FAQ o insight.

Por tanto:

- no se modifica ahora el proveedor por defecto de generación en esta rama experimental;
- cualquier propuesta de usar Gemini como primario y Nemotron como respaldo para generación debe evaluarse por separado.

## Evidencia operacional

Durante el desarrollo se observaron timeouts variables con 10 s y 20 s. Otras corridas respondieron por debajo de esos valores. El holdout final, con timeout amplio, terminó sin retries externos.

Esto se registra como evidencia de variabilidad operacional y no se mezcla con la métrica semántica.

## Archivos a versionar

Código:

```text
src/agentes/prompts/analisis.py
src/agentes/nodos/nodo_analizador.py
```

No es necesario cambiar ahora los defaults de `src/agentes/configuracion_ia.py`: esta rama conserva su propósito experimental con NVIDIA NIM como primario.

Pruebas:

```text
tests/agents/test_procesamiento_lotes.py
```

Las pruebas que actualmente esperan NVIDIA como default de esta rama no deben cambiarse solo por la recomendación futura para `develop`.

Evidencia y reproducibilidad:

```text
tests/fixtures/holdout_final_analisis_semana3.json
docs/evidencia_holdout_proveedores_semana3.json
scripts/evaluar_holdout_proveedores.py
docs/evaluacion_proveedores_semana3.md
```

Documentación a actualizar:

```text
docs/guia_pruebas_nvidia.md
docs/manual_lectura_codigo_nvidia.md
```

## Limitaciones

- El holdout contiene 30 casos.
- Las etiquetas fueron fijadas antes de ejecutar los modelos, pero no provienen de múltiples anotadores independientes.
- Los development sets no deben presentarse como evaluación final.
- Las ejecuciones históricas siguen siendo referencias de regresión/estabilidad.
- La generación de activos necesita una evaluación específica.

## Conclusión

La integración NVIDIA es técnicamente funcional y esta rama experimental puede mantenerla como proveedor primario para continuar las pruebas. El holdout congelado favorece a Gemini en sentimiento, tema, tipo detectado, exactitud conjunta y tiempo acumulado.

La recomendación para la reunión es **no promover NVIDIA como primario de la línea estable todavía**. En su lugar, se propone discutir una arquitectura futura con Gemini como primario y Nemotron como respaldo, cuya inversión de fallback deberá implementarse y validarse en un cambio separado.
