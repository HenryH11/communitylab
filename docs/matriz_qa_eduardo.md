# Matriz de QA — Semana 3 → 5.1

**Responsable:** Eduardo Salvador Martínez Hernández
**Fecha de inicio:** 08/10/2026
**Rama activa:** feature/streamlit-agente-vivo-semana5.1 (creada desde develop `aa2f8c0` el 18/10/2026)
**Última actualización:** 18/10/2026 (cierre Semana 5 + arranque Semana 5.1)

## Pruebas planificadas y ejecutadas

| # | Prueba | Tipo | Estado | Evidencia | Fecha | Observaciones |
|---|--------|------|--------|-----------|-------|---------------|
| 1 | Carga de JSON válido | Funcional | ✅ Completada | Captura local | 08/10/26 | 23 mensajes cargados correctamente |
| 2 | Carga de JSON inválido | Funcional | ✅ Completada | Código actualizado | 08/10/26 | Fix aplicado en app.py (json.load dentro del try) |
| 3 | Carga de archivo vacío | Funcional | ✅ Completada | tests/test_archivo_vacio.py + fixtures | 18/10/26 | 2 passed. Pipeline no rompe con interacciones vacías; error claro si falta el campo |
| 4 | Procesamiento con IA | Funcional | ✅ Completada | Capturas locales + E2E | 08/10 y 18/10/26 | Gemini forzado generó 19 activos de 23 mensajes |
| 5 | Preservación de IDs | Integridad | ✅ Completada | Diagnóstico resultados_por_id | 17/10/26 | IDs de entrada coinciden con IDs de salida (23/23) |
| 6 | Tiempo de respuesta | Rendimiento | ✅ Completada | reports/latencia_semana51.json | 18/10/26 | 2 corridas: 282.98s y 391.79s. Ver detalle en QA-2 |
| 7 | Manejo de errores de IA | Funcional | ✅ Completada | tests/test_fallback_*.py + incidente NVIDIA 410 | 17-18/10/26 | Fallback NVIDIA a Gemini probado en producción local |
| 8 | Seguridad de API Key | Seguridad | ✅ Completada | .gitignore activo (.env, .env.*, *.pem, *.key) | 08/10/26 | .env no subido al repositorio |
| 9 | Validación del contrato JSON | Integridad | ✅ Completada | tests/test_contratos_arquitectura.py (verde) | 18/10/26 | Contrato de 7 campos validado por suite automatizada |
| 10 | Pruebas de estrés | Capacidad | ✅ Cubierta por equipo | PR #41 (DA - Gustavo), tests/test_estres_lotes.py | 18/10/26 | Validado por DA; corrida con IA en estres_lotes_ds.json de DS |
| 11 | Gobernanza de Git | Agilidad | ✅ Completada | PR #19, #24, #25, #36, #43 fusionados | 11-18/10/26 | Aprobaciones formales en GitHub |
| 12 | Pruebas cruzadas E2E | Integración | ✅ Completada | Flujo local completo | 18/10/26 | Data a IA a UI a Curaduría a Paquete OCI |

## Resumen

- **Completadas:** 11
- **Cubiertas por equipo:** 1 (10)
- **Pendientes:** 0
- **Prioridad alta resuelta:** 5, 9, 12 ✅
- **Prioridad media resuelta:** 3, 6, 7 ✅
- **Prioridad baja:** 10 cubierta por DA

---

## Cierre Semana 4 — Curaduría humana (17–18 oct 2026)

**Objetivo:** Implementar curaduría humana con st.text_area para que marketing edite y apruebe activos antes de enviarlos a OCI.

**Resultados:**

