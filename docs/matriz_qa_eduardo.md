# Matriz de QA — Semana 3 → 5

**Responsable:** Eduardo Salvador Martínez Hernández
**Fecha de inicio:** 08/10/2026
**Rama activa:** feature/streamlit-curaduria-semana4 (mergeada a develop vía PR #36)
**Última actualización:** 18/10/2026

## Pruebas planificadas y ejecutadas

| # | Prueba | Tipo | Estado | Evidencia | Fecha | Observaciones |
|---|--------|------|--------|-----------|-------|---------------|
| 1 | Carga de JSON válido | Funcional | ✅ Completada | Captura local | 08/10/26 | 23 mensajes cargados correctamente |
| 2 | Carga de JSON inválido | Funcional | ✅ Completada | Código actualizado | 08/10/26 | Fix aplicado en app.py (json.load dentro del try) |
| 3 | Carga de archivo vacío | Funcional | ⏳ Pendiente | - | - | Probar con archivo vacío (ver nota Semana 5.1) |
| 4 | Procesamiento con IA | Funcional | ✅ Completada | Capturas locales + E2E | 08/10 y 18/10/26 | Gemini forzado generó 19 activos de 23 mensajes |
| 5 | Preservación de IDs | Integridad | ✅ Completada | Diagnóstico `resultados_por_id` | 17/10/26 | IDs de entrada coinciden con IDs de salida (23/23) |
| 6 | Tiempo de respuesta | Rendimiento | 🟡 Parcial | Suite completa 52.40s | 18/10/26 | Pendiente medir latencia por mensaje con Gemini |
| 7 | Manejo de errores de IA | Funcional | ✅ Completada | tests/test_fallback_*.py (verde) + incidente NVIDIA 410 | 17-18/10/26 | Fallback NVIDIA→Gemini probado en producción local |
| 8 | Seguridad de API Key | Seguridad | ✅ Completada | .gitignore activo | 08/10/26 | .env no subido al repositorio |
| 9 | Validación del contrato JSON | Integridad | ✅ Completada | tests/test_contratos_arquitectura.py (verde) | 18/10/26 | Contrato de 7 campos validado por suite automatizada |
| 10 | Pruebas de estrés | Capacidad | 🟡 Cubierta por equipo | PR #41 (DA - Gustavo) | 18/10/26 | Validado por DA; Eduardo no ejecutó local |
| 11 | Gobernanza de Git | Agilidad | ✅ Completada | PR #19, #24, #25, #36 fusionados | 11-17/10/26 | Aprobaciones formales en GitHub |
| 12 | Pruebas cruzadas E2E | Integración | ✅ Completada | Flujo local completo | 18/10/26 | Data → IA → UI → Curaduría → Paquete OCI |

## Resumen

- **Completadas:** 9
- **Parciales / cubiertas por equipo:** 2 (6, 10)
- **Pendientes:** 1 (3)
- **Prioridad alta resuelta:** 5, 9, 12 ✅
- **Prioridad media:** 3 pendiente, 6 parcial, 7 resuelta ✅
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
- **Reportado a:** #data-scientist (equipo DS — Arnold ya lo había detectado el 14/10, fix pendiente en develop).

---

## Cierre Semana 5 — Suite de QA en verde (18 oct 2026)

**Objetivo:** Correr por última vez la batería completa de pruebas automatizadas y documentar reporte final libre de regresiones.

**Comando ejecutado:**

```powershell
python -m pytest -q