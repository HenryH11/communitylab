# Sub-equipo 3 — Ingesta y Procesamiento de Datos

## Actualización de Jhonattan (17 de septiembre de 2026)

La selección de relevancia está implementada en `ingest.py` y `relevancia.py`.
El dataset tiene 23 mensajes: los 21 de Gustavo más Mariana Souza y Lucas
Albuquerque, con los textos del brief. Los pesos de `config/relevancia.json`
son una propuesta pendiente de validación con Gustavo e IA.

Desde la raíz del repositorio:

```sh
python -m src.data.ingest --config config/relevancia.json --fecha-referencia 2026-09-17T12:00:00Z
python -m unittest discover -s tests -p "test_ingest_relevancia.py" -v
python tests/verificar_transformacion_reddit.py
```

Se generan `output/datos/mensajes_filtrados.json` y un informe separado con
puntajes y descartes. El JSON simulado sigue siendo la entrada completa; no
está prefiltrado. Para integrar, ver el
[contrato de datos](../../docs/contrato_datos_ingesta.md) y el
[criterio implementado](../../docs/criterio_puntuacion_relevancia.md).

El foro de Alura sigue representado por datos simulados; la evaluación de una
fuente real con Arthur es opcional. El resto de esta guía conserva el contexto
de entrega de Gustavo, con los pendientes de relevancia actualizados.

## Semana 1 — entrega consolidada de Gustavo y Jhonattan (26 de septiembre)

El comando de entrega conserva todos los mensajes válidos para sentimiento y
separa su elegibilidad para contenido. Reutiliza el adaptador de Gustavo a
AgentState y valida los puntajes por ID y contexto.

```sh
python -m src.data.ingest --config config/relevancia.json --fecha-referencia 2026-09-17T12:00:00Z --entrega-ia output/datos/ia --tamano-ciclo 20
```

Con esa referencia: **23 estados para sentimiento, 14 seleccionados para contenido
y ciclos operativos de 12 y 11 mensajes**. El paquete incluye:
- Selección e informe en output/datos.
- Población completa, estados de IA y plan de procesamiento en output/datos/ia.
- Fragmentos planos por origen y manifest en output/datos/entregas.

Los fragmentos por origen pueden ser menores de 10. El plan operativo agrupa
estados de 10 a 30 conservando cada origen; cualquier remanente queda pendiente.
Sin `--entrega-ia`, se conserva la selección de contenido por defecto.
`--tamano-ciclo` acepta ahora únicamente enteros de 10 a 30.
Los IDs para entrega deben ser globalmente únicos y las fechas válidas.

El guardado solo retira fragmentos del manifest previo; conserva archivos ajenos
y rechaza rutas o colisiones inseguras. No se usa output como carpeta de ciclos.
No hay llamadas a Gemini ni OCI en esta entrega.

Pruebas de Datos sin dependencias externas ni servicios cloud:

```sh
python -m unittest discover -s tests -p "test_ingest_relevancia.py"
python -m unittest discover -s tests -p "test_entrega_ia.py"
python -m unittest discover -s tests -p "test_reddit_original.py"
```

Para DS: `preparar_paquete_ia` devuelve estados con las claves existentes
`score_relevancia`, `origen` y `tipo_original`. El plan conserva
`ids_contenido` por separado; DS debe respetarlos al generar activos.
La conexión al grafo y aprobación del contrato siguen pendientes.
Ver [contrato, archivos y ejemplo de consumo](../../docs/contrato_datos_ingesta.md).

El texto siguiente conserva el contexto original del aporte de Gustavo.

---

Hola Jhonattan y Arthur 👋

Este documento tiene dos públicos distintos, porque les toca a cada uno algo
diferente de acá:

- **Jhonattan** (Sub-equipo 3, conmigo): para que continúes y refines el
  proceso de ingesta — el criterio de relevancia, y en conjunto con Arthur,
  el foro de Alura.
