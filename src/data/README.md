# Sub-equipo 3 — Ingesta y Procesamiento de Datos

Hola Jhonattan 👋

Este documento resume dónde quedó el trabajo de ingesta hasta ahora (Semana
0) y te deja el contexto para que avances con la ingesta del **foro de
Alura**, que es lo que falta de nuestro sub-equipo.

## Qué hay en esta carpeta

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
  feedback, y **Alura_Forum_ONE_G10** (este último con 5 interacciones de
  ejemplo que armé a mano — ver más abajo por qué son simuladas y no reales).

- **`ingesta_reddit.py`** — ingesta **real** (no simulada) desde Reddit, vía
  RSS/Atom público, sin necesitar API key ni login. Es un diferencial
  opcional del proyecto (el MVP ya está cubierto con el dataset simulado).
  Está aquí como referencia de patrón si te sirve de base para Alura: separa
  funciones puras (parseo/transformación, testeables sin red) de las
  funciones con efecto de red, arma el mismo esquema de `interacciones`, y
  descarta contenido borrado antes de guardarlo.

Las pruebas de este código viven en `../../tests/` (no en `src/data/` — ya
existe carpeta dedicada a tests en el repo) y la documentación de fuentes de
datos en `../../docs/fuentes_de_datos_acceso.md`.

## Lo que falta: ingesta real del foro de Alura

Investigué si se podía ingerir el foro de Alura
(`app.aluracursos.com/forum/`) igual que hicimos con Reddit (acceso público,
sin credenciales) y **no es posible tal cual**:

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

### Qué te pediría que evalúes

1. **Leé primero** `docs/fuentes_de_datos_acceso.md` (sección de Alura) para
   no repetir la misma investigación.
2. Si el equipo decide que vale la pena el acceso real, la vía menos
   riesgosa sería con una **cuenta de prueba dedicada** (no la personal de
   nadie), y con aprobación explícita del equipo antes de escribir cualquier
   scraper — quedó anotado como "trabajo futuro opcional" en el doc.
3. Si se construye, seguí el mismo patrón que `ingesta_reddit.py`: funciones
   puras de transformación (testeables con fixtures, sin red) separadas de
   las funciones que hacen requests, mismo esquema de salida
   (`origen_comunidad`/`periodo_referencia`/`interacciones`), y filtrar
   contenido borrado/eliminado antes de guardarlo (mismo criterio de
   cumplimiento que usamos con Reddit).
4. Si no se consigue acceso real a tiempo, no pasa nada — el lote simulado ya
   cubre el requisito del MVP; podés simplemente mejorar/ampliar esos datos
   de ejemplo si hace falta más variedad para que Sub-equipo 2 (IA) tenga con
   qué probar.

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
duda sobre lo que hice hasta ahora, mejor preguntame directo antes de asumir
algo del código — así no duplicamos trabajo.

— Gustavo
