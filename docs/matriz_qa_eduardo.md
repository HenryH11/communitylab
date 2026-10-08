# Matriz de QA - Semana 3

**Responsable:** Eduardo Salvador Martínez Hernández
**Fecha de inicio:** 08/10/2026
**Rama:** feature/streamlit-conexion-ia

## Pruebas planificadas

| # | Prueba | Tipo | Estado | Evidencia | Fecha | Observaciones |
|---|--------|------|--------|-----------|-------|---------------|
| 1 | Carga de JSON válido | Funcional | ✅ Completada | Captura local | 08/10/26 | 23 mensajes cargados |
| 2 | Carga de JSON inválido | Funcional | ✅ Completada | Código actualizado | 08/10/26 | Fix aplicado en app.py |
| 3 | Carga de archivo vacío | Funcional | ⏳ Pendiente | - | - | Probar con archivo vacío |
| 4 | Procesamiento con IA | Funcional | ✅ Completada | Captura local | 08/10/26 | Gemini generó activos |
| 5 | Preservación de IDs | Integridad | ⏳ Pendiente | - | - | Verificar que IDs entrada = salida |
| 6 | Tiempo de respuesta | Rendimiento | ⏳ Pendiente | - | - | Medir con 23 mensajes |
| 7 | Manejo de errores de IA | Funcional | ⏳ Pendiente | - | - | Simular fallo de Gemini |
| 8 | Seguridad de API Key | Seguridad | ✅ Completada | .gitignore activo | 08/10/26 | .env no subido al repo |
| 9 | Validación del contrato JSON | Integridad | ⏳ Pendiente | - | - | Verificar 7 campos |
| 10 | Pruebas de estrés | Capacidad | ⏳ Pendiente | - | - | Probar con 100+ mensajes |
| 11 | Gobernanza de Git | Agilidad | ✅ Completada | PR #19 abierto | 08/10/26 | Commits con Conventional Commits |
| 12 | Pruebas cruzadas E2E | Integración | ⏳ Pendiente | - | - | Data → IA → UI → OCI |

## Resumen

- **Completadas:** 4
- **Pendientes:** 8
- **Prioridad alta:** 2, 5, 9
- **Prioridad media:** 3, 6, 7, 12
- **Prioridad baja:** 10

## Próximos pasos

1. Ejecutar pruebas 5, 9, 10 (integridad, contrato, estrés).
2. Documentar resultados en esta matriz.
3. Publicar en Discord como evidencia.