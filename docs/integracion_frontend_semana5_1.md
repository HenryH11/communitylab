# Integración de la página de Plantillas (Semana 5.1)

Rama: `feature/integracion-diseno-semana5.1`, creada desde `origin/develop`
(`10bdc92`, 2026-10-19). Acordado en Discord (18/10): Ramses integra las
plantillas y Eduardo prepara los casos de prueba del chat.

## Estado de partida

- **Diseño:** Jhonattan, rama `feature/frontend-streamlit-local`. Dos vistas del
  boceto: *Plantillas* (el catálogo) y *Resultado* (la plantilla abierta). En su
  rama todo es simulado: el SVG lleva botones transparentes encima y
  `simular_plantilla` arma los borradores sin IA.
- **App funcional:** develop, `src/app/app.py`. Tiene el pipeline real, las
  gráficas y la curaduría (editar, aprobar y guardar en OCI). La curaduría la
  escribió Eduardo en `0908e66`, y Marco y Renato la completaron.
- **Eduardo en la Semana 5.1** (`feature/streamlit-agente-vivo-semana5.1`, sin cambios en `src/app`):
  - QA-1, archivo vacío: `tests/test_archivo_vacio.py`.
  - QA-2, latencia: 23 mensajes en 283 a 392 s con Gemini, es decir, unos 12 a 17 s por mensaje y muy variable.
  - Riesgo que anotó: perder el procesamiento y la curaduría si se fusiona el frontend nuevo sin revisarlo.
  - QA-3, la regresión del frontend nuevo, la deja pendiente hasta que se defina la integración.

**Decisión:** el código sale de develop y el diseño de Jhonattan, rehecho
con componentes nativos de Streamlit. Las plantillas **no vuelven a llamar a
la IA**: muestran y curan lo que el pipeline ya generó. Con la latencia que
midió Eduardo, una llamada por clic no es viable para la demo.

## Las 6 plantillas del boceto frente a lo que genera el pipeline

El pipeline (`nodos_generadores.py`) produce por mensaje `activos_generados` de
cinco tipos: `linkedin`, `boletin`, `preguntas_frecuentes`, `caso_exito` e
`insight_mejora`. Además, el análisis aporta `sentimiento`, `tema_principal`,
`subtema` y `tipo_detectado`. La curaduría solo valida y guarda en OCI esos
cinco tipos (`curaduria_oci.MODELOS_ACTIVO`).

| Plantilla del boceto | Categoría | Fuente real | Estado |
| --- | --- | --- | --- |
| Publicación para LinkedIn | Contenido | activo `linkedin` (`titulo`, `contenido`, `hashtags`) | ✅ Directa, con curaduría y OCI |
| Preguntas de la comunidad | Conocimiento | activo `preguntas_frecuentes` (`tema`, `respuesta`) | ✅ Directa, con curaduría y OCI |
| Sentimiento de comunidad | Analítica | campo `sentimiento` de cada mensaje | ✅ Calculada: gráfica de dona y resumen, sin IA ni curaduría |
| Temas y tendencias | Analítica | `tema_principal` y `subtema` | ✅ Calculada: ranking y gráfica de barras, sin IA |
| Post para Instagram | Contenido | **no hay generador** | ⚠️ Ver opciones |
| Publicación para X | Contenido | **no hay generador** | ⚠️ Ver opciones |

Además hay tres activos reales que el boceto no tiene: **Newsletter**
(`boletin`), **Caso de éxito** (`caso_exito`) y **Oportunidades de mejora**
(`insight_mejora`). Propongo añadirlos como tarjetas en *Contenido para redes*
y *Analíticas*, porque ya funcionan con curaduría y OCI.

### Instagram y X: próximamente

Decisión del 20/10: se muestran en el catálogo como **"Próximamente"**,
sin borradores, hasta que el equipo decida si DS añade las rutas `instagram`
y `x` (prompt, modelo Pydantic y entrada en `MODELOS_ACTIVO`). Cuando existan,
basta con cambiar su `fuente` a `"activo"` en `plantillas_catalogo.py`.

## Diseño de la página

En `st.tabs`, la pestaña **Plantillas** tiene dos partes.

