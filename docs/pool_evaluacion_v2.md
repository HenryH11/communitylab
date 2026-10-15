# Pool de evaluación v2 · 200 casos por fuente

Responsable: Data Analyst (Gustavo Vásquez, Jhonattan Benavides). Fecha: 15 de octubre de 2026.
Estado: **propuesta**. No forma parte del cierre de la Matriz 2 ni de la Semana 5.1.

## Para qué sirve

La comparación de proveedores de la Semana 3 (`docs/evaluacion_proveedores_semana3.md`)
usó un holdout de 30 casos. Con 30 casos, una exactitud del 75 % tiene un margen de
±15,5 puntos (intervalo del 95 %). Con eso no se puede distinguir si NVIDIA y Gemini, o
dos modelos de NVIDIA, clasifican distinto. Con 200 casos por fuente el margen baja
a unos ±6 puntos, o ±7 en el peor caso (exactitud del 50 %).

El pool sirve para medir el **análisis** de DS (`sentimiento`, `tema_principal`,
`tipo_detectado`) con texto real en español, distinto de los 23 mensajes simulados.

## Qué no cambia

- `tests/fixtures/holdout_final_analisis_semana3.json` (holdout v1, 30 casos)
  sigue congelado.
- `src/datos/mensajes_comunidad_simulados.json` (23 interacciones) sigue igual.
- El pool vive aparte, en `datos_evaluacion/pool_v2/`. El constructor descarta
  cualquier texto que ya esté en el holdout o en el dataset base, y una prueba lo
  verifica.

## Fuentes

