# Validación de ajustes OCI — Semana 3

Fecha: 7 de octubre de 2026. Base: `develop` en `1a9bcaa` (PR #17 integrado).

## Cambios

- El conector admite `insight_mejora`, además de las cuatro rutas existentes.
- Una prueba recorre las rutas de `src/agentes/estado_agente.py` y verifica
  que cada activo conserve su contenido JSON al guardarse con un cliente simulado.
- La prueba manual pasó de `tests/test_storage.py` a
  `scripts/probar_oci_storage.py`, fuera del descubrimiento automático.
- `test_persistencia_oci.py` omite el módulo cuando falta específicamente `oci`.
  Los errores de otras dependencias o del conector siguen siendo visibles.

## Evidencia local

Se utilizó un entorno temporal con Python 3.14 y las dependencias de
`requirements.txt`. No se ejecutó la prueba manual ni se realizaron subidas a OCI.

| Comprobación | Resultado |
| --- | --- |
| Suite completa con OCI (`python -m pytest -q`) | 133 passed |
| Pruebas Cloud con unittest | 6 pruebas correctas |
| Suite completa sin OCI (`python -m pytest -q -rs`) | 127 passed, 1 skipped |
| Módulo Cloud con unittest sin OCI | Omitido con motivo visible |
| Pruebas de tolerancia OCI de DA con `--runxfail` | 29 passed |

La suite completa emite un aviso de deprecación de `google.genai` en Python 3.14.
Las pruebas de DA se tomaron de `feature/jhonattan-validacion-semana3`, commit
`a15631c`, en una copia temporal; no se incorporó esa rama a este cambio.

## Coordinación pendiente

DA debe retirar el `xfail(strict=True)` de
`test_toda_ruta_del_grafo_tiene_destino_en_el_bucket` al integrar esta corrección.
El uso de `--runxfail` en la comprobación anterior exige que todas esas pruebas
pasen normalmente: la carencia de `insight_mejora` ya está resuelta.

Estos ajustes no conectan todavía el guardado al cierre del grafo. Quedan por
coordinar el punto de integración y la señal de aprobación antes de automatizar
las subidas.