**A. Catálogo**, según la vista "Elige el resultado que necesitas":
- Columna izquierda: buscador (`st.text_input`), categoría (`st.radio`: Todas, Contenido para redes, Analíticas, Preguntas frecuentes) y "Fuente de datos: JSON importado · redes conectadas: no requeridas".
- Cuadrícula de tarjetas en `st.columns(2)`: icono, nombre, etiqueta de categoría, descripción y un **contador real**, por ejemplo "8 borradores". Ordenar: recomendadas o por número de borradores.
- Sin resultado procesado: tarjetas atenuadas con el aviso "Procesa un lote en Datos".

**B. Resultado**, según la vista "Publicación generada a partir de conversaciones":
- Una sub-pestaña por plantilla (`st.tabs`) para abrirla.
- Izquierda: *Configuración*, de solo lectura (lote, formato de salida, objetivo y tono fijos de la plantilla) y la nota "La plantilla define la tarea. No muestra prompts al usuario."
- Centro: *Resultado estructurado*, con un selector de borrador ("1 de 8 · autor · tema"), los editores de la curaduría actual (`st.text_area`) y los botones **Aprobar**, **Copiar contenido** y **Abrir LinkedIn ↗**.
- Derecha: *Vista previa* tipo tarjeta de la red social, con el aviso "La apertura no publica automáticamente".
- Al final, el bloque actual "Activos aprobados listos para OCI" con el botón `guardar_aprobados_oci`.

### Restricciones de las pruebas (no romper)

- `test_curaduria_oci.py` arranca `app.py` con un `resultado` y busca
  `text_area` cuya clave termine en `linkedin_contenido`, botones `…int-demo_linkedin` y
  `guardar_aprobados_oci`. Por eso las sub-pestañas de B tienen que pintarse
  **todas**: `st.tabs` lo hace, mientras que un selector que solo pinta la plantilla activa
  ocultaría los editores. Hay que conservar las claves actuales (`edit_{lote}_{id}_{tipo}_{campo}`,
  `btn_{lote}_{id}_{tipo}`) y **mover** la curaduría a esta pestaña, sin duplicarla: con claves
  repetidas, Streamlit da error.
- El selector "1 de 8" no puede ocultar los editores de los demás
  borradores. Dentro de cada sub-pestaña, cada borrador va en un `st.expander` con el
  primero abierto.
- `test_tolerancia_app.py`: el pipeline sigue en `app.py`, dentro de `try` y sin `st.rerun`.

## Implementado en esta rama

```
src/app/plantillas_catalogo.py  # 9 plantillas (7 activas, Instagram y X próximamente), filtros y contadores; sin Streamlit
src/app/vista_plantillas.py     # catálogo + pestañas de resultado + curaduría + guardado en OCI (movidos desde app.py)
src/app/app.py                  # pipeline y analíticas sin cambios; al final llama a vista_plantillas.render()
tests/test_plantillas.py        # catálogo, contadores, filtros y render con AppTest
```

- La curaduría conserva sus claves y su comportamiento: `test_curaduria_oci.py` pasa sin cambios.
- Los tipos de activo que el catálogo no conozca aparecen en una pestaña "Otros activos", para no perderlos.
- Suite completa: 620 pruebas aprobadas (sin `tests/integracion`, que llama a proveedores reales).

Pendiente: estilos completos del boceto (barra de navegación y paleta global) y las vistas
Inicio, Agente y Ayuda.

## Para Eduardo (QA-3 de Plantillas)

- Abrir Plantillas sin lote procesado: las tarjetas aparecen atenuadas y no hay error.
- Lote sin activos de un tipo: la plantilla muestra "0 borradores" y un mensaje claro.
- Editar, aprobar, volver a editar: la aprobación se pierde (ya está cubierto) y se ve en la plantilla.
- Mojibake en un borrador editado: el error de validación aparece junto al editor.
- X: el texto adaptado nunca pasa de 280 caracteres.
- Abrir la red no publica nada ni guarda en OCI.

## Verificación

```powershell
python -m pytest tests/test_tolerancia_app.py tests/test_curaduria_oci.py tests/test_docker_cloud.py tests/test_plantillas.py -q
```