- **Arthur** (encabeza Sub-equipo 2, Data Science): para que sepas qué datos
  tenés disponibles, con qué esquema, y qué cuidados tener al consumirlos
  desde el pipeline de LangGraph — y porque el foro de Alura fue idea tuya,
  te pido una mano ahí junto con Jhonattan (ver más abajo).

Andá directo a tu sección si no te interesa el resto.

## Qué hay en esta carpeta (contexto común)

- **`mensajes_comunidad_simulados.json`** — dataset base del MVP obligatorio
  del proyecto. Sigue el esquema exacto que pide el brief del cliente:
  ```json
  {
    "metadata": { ... },
    "lotes": [
      {
        "origen_comunidad": "Discord_Grupo_ONE_G10",
        "periodo_referencia": "Semana_00",
        "interacciones": [
          {"id", "autor", "canal", "tipo", "texto", "fecha", "idioma"}
        ]
      }
    ]
  }
  ```
  `tipo` es uno de: `testimonio` | `pregunta_tecnica` | `comentario` |
  `feedback`. Hoy tiene 4 lotes simulados: Discord, LinkedIn, Formulario de
  feedback, y **Alura_Forum_ONE_G10** (simulado, ver sección de Jhonattan).

- **`ingesta_reddit.py`** — ingesta **real** (no simulada) desde Reddit
  (`r/programacion`, en español), vía RSS/Atom público, sin necesitar API key
  ni login. Es un diferencial opcional (el MVP ya está cubierto con el
  dataset simulado).

Las pruebas viven en `../../tests/` y la documentación de fuentes de datos en
[`../../docs/fuentes_de_datos_acceso.md`](../../docs/fuentes_de_datos_acceso.md).
El panorama completo de cómo esta carpeta se conecta con el resto del sistema
está en [`../../docs/arquitectura_general_sistema.md`](../../docs/arquitectura_general_sistema.md).

---

## Para Jhonattan y Arthur juntos — foro de Alura

Arthur, esta fuente fue idea tuya — quedó anotado que la recomendaste como
posible ingesta real. Te pido tu apoyo acá junto con Jhonattan para dar con
un mecanismo viable, sumando tu mirada de Sub-equipo 2 (qué te serviría
recibir de ahí) a la investigación técnica que ya hizo Jhonattan revisando.

Lo que ya investigué yo: se puede ingerir el foro de Alura
(`app.aluracursos.com/forum/`) igual que Reddit (acceso público, sin
credenciales) y **no es posible tal cual**:

- El foro **requiere login obligatorio** (redirige a `/loginForm`).
- No encontré RSS, API JSON, ni ningún endpoint público sin autenticación.
- Parece un foro hecho a medida por Alura (rutas como
  `/forum/topico-<nombre>-<id>`, `/forum/categoria-<nombre>`,
  `/forum/subcategoria-<nombre>`), no algo estándar como Discourse con API
  documentada.

Por eso decidí (documentado en `docs/fuentes_de_datos_acceso.md`, sección
"Foro de Alura — por qué no se implementó acceso real") **no construir un
scraper autenticado** por ahora: implicaría usar credenciales personales de
Alura de alguien del equipo, probablemente viola los términos de servicio de
una plataforma paga, y es frágil (HTML sin documentar). En su lugar dejé el
lote `Alura_Forum_ONE_G10` simulado en `mensajes_comunidad_simulados.json`
como placeholder, con `canal` inspirado en las rutas reales que vi
(`categoria-python`, `categoria-data-science`, etc.).

**Qué les pediría que evalúen entre los dos:**

1. **Lean primero** `docs/fuentes_de_datos_acceso.md` (sección de Alura) para
   no repetir la misma investigación.
2. Si deciden que vale la pena el acceso real, la vía menos riesgosa sería
   con una **cuenta de prueba dedicada** (no la personal de nadie), y con
   aprobación explícita del equipo antes de escribir cualquier scraper —
   quedó anotado como "trabajo futuro opcional" en el doc.
3. Si se construye, seguir el mismo patrón que `ingesta_reddit.py`: funciones
   puras de transformación (testeables con fixtures, sin red) separadas de
   las funciones que hacen requests, mismo esquema de salida, y filtrar
   contenido borrado/eliminado antes de guardarlo (mismo criterio de
   cumplimiento que usamos con Reddit).
4. Si no se consigue acceso real a tiempo, no pasa nada — el lote simulado ya
   cubre el requisito del MVP; se puede mejorar/ampliar esos datos de
   ejemplo si hace falta más variedad.

---

## Para Jhonattan — implementar el criterio de relevancia

El diseño inicial de `docs/criterio_puntuacion_relevancia.md` ya cuenta con
implementación y pruebas en esta rama. Se ejecuta mediante `ingest.py` y
genera una selección separada; no reemplaza el dataset original. Falta
validar conjuntamente los pesos y conectar la selección con el grafo de IA.

---

## Para Arthur — cómo consumir estos datos desde Sub-equipo 2

Según `docs/arquitectura_general_sistema.md`, Sub-equipo 3 es el punto de
entrada del pipeline: lo que armamos acá es exactamente lo que tu grafo de
LangGraph/LangChain va a leer para el análisis de sentimiento, clasificación
de temas y generación de copy.

**Qué archivo usar:** `mensajes_comunidad_simulados.json` es el dataset
principal — estable, reproducible, y con el esquema oficial del cliente. Es
sobre el que deberían construir y probar el pipeline. `ingesta_reddit.py`
genera datos reales adicionales (`src/data/mensajes_reddit.json`, no
versionado — hay un snapshot de ejemplo en
`../../tests/fixtures/prueba_reddit_controlada.json`), útil como caso de
prueba con datos "sucios" reales, pero no reemplaza al dataset simulado.

**Esquema:** cada archivo tiene `lotes[]`, cada lote con `origen_comunidad`,
`periodo_referencia`, e `interacciones[]`. Cada interacción trae `id`,
`autor`, `canal`, `tipo`, `texto`, `fecha` (ISO 8601 UTC), `idioma` (código
ISO 639-1, mayormente `"es"`).

**El campo `tipo` mapea directo a los casos de uso del proyecto:**

| `tipo` | Para qué te sirve |
|---|---|
| `testimonio` | Detector de Historias de Éxito / Generador de contenido para RRSS |
| `pregunta_tecnica` | Motor de FAQ Dinámico |
| `comentario` / `feedback` | Dashboard de Salud y Sentimiento de la comunidad |

**Cuidados importantes antes de asumir cosas:**

- **El dataset original contiene todas las interacciones.** Para generar
  contenido con mensajes seleccionados, ejecutar `ingest.py` o llamar a
  `procesar_datos`. Para medir sentimiento general y recurrencia, usar la
  entrada completa limpiada con `validar_y_limpiar`; el ranking de marketing
  no representa la distribución de toda la comunidad. Los pesos y la
  propuesta de contrato están documentados para revisión conjunta.
- `tests/fixtures/prueba_reddit_controlada.json` tiene comentarios reales de
  Reddit sin filtrar de lenguaje — puede incluir groserías. Es contenido
  público sin editar a propósito; la curaduría final es responsabilidad del
  panel de Sub-equipo 1, no de esta etapa.
- Todo lo simulado (Discord, LinkedIn, Formulario, Alura) es texto en
  español; Reddit también, salvo que alguien corra el script apuntando a un
  subreddit en otro idioma con `--idioma` explícito.

---

## Cómo verificar lo que ya existe

```
python -m py_compile src/data/ingesta_reddit.py
python tests/verificar_transformacion_reddit.py
python src/data/ingesta_reddit.py --help
python -m json.tool src/data/mensajes_comunidad_simulados.json
```

## Flujo de trabajo

Seguimos la gobernanza del repo: rama `feature/tu-nombre-tarea`, commits,
push, y PR con al menos 1 aprobación (ver README.md de la raíz). Cualquier
duda sobre lo que hice hasta ahora, mejor pregúntenme directo antes de asumir
algo del código — así no duplicamos trabajo.

— Gustavo