| Fuente | Licencia | Uso | Decisión |
| --- | --- | --- | --- |
| [IA Tweets Analysis Dataset (Spanish)](https://doi.org/10.5281/zenodo.10821485), Universidad de Cádiz, 2024: 4.038 tuits sobre IA | CC BY 4.0 | Sentimiento con etiqueta de la fuente (P / N / NEU) | **Usada**: `uca_ia_tweets.json` |
| Preguntas de [es.stackoverflow.com](https://es.stackoverflow.com) por la [API pública de Stack Exchange](https://api.stackexchange.com/docs) | CC BY-SA 3.0 o 4.0, según la pregunta | Preguntas técnicas reales de programación, datos y cloud | **Usada**: `stackoverflow_es.json` |
| [Reddit Hispano Mundial 2026](https://huggingface.co/datasets/Maverz/reddit-hispano-mundial-2026), Hugging Face | CC BY-NC 4.0 | Posts sin anotar sobre el Mundial | **Descartada**: está fuera del dominio, no tiene etiquetas y prohíbe el uso comercial |
| Tuits con sentimiento (unos 250.000), propuestos por DS | Sin verificar | — | **Pendiente**: falta el enlace y la licencia |
| Reddit `r/programacion` (`src/datos/ingesta_reddit.py`) | Términos de Reddit | — | **No usada**: no da permiso claro para redistribuir el texto en el repositorio |

Las fuentes crudas no se suben al repositorio; solo el pool procesado, con su
atribución (ver `datos_evaluacion/pool_v2/ATRIBUCION.md`).

## Cómo se construye

`scripts/construir_pool_evaluacion.py` usa solo la biblioteca estándar: no llama a
IA ni a la red.

### Tuits

- Quita enlaces y reemplaza las menciones por `@usuario`, para no exponer cuentas.
- Descarta textos de menos de 40 caracteres, textos que no están en español y
  duplicados.
- Quedan 3.181 candidatos de 4.038.

### Preguntas

- Usa el título y el comienzo del cuerpo. Reemplaza los bloques de código por
  `[código]` y recorta a 400 caracteres.
- Descarta duplicados.
- Quedan 565 candidatos de 600 (10 etiquetas × 60).

### Muestreo

- Estratificado y con semilla fija `20261015`.
- Tuits: 67 negativos, 67 neutrales y 66 positivos. Se equilibra para medir la
  exactitud por clase, porque la fuente es 67 % neutral.
- Preguntas: 20 por etiqueta (python, javascript, html, css, sql, java, git,
  pandas, machine-learning, docker).

### Salida

- Un JSON por fuente, con el formato del holdout v1. Así,
  `scripts/evaluar_holdout_proveedores.py --fixture <archivo>` lo lee sin cambios.
- `manifiesto.json` registra la semilla, el SHA-256 de cada archivo y de la
  entrada, los candidatos y las distribuciones. Una prueba comprueba que los
  archivos versionados coinciden con su SHA. El SHA se calcula con saltos de
  línea LF; la prueba normaliza CRLF para que pase también en Windows.

Para regenerarlo:

```powershell
# 1. Fuentes (fuera del repositorio)
curl -L -o ia_tweets.csv "https://zenodo.org/api/records/10821485/files/ia_tweets.csv/content"
# Preguntas: una consulta por etiqueta, 60 por consulta, sin clave
# https://api.stackexchange.com/2.3/questions?order=desc&sort=votes&site=es.stackoverflow&pagesize=60&tagged=<etiqueta>&filter=withbody
# 2. Pool
python -m scripts.construir_pool_evaluacion --uca-csv ia_tweets.csv --so-dir <carpeta_json> --salida datos_evaluacion/pool_v2
```

Las preguntas se ordenan por votos y la API las devuelve en el orden actual. Para
reproducir exactamente este pool, se usa el `manifiesto.json` y los archivos
versionados, no una descarga nueva.

## Etiquetas: de dónde vienen y cuánto valen

Cada caso declara en `origen_etiquetas` si cada etiqueta viene de la **fuente** o de
una **regla**, y trae `revision_humana: "pendiente"`.

| Fuente | sentimiento | tema | tipo |
| --- | --- | --- | --- |
| Tuits | fuente (P/N/NEU; la fuente no dice si la etiquetó una persona) | regla: `datos_ia` | regla: `comentario` |
| Preguntas | regla: `neutral` | regla, por etiqueta (programación, datos_ia, cloud) | fuente: `pregunta_tecnica` |

Límites conocidos:

1. **El sentimiento de los tuits tiene 3 clases; DS usa 5.** Hay que comparar
   agrupando `muy_positivo` con `positivo` y `muy_negativo` con `negativo`.
   `evaluar_holdout_proveedores.py` hoy compara de forma exacta: con los tuits
   subestimaría la exactitud. Se propone a DS una opción para agrupar las clases.
2. **Las etiquetas por regla tienen errores.** Por ejemplo, hay tuits que no
   hablan de IA, y preguntas con frustración que no son neutrales. Antes de usar
   el pool para decidir, DA revisa una muestra estratificada de 40 casos por
   fuente. Si una regla falla en más del 10 % de la muestra, se corrige la regla
   o se etiqueta a mano.
3. **Falta cobertura de tres tipos:** `testimonio`, `pregunta_programa` y
   `feedback`. No hay una fuente abierta en español de testimonios de alumnos ni
   de preguntas sobre un programa de formación. Opciones para una tercera fuente:
   - generar casos sintéticos con IA, como propuso Jhonattan; requiere el OK de
     Gustavo por el costo y que una persona revise las etiquetas;
   - o que el equipo los redacte a mano.

## Costo de usarlo

Con la configuración del evaluador (lotes de 10 y 3 corridas), cada fuente de 200
casos son 60 llamadas por proveedor. Las 2 fuentes con 2 proveedores suman unas 240
llamadas. Ninguna corrida se hace sin el OK de Gustavo.

## Pendiente

- Revisión humana de 40 casos por fuente.
- Opción de DS para agrupar el sentimiento a 3 clases.
- Decidir la tercera fuente (sintéticos o redactados).
- Decidir si el pool entra en la Semana 5.1 o queda para después del congelamiento.