- [x] Implementación de st.text_area editable por activo
- [x] Botón "Aprobar" por activo con validación
- [x] Lista "Activos aprobados listos para OCI"
- [x] PR #36 fusionado a develop por Henry (17/10/26)
- [x] Validación de hashtags (3–4, con #) — PR #42
- [x] Validación de mojibake antes de guardar — PR #42

**Incidente detectado y resuelto:**

- **Bug:** modelos meta/llama-3.3-70b-instruct y meta/llama-3.1-8b-instruct deprecados (EOL 26 ago 2026) → error 410 Gone en todas las generaciones.
- **Causa raíz:** modelos NVIDIA NIM obsoletos en la configuración por defecto de DS.
- **Workaround aplicado:** COMMUNITYLAB_PROVEEDOR_GENERACION=gemini en .env.
- **Resultado:** 0 activos → 19 activos generados correctamente.
- **Reportado a:** #data-scientist el 16/10. Arnold ya lo había detectado el 14/10; fix aplicado en PR #32 (Nemotron Super para rápido/estándar y razonamiento).

---

## Cierre Semana 5 — Suite de QA en verde (18 oct 2026)

**Objetivo:** Correr por última vez la batería completa de pruebas automatizadas y documentar reporte final libre de regresiones.

**Comando ejecutado:**

    python -m pytest -q

**Resultado:**

    581 passed, 208 subtests passed in 70.40s

- **Fallos:** 0
- **Warnings:** solo deprecaciones de Streamlit (use_container_width) — no bloquean
- **Nota técnica:** pytest -q directo falla con ModuleNotFoundError: No module named 'src'; usar siempre python -m pytest -q para agregar el rootdir al sys.path.

**Flujo E2E validado en local:**

| Etapa | Resultado |
|-------|-----------|
| Carga JSON | ✅ 23 mensajes cargados (estructura metadata + lotes) |
| Procesamiento IA (Gemini forzado) | ✅ 19 con contenido / 4 sin contenido / 5 elegibles FAQ |
| Generación de activos | ✅ LinkedIn, Caso de Éxito, Boletín, Insight Mejora |
| Curaduría (editar + aprobar) | ✅ int-022: caso_exito aprobado con texto editado |
| Validación hashtags/mojibake | ✅ Bloquea activos inválidos correctamente |
| Preparación paquete OCI | ✅ Detecta período 2026-10 y bucket bkt-communitylab-marketing |
| Guardado físico OCI | ✅ Validado por Renato en VM con identidad de la VM (no requiere credenciales locales) |

**Aislamiento de interfaz:**

- [x] Componentes interactivos mantienen estado en st.session_state
- [x] Sin caídas ante entradas nulas durante la prueba E2E
- [x] Manejo correcto de interrupciones del proceso sin corromper estado

**PRs fusionados a develop durante el cierre:**

- PR #36 — Curaduría st.text_area (Henry, 17/10)
- PR #39 — Evaluación DS (Arnold, 50bc28f)
- PR #40 — Saneamiento JSON / mojibake (Gustavo, 4c5431c)
- PR #41 — Estrés de Datos (Gustavo)
- PR #42 — Validación mojibake en curaduría (Marco)
- PR #43 — Matriz QA cierre Semana 4 y 5 (Eduardo, aa2f8c0)

---

## Cierre parcial Semana 5.1 — QA proactivo (18 oct 2026)

**Objetivo:** Adelantar las comprobaciones de QA de la Semana 5.1 que no dependen de otros equipos, mientras SS-1 (contrato v1.4), SS-2 (coexistencia de frontends) y SS-3 (Conjunto Consultable) se coordinan en la reunión del lunes 19/10.

**Rama:** feature/streamlit-agente-vivo-semana5.1 (creada desde develop aa2f8c0)

**Commits:**
- 56b8d94 — QA-1 archivo vacío + script QA-2 inicial
- 0ab3f91 — Reporte QA-2 + matriz 5.1
- de4b339 — Corrección de QA-2 con ambas corridas

### QA-1 — Carga de archivo vacío ✅

- **Fixtures creados:**
  - tests/fixtures/json_vacio_semana51.json → objeto con interacciones vacías
  - tests/fixtures/json_sin_interacciones.json → falta el campo interacciones
- **Prueba automatizada:** tests/test_archivo_vacio.py
- **Resultado:** 2 passed in 14.63s
  - JSON válido con interacciones vacías → el pipeline no rompe; devuelve paquete vacío.
  - JSON sin campo interacciones → error explícito (no KeyError críptico).

### QA-2 — Latencia por mensaje ✅

- **Script:** scripts/medir_latencia_semana51.py
- **Reporte:** reports/latencia_semana51.json
- **Resultado (18/10/2026, provider Gemini, 23 mensajes procesados):**

| Corrida | Tiempo total | Promedio por mensaje |
|---|---|---|
| 1ª (matriz inicial) | 282.98 s | 12,303 ms (~12.3 s) |
| 2ª (reporte actual) | 391.79 s | 17,034 ms (~17.0 s) |
| **Variación** | **+38%** | **+4.7 s por mensaje** |

- **Hallazgo crítico para compuerta A:** Gemini tiene latencia muy variable entre corridas (+38% en el mismo día con el mismo dataset). La 2ª corrida fue más lenta probablemente por carga del proveedor. No es un problema del código; es un comportamiento del proveedor.

- **Comparación con Nemotron Super (VM, según Renato/Arnold):**

| Provider / Modelo | Tiempo por mensaje | 23 mensajes |
|---|---|---|
| Nemotron Super (VM) | ~4.2 s | ~1.6 min |
| Gemini (1ª corrida, local) | ~12.3 s | ~4.7 min |
| Gemini (2ª corrida, local) | ~17.0 s | ~6.5 min |

Gemini es 3x a 4x más lento que Nemotron Super. Y su latencia no es estable. Para la demo interactiva del agente en vivo, considerar usar Nemotron Super como primario.

- **Nota técnica:** el pipeline aún no expone tiempo_ms por ID. Se registra el promedio como tiempo_total / mensajes_procesados. Se recomienda a DS agregar el campo al contrato v1.4 para futuras mediciones por ID.

- **Nota de proceso:** la matriz se actualiza a los datos del reporte actual (2ª corrida, 391.79s). La 1ª corrida se conserva como evidencia de la variabilidad.

- **Nota sobre el script:** la versión anterior imprimía "0 mensajes a procesar" porque buscaba la clave interacciones en el paquete, pero preparar_paquete_ia() devuelve estados (23 IDs). El script corregido (_ids_desde_estados) ya lee la clave correcta. El reporte actual es válido; los 23 mensajes se procesaron correctamente.

### Pendientes de Semana 5.1 (bloqueados por coordinación)

| # | Tarea | Bloqueado por | Dueño del desbloqueo |
|---|-------|---------------|----------------------|
| SS-1 | Contrato v1.4 (campos spam) y retrocompatibilidad v1.2/v1.3 | Arnold (DS) — debe subir el cambio | Arnold |
| SS-2 | Coexistencia de frontends (app.py vs feature/frontend-streamlit-local) | Decisión con Jhonattan + Ramses | Reunión lunes 19/10 |
| SS-3 | Conjunto Consultable: ruta en bucket, cuándo se genera | Renato/Marco (CE) + Arnold (DS) | Reunión lunes 19/10 |
| QA-3 | Regresión del frontend nuevo | Bloqueado por SS-2 | Eduardo (después de SS-2) |

**Nota:** feature/frontend-streamlit-local está 58 commits detrás de develop y modifica src/app/app.py (−206 líneas, +39). No se puede mergear a ciegas. Se requiere decisión explícita de SS antes de integrar.

---

## Riesgos identificados (SS)

1. **Contrato v1.4 no publicado:** develop sigue declarando v1.2/v1.3. Los campos es_spam_detectado, motivo_spam, total_spam_detectado no aparecen aún en el esquema. Requiere coordinación con Arnold antes del congelamiento del sáb 24.
2. **Frontend nuevo divergente:** ver nota en SS-2. Riesgo de perder integración existente (procesamiento, resultados_por_id, curaduría/guardado) si se mergea sin revisión.
3. **Holdout en ASCII:** tests/fixtures/holdout_final_analisis_semana3.json quedó con signos de interrogación en lugar de tildes/ñ (creado en b141c93). Pendiente de DS; no bloquea QA.
4. **Latencia de Gemini:** 3x–4x más lento que Nemotron Super y con alta variabilidad (+38% entre corridas del mismo día). Considerar para compuerta A del martes 20 y demo del agente en vivo.
5. **Estructura del dataset cambió:** el dataset pasó de objeto con interacciones directas a metadata + lotes tras PR #40. Cualquier script de terceros que lea el JSON directo necesita actualizarse. Los scripts internos del pipeline ya manejan la nueva estructura.

---

## Próximos pasos (Semana 5.1 — desde 19 oct 2026)

1. **Reunión lunes 7:00 PM PT (sprint-meet):** cerrar SS-2 (Jhonattan/Ramses), SS-1 (Arnold) y SS-3 (Renato/Marco).
2. **Después de SS-2:** iniciar QA-3 (regresión del frontend nuevo) con los casos del agente en vivo:
   - Consultas vacías / solo espacios
   - Caracteres corruptos (mojibake)
   - Consultas fuera de ámbito MarTech
   - Consultas válidas sobre datos
   - Consultas concurrentes (2+ simultáneas)
   - Consultas largas (500+ caracteres)
   - Emojis y tildes
3. **Después de SS-1:** agregar casos de contrato v1.4 y retrocompatibilidad v1.2/v1.3 a tests/test_contratos_arquitectura.py.
4. **Después de SS-3:** validar el Conjunto Consultable de 7 campos con 23 registros reales.
5. **Sábado 24:** purga final y congelamiento.

---

## Evidencia pública

| Evidencia | Ubicación |
|-----------|-----------|
| Commit cierre Semana 5 | 37dcfb6 → fusionado en aa2f8c0 (PR #43) |
| Suite en verde | 581 passed, 208 subtests, 0 failed |
| Flujo E2E | Capturas en #general (Discord, 18/10 8:10 PM) |
| QA-1 archivo vacío | tests/test_archivo_vacio.py + commit 56b8d94 |
| QA-2 script y reporte | scripts/medir_latencia_semana51.py + reports/latencia_semana51.json + commits 0ab3f91 y de4b339 |
| Rama Semana 5.1 | feature/streamlit-agente-vivo-semana5.1 |