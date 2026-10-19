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
| 3 | Carga de archivo vacío | Funcional | ✅ Completada | `tests/test_archivo_vacio.py` + fixtures | 18/10/26 | 2 passed. Pipeline no rompe con `interacciones: []`; error claro si falta el campo |
| 4 | Procesamiento con IA | Funcional | ✅ Completada | Capturas locales + E2E | 08/10 y 18/10/26 | Gemini forzado generó 19 activos de 23 mensajes |
| 5 | Preservación de IDs | Integridad | ✅ Completada | Diagnóstico `resultados_por_id` | 17/10/26 | IDs de entrada coinciden con IDs de salida (23/23) |
| 6 | Tiempo de respuesta | Rendimiento | ✅ Completada | `reports/latencia_semana51.json` | 18/10/26 | 282.98s total / 23 msgs = 12,303 ms/mensaje (Gemini) |
| 7 | Manejo de errores de IA | Funcional | ✅ Completada | `tests/test_fallback_*.py` + incidente NVIDIA 410 | 17-18/10/26 | Fallback NVIDIA→Gemini probado en producción local |
| 8 | Seguridad de API Key | Seguridad | ✅ Completada | `.gitignore` activo (`.env`, `.env.*`, `*.pem`, `*.key`) | 08/10/26 | `.env` no subido al repositorio |
| 9 | Validación del contrato JSON | Integridad | ✅ Completada | `tests/test_contratos_arquitectura.py` (verde) | 18/10/26 | Contrato de 7 campos validado por suite automatizada |
| 10 | Pruebas de estrés | Capacidad | ✅ Cubierta por equipo | PR #41 (DA - Gustavo), `tests/test_estres_lotes.py` | 18/10/26 | Validado por DA; corrida con IA en `estres_lotes_ds.json` de DS |
| 11 | Gobernanza de Git | Agilidad | ✅ Completada | PR #19, #24, #25, #36, #43 fusionados | 11-18/10/26 | Aprobaciones formales en GitHub |
| 12 | Pruebas cruzadas E2E | Integración | ✅ Completada | Flujo local completo | 18/10/26 | Data → IA → UI → Curaduría → Paquete OCI |

## Resumen

- **Completadas:** 11
- **Cubiertas por equipo:** 1 (10)
- **Pendientes:** 0
- **Prioridad alta resuelta:** 5, 9, 12 ✅
- **Prioridad media resuelta:** 3, 6, 7 ✅
- **Prioridad baja:** 10 cubierta por DA

---

## Cierre Semana 4 — Curaduría humana (17–18 oct 2026)

**Objetivo:** Implementar curaduría humana con `st.text_area` para que marketing edite y apruebe activos antes de enviarlos a OCI.

**Resultados:**

- [x] Implementación de `st.text_area` editable por activo
- [x] Botón "✅ Aprobar" por activo con validación
- [x] Lista "📦 Activos aprobados listos para OCI"
- [x] PR #36 fusionado a develop por Henry (17/10/26)
- [x] Validación de hashtags (3–4, con `#`) — PR #42
- [x] Validación de mojibake antes de guardar — PR #42

**Incidente detectado y resuelto:**

- **Bug:** modelos `meta/llama-3.3-70b-instruct` y `meta/llama-3.1-8b-instruct` deprecados (EOL 26 ago 2026) → error 410 Gone en todas las generaciones.
- **Causa raíz:** modelos NVIDIA NIM obsoletos en la configuración por defecto de DS.
- **Workaround aplicado:** `COMMUNITYLAB_PROVEEDOR_GENERACION=gemini` en `.env`.
- **Resultado:** 0 activos → 19 activos generados correctamente.
- **Reportado a:** `#data-scientist` el 16/10. Arnold ya lo había detectado el 14/10; fix aplicado en PR #32 (Nemotron Super para rápido/estándar y razonamiento).

---

## Cierre Semana 5 — Suite de QA en verde (18 oct 2026)

**Objetivo:** Correr por última vez la batería completa de pruebas automatizadas y documentar reporte final libre de regresiones.

**Comando ejecutado:**

```powershell
python -m pytest -q