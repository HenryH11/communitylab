# Semana 4: preparación de la auditoría de consistencia

Preparado el 12 y actualizado el 15 de octubre de 2026. DA: Gustavo y Jhonattan.

**Estado: auditoría técnica de la entrega real de DS recibida y completada
offline. Sin discrepancias bloqueantes detectadas en 35 activos. Pendientes el
visto bueno humano de DA, la curaduría, el estrés y la evidencia OCI del equipo.**

## Revisión cruzada de Jhonattan · 15 de octubre

### Versiones y alcance actual

- `develop`: `46f6d41`; los PR #30 y #31 ya están fusionados.
- Auditor v2 de Gustavo, PR #33: `8d8d8b1`, todavía en borrador al revisar.
- DS, PR #32: `73c5175`. La documentación identifica `5162e61` como el código
  que produjo su última entrega; `73c5175` solo actualiza documentación.
- Rama de ajustes: `feature/jhonattan-ajustes-auditor-v2`, creada desde
  `8d8d8b1` (#33), con únicamente el commit de ajustes de DA trasladado mediante
  `cherry-pick`. No incluye los commits del PR #32 ni el merge `424af25`.
- La combinación con DS se validó separadamente en la rama local
  `feature/jhonattan-revision-auditoria-semana4`, que sí incorpora #32 mediante
  `424af25`. Los resultados de esa combinación no se atribuyen a la rama limpia.

Solo se trabaja en Semana 4. No se modifica el dataset de referencia, el frontend
ni la deduplicación reservada para Semana 5. Los cambios propios de esta revisión
son el auditor de DA, sus pruebas y este reporte.

### Resultado de la revisión del auditor v2

| Punto | Evaluación técnica y acción |
| --- | --- |
| `comentario_interno` | Útil para notas como «mensaje original» o «la pregunta no proporciona». Se mantiene como señal para revisión: «Si no se especifica un índice…» puede ser una explicación técnica legítima. No se utiliza para rechazar automáticamente. |
| `hashtag_sin_almohadilla` | Correcto revisarlo aparte: el aplanado omite hashtags. DS añadió normalización en #32, pero debe comprobarse la salida real. La regla solo verifica el prefijo; no certifica todas las convenciones de hashtags. |
| `DataFrame` | No se añade una excepción global. La regla de mayúsculas es heurística. Una fuente técnica aprobada puede respaldar ese término, conservando alertas para otras entidades nuevas. La aprobación factual corresponde a revisión humana. |
| Exclusiones del informe de DA | **Corregido en esta rama.** `motivos` explica selección de contenido y no equivale a exclusión de IA. Se usan `incluido_sentimiento` y `motivos_exclusion_sentimiento`; para informes antiguos se filtran solo los cinco motivos de ruido del contrato de DA. |
| Exclusión explícita sin motivo | **Corregido en esta rama.** `incluido_sentimiento=False` se conserva aunque falte la explicación, con el marcador `excluido_por_data`. |
| IDs duplicados | **Corregido en esta rama.** Se rechaza una entrega con IDs repetidos antes de comparar activos. Antes, el índice podía sustituir silenciosamente un original por otro. No es deduplicación semántica. |

Se añadieron 11 casos de prueba al auditor. Ocho reprodujeron fallos antes de la
corrección; los otros verifican límites de la heurística y coherencia con el
contrato de DA. El auditor pasa de 31 a **42 pruebas**. Conserva únicamente
dependencias de la biblioteca estándar en ejecución.

### Conexión comprobada con el exportador de DS

Se añadió una prueba al recorrido existente que ejecuta:

```text
Datos sintéticos → preparar_paquete_ia → procesamiento/grafo
→ construir_paquete_auditoria de DS → auditar_entrega de DA
```

Resultado: **30 mensajes sintéticos**, 10 excluidos por spam, 20 válidos y
**40 activos auditados sin alertas**. El auditor no modifica la entrega y no
asigna decisiones humanas. Las respuestas y las trazas de proveedor se simulan;
la red está bloqueada en el archivo de pruebas. Esto verifica compatibilidad
entre módulos, no calidad ni latencia de NVIDIA/Gemini reales.

La prueba del exportador se omite mediante `pytest.mark.skipif` si #32 no está
disponible, sin importarlo durante la recolección. Se activa al incorporar DS.

Validación local del 15 de octubre, con `.env` desactivado y sin red real:

| Ejecución | Resultado |
| --- | --- |
| Auditor y recorrido de Semana 4, con DS #32 | 50 aprobadas |
| Suite completa: `develop` `46f6d41` + #33 `8d8d8b1` + ajustes DA, sin #32 | **474 aprobadas, 132 subpruebas aprobadas; 0 fallidas, 1 omitida** (exportador de DS aún ausente) |
| Suite completa: la misma combinación + DS #32 `73c5175` | **502 aprobadas, 132 subpruebas aprobadas; 0 fallidas, 0 omitidas** |
| `unittest discover` en la rama limpia | 91 pruebas, OK |

Las dos suites completas se repitieron antes de publicar. Esta diferencia es
esperada: la rama limpia no transporta las funciones ni las pruebas de DS #32.
No se deben anunciar 502 aprobadas al ejecutar solo la rama de ajustes.

La suite incluye respuestas simuladas y pruebas de contratos. No se hicieron
llamadas reales a IA ni escrituras en OCI. El primer intento de las 31 pruebas
originales de Gustavo tuvo un error al crear temporales en el entorno restringido
de Windows (30 aprobadas, 1 error de preparación). Fuera de ese entorno y con
`--basetemp` dentro de `salida/`, las 31 pasaron antes de añadir los ajustes.

### Tercera corrida de DS: entrega final recibida y auditada · 15 de octubre

El usuario entregó `auditoria_semana4.json` como archivo completo desde Descargas.
Se conservó una copia byte a byte en
`salida/auditoria_jhonattan_semana4/2026-10-15/auditoria_ds_5162e61_completa.json`.
El primer pegado estaba cortado dentro de `int-017` y no era JSON válido: no se
reparó ni completó por suposición. Su revisión parcial queda como antecedente,
separada y reemplazada para las conclusiones por este archivo completo.

| Identificación de la evidencia | Valor |
| --- | --- |
| JSON | Versión 1.2; válido, UTF-8; 60 897 bytes |
| SHA-256 del archivo completo | `456f5d874c36f767ef546831a3b9bb2efaf3cbfb1bd0fd61bf1b616410a12a57` |
| Código DS declarado en el JSON | `5162e6108b4e5ef96d91804c3193b955a0ced69b` |
| Ejecución declarada | `d5e2c90405464523b2779249540d1fd3`, `2026-10-15T04:48:53.756484+00:00` |
| SHA-256 del dataset, contrastado con el archivo local | `63f19b4756d26c4f4fd64f6b289ada8fe1bee83c5f1ef1194f6009c3a7bfe045` |
| SHA-256 del auditor local usado | `dd0f7b095236814895cea8269dc55b42016add56ad1eabfce1b2498a070ac221` |

Se verificaron los 23 IDs únicos y todos los textos/metadatos contra el dataset;
se recalcularon puntajes, elegibilidad, motivos y exclusiones con la preparación
actual de DA y la fecha de referencia declarada. Coinciden. Los 23 análisis y
35 activos validan con los modelos Pydantic; sus rutas coinciden con el enrutador.
Los campos adicionales `area` y `canal_recomendado` coinciden con los metadatos
que añade el generador. Los conteos y distribuciones del resumen se contrastaron
con los registros. Las 58 trazas (23 análisis + 35 activos) son internamente
coherentes con los modelos y proveedores declarados; todas indican NVIDIA sin
fallback. No hay errores, fallos, pendientes ni exclusiones en este dataset.

Auditor ejecutado sin fuentes excluyentes adicionales ni llamadas a IA:

```powershell
python -B scripts/auditoria_consistencia.py `
  --entrega salida/auditoria_jhonattan_semana4/2026-10-15/auditoria_ds_5162e61_completa.json `
  --proveedor por_activo --version-codigo 5162e6108b4e5ef96d91804c3193b955a0ced69b
```

| Modelo declarado en cada activo | Activos | Con alertas |
| --- | --- | --- |
| `nvidia/nemotron-3-super-120b-a12b` | 18 | 0 |
| `nvidia/nemotron-3.5-lightning-30b-a3b` | 17 | 0 |
| Total | **35** | **0** |

Las rutas son 8 casos de éxito, 8 boletines, 8 publicaciones LinkedIn, 9 FAQ y
2 insights. La comparación técnica asistida de los 35 activos contra su fuente
no detectó discrepancias bloqueantes. No se modifica ninguna salida de DS.

### Verificación de las observaciones anteriores

| Observación de las corridas históricas | Resultado en el archivo completo de `5162e61` |
| --- | --- |
| `int-015`, FAQ redactada como instrucción | Respuesta final prudente; no inventa diferencias institucionales. Sin instrucción filtrada. |
| `int-011`, `int-014`, `int-018`, testimonios sin activos | Se detectan como testimonios y cada uno genera caso de éxito, boletín y LinkedIn. |
| `int-011` / `int-014`, notas internas en caso de éxito | No aparecen; se conservan oportunidad de colaborar y comprensión de conceptos sin inventar logros. |
| `int-004`, `int-007`, `int-010`, `int-013`, metacomentarios en FAQ | No aparecen; las respuestas remiten a información oficial sin precios, fechas ni acuerdos inventados. |
| `int-003`, hashtags sin `#` | Los tres hashtags llevan `#`. |
| `int-017`, alerta heurística por `DataFrame` | El término ya no aparece en la nueva FAQ; no hizo falta una excepción ni fuente aprobada para silenciarlo. |
| `int-020`, pérdida de insight por detectar comentario | Se detecta `feedback`, genera `insight_mejora` y conserva la propuesta de ejercicios. |
| `int-023`, casi duplicado de `int-002` | Continúa presente, como estaba acordado. La deduplicación se mantiene fuera de Semana 4. |

La revisión registra especial atención a «menos de 3 meses» (`int-001`), seis
semanas (`int-003`), «seleccionada» frente a «contratada» (`int-022`) y oportunidad
de colaborar frente a colaboración ya realizada (`int-011`). Los activos
conservan estas distinciones. Los otros hechos de los testimonios e insights
tampoco presentan añadidos bloqueantes en esta revisión.

Las cuatro FAQ técnicas (`int-002`, `int-023`, `int-017`, `int-021`) se contrastaron
con [LangGraph: conditional edges](https://docs.langchain.com/oss/python/langgraph/graph-api#conditional-edges),
[Python: indentación](https://docs.python.org/3/reference/lexical_analysis.html#indentation),
[W3C: Flexbox](https://www.w3.org/TR/css-flexbox-1/) y
[W3C: Grid](https://www.w3.org/TR/css-grid-1/), según el caso. Son explicaciones
generales; no prueban una solución específica sin ver el código del usuario.

### Evidencia local y límites de la conclusión

En `salida/auditoria_jhonattan_semana4/2026-10-15/` se conservan:

- `auditoria_ds_5162e61_completa.json`: copia íntegra del archivo recibido;
- `validacion_entrega_completa.json`: identidad, huellas y controles de contrato;
- `reporte_automatico_completo.json` / `.md`: 35 filas, cero alertas;
- `revision_tecnica_asistida_completa.json` / `.md`: comparación y justificación
  por `(ID, ruta)`, con las 35 decisiones humanas todavía pendientes.

Los artefactos completos permanecen fuera de Git por la regla `salida/`; el
reporte versionado conserva su identificación y resultados. La revisión asistida
no rellena `decision_humana` ni `justificacion`, ni suplanta el visto bueno del
subequipo o la curaduría.

No se recibieron los logs originales ni se volvió a llamar al proveedor. El SHA
de ejecución, `working_tree_limpio` y `reproducible` son declaraciones del JSON,
no una reproducción independiente de la corrida. El JSON no registra el timeout
efectivo; no puede comprobarse una posible variable de entorno de aquella sesión.
Tampoco certifica latencia, calidad general del modelo, etiquetas contra un
ground truth humano conciliado, curaduría, estrés o persistencia real en OCI.
El spam sigue cubierto por pruebas sintéticas: la entrega real no contiene spam.

Los `0 inconsistencias` internos de DS y las `0 alertas` de nuestro auditor son
comprobaciones distintas; ninguna equivale por sí sola a aprobación humana.

### Dictamen y cierre de Semana 4

La dirección del auditor v2 es correcta. La revisión técnica queda completada
para esta entrega de 35 activos, con los ajustes de esta rama;
**no se ha emitido un OK humano ni una aprobación de PR**.
Para el cierre todavía faltan:

- que DA confirme las decisiones y el visto bueno sobre esta entrega identificada;
- revisar la versión editada/aprobada cuando SS entregue la curaduría;
- registrar con SS/CE el estrés y la persistencia real que corresponden al equipo.

## Evidencia histórica · 12–14 de octubre

Las secciones siguientes conservan las versiones y decisiones de cada corrida.
Los modelos Gemma/Llama, los PR pendientes y los resultados anteriores deben
interpretarse según la fecha y el SHA indicados, no como estado final vigente.

## Alcance y reparto

Fuente de coordinación: [artefacto de Gustavo, Semana 4](https://claude.ai/artifact/5pdbxqDswUooS2wPodpy8J),
consultado el 12 de octubre. La matriz rectora pide comparar originales con activos
de IA y con su edición humana, cubrir éxito, duda técnica y spam, y conservar un
reporte de consistencia en `docs/`.

- Gustavo: script de auditoría sin dependencias nuevas; similitud, palabras
  excluidas y posibles números, nombres, fechas o programas sin respaldo.
- Jhonattan: casos y pruebas offline, revisión de alertas y preparación del PR del
  reporte. Este cambio adelanta las pruebas previstas para el martes 13.
- Miércoles 14: corrida sobre los tres perfiles y revisión humana de resultados.
- Jueves 15: repetir sobre la curaduría si SS la entrega y participar en estrés.
- Viernes 16: demo. Las corridas reales se coordinan con Gustavo.

La similitud y las coincidencias de palabras son señales para revisión, no una
certificación de fidelidad. Un cambio de negación puede conservar casi todas las
palabras y alterar el hecho. Una paráfrasis fiel puede tener poca coincidencia.

## Base y aislamiento

Rama: `feature/jhonattan-auditoria-semana4`, creada desde DA `f5e059c`.
El 14 se incorporó `develop` `8cedef2` mediante el merge `9dd4f27`, sin conflictos.
Ya están fusionados los PR #21, #24, #25, #26, #28, #29 y #23. Los cambios propios
de esta rama frente a `develop` son casos sintéticos, pruebas y este reporte.
No se modifica el dataset compartido ni código de producción.

El enrutador ahora devuelve `tier_modelo` además de `rutas`. Se ajustaron las
comparaciones de rutas de los tres casos parametrizados de `int-020` y del caso
de estado vacío de Semana 3 para aceptar metadatos adicionales sin debilitar la
comprobación de rutas. El tier tiene su cobertura en
`tests/agents/test_enrutamiento_adaptativo.py`.

Con #21 integrado, `tests/test_tolerancia_persistencia_oci.py` exige el prefijo
`activos/`; se retiró la aceptación temporal de `assets/`. La suite OCI continúa
usando clientes simulados, no el servicio real.

## Proveedores de la base integrada

La configuración predeterminada de `src/agentes/configuracion_ia.py` usa NVIDIA
para análisis y generación, con enrutamiento adaptativo activo:

| Etapa/ruta | Modelo predeterminado |
| --- | --- |
| Análisis individual y por lotes | `google/gemma-4-31b-it` |
| FAQ y boletín | `meta/llama-3.1-8b-instruct` |
| Caso de éxito, insight y LinkedIn | `meta/llama-3.3-70b-instruct` |

La configuración puede cambiar mediante variables de entorno. El respaldo de
NVIDIA es Gemini; el timeout NVIDIA sigue siendo 3 s por intento, no un plazo
total del recorrido. El ensayo histórico de Nemotron no evalúa estos modelos.
Para la auditoría real deben registrarse los modelos y configuración efectivamente
usados, tanto en análisis como en cada activo, además de la versión del código.

## Casos disponibles

Archivo: `tests/fixtures/casos_consistencia_semana4.json`. Contiene tres perfiles
con entrada, análisis simulado, activos simulados y criterios de revisión.
Estos campos son datos de prueba, no un nuevo contrato de producción.

| Perfil | Recorrido esperado | Riesgos a revisar |
| --- | --- | --- |
| Éxito | Testimonio positivo → caso de éxito, boletín y LinkedIn | Mantener 3 ejercicios, Python, ONE y fecha; no inventar empleo o certificación; conservar la negación. |
| Duda técnica | Pregunta técnica → FAQ prudente | Conservar KeyError y clave `curso`; no garantizar plazos ni afirmar una causa sin evidencia. |
| Spam | Repetición evidente → exclusión antes de IA | Ningún análisis ni activo; ID y motivo conservados en el informe de Datos. |

Los nombres y hechos son sintéticos. Las pruebas crean diez autores distintos por
perfil para completar ciclos sin cambiar el mínimo de diez mensajes del plan.
Esa repetición verifica identidad y transporte; no aumenta la diversidad ni el
tamaño de una muestra de evaluación semántica real.

## Qué comprueban las pruebas

`tests/agents/test_consistencia_semana4.py` contiene siete pruebas:

1. Cada uno de los tres perfiles recorre Datos → procesamiento → grafo → contrato,
   con cadenas de IA simuladas y el acceso a la red bloqueado.
2. Un lote mixto conserva los activos de éxito y FAQ y excluye spam. El análisis
   simulado devuelve IDs en orden inverso: el resultado debe seguir asociado al
   mensaje correcto. Se comprueba el contenido completo por `(id_interaccion, tipo)`,
   no solo la presencia de fragmentos en el JSON global.
3. Dos casos de `int-020` verifican que feedback neutral o negativo conserva
   `insight_mejora` sin alterar `tipo_original`.
4. Una divergencia simulada de `int-020` a `comentario` reproduce la ausencia de
   `insight_mejora`, conservando el original `feedback`.

Los puntos 1 y 3 se parametrizan: 3 + 1 + 2 + 1 = 7. También se comprueban
ausencia de fallos y pendientes, entrada sin mutaciones, trazabilidad del ruido y
cero llamadas de generación para los mensajes excluidos.

Estas pruebas verifican conservación de respuestas controladas, no la exactitud
de un proveedor real. No invocan ni sustituyen el script de auditoría de Gustavo.

## Material para integrar con el auditor de Gustavo

Cada perfil incluye `variantes_para_auditor`: ocho salidas con una decisión humana
esperada y su justificación. Se cubren número cambiado, fecha cambiada, entidad
inventada, negación invertida, paráfrasis fiel, garantía institucional inventada,
respuesta técnica prudente y un activo que no debería existir para spam.

**Pendiente:** conectar estas variantes a la interfaz que publique Gustavo y
comprobar sus alertas. No se inventó una firma ni se añadieron pruebas omitidas
que aparenten cubrir un módulo todavía ausente.

El 13 de octubre Gustavo reportó que `scripts/auditoria_consistencia.py` funciona
localmente, sin IA ni red: las ocho variantes y cuatro activos simulados coinciden
con la decisión esperada (12/12), con 23 casos de prueba propios. Propuso publicarlo
en `feature/gustavo-auditoria-semana4` partiendo de `34989bf`. Al actualizar las
referencias el 14 no se encontró esa rama ni el archivo en `develop` o en nuestra
rama. Son resultados reportados por Gustavo, todavía sin revisión local de su
implementación. Se recomienda integrar su rama cuando la publique y conservar
el historial mediante merge.

Para comparar la salida deben considerarse texto original, metadatos autorizados
(por ejemplo autor) y fuentes técnicas aprobadas cuando correspondan. La ausencia
literal de un nombre en el texto no demuestra que sea inventado si está en los
metadatos. Las palabras excluidas deben acordarse con el equipo; no se usa una
lista improvisada para aprobar o rechazar contenido.

## Decisión propuesta sobre int-020

Mantener `feedback` en los datos: el mensaje propone agregar ejercicios prácticos.
El sentimiento negativo o neutral sigue sujeto a revisión humana. DS conserva
`tipo_original` y calcula `tipo_detectado` independientemente; no se fuerza al
modelo a copiar la etiqueta original. Si detecta `comentario`, registrar la
divergencia y su efecto en la ruta. Las pruebas no cambian el fixture de referencia.

## Evidencia y límites

### Validación integrada del 14 de octubre

Base `develop` `8cedef2`, merge `9dd4f27`, más los ajustes de pruebas descritos:

| Ejecución | Resultado |
| --- | --- |
| Consistencia de Semana 4, estados manuales y tolerancia OCI | 47 aprobadas |
| Suite completa | 432 aprobadas, 132 subpruebas aprobadas; 0 fallidas, 0 omitidas |
| `unittest discover` | 91 pruebas, OK |
| `pip check` | Sin dependencias incompatibles |

La primera ejecución completa se detuvo al recolectar contratos porque faltaba
`jsonschema`. Se instaló `jsonschema[format-nongpl]>=4.18,<5`, ya declarado en
`requirements.txt`, y se repitió la suite sin exclusiones adicionales. Las 46
pruebas NVIDIA antes omitidas ya están activas y pasan con proveedores simulados.
No se agregaron dependencias al repositorio.

### Evidencia histórica del 12 de octubre

Resultados sobre DA `f5e059c` más los casos iniciales:

| Ejecución | Resultado |
| --- | --- |
| Pruebas focalizadas de Semana 4 | 7 aprobadas |
| Suite completa | 280 aprobadas, 46 omitidas, 132 subpruebas aprobadas; sin fallos |
| `unittest discover` | 85 pruebas, OK |

Las 46 omisiones de esa ejecución correspondían a NVIDIA, entonces fuera de la
base. Unittest no ejecuta las siete funciones nuevas de pytest ni sustituye su
resultado. La suite completa se ejecutó fuera del entorno restringido por los problemas de
temporales de Windows ya conocidos. No hubo llamadas reales a IA, ni ejecución
de curaduría, ni escrituras en OCI. El acceso de red se bloquea en el archivo de
pruebas y `.env` no se carga.

```powershell
python -B -m pytest tests/agents/test_consistencia_semana4.py -q -p no:cacheprovider
```

Suite completa, desde la raíz y con el entorno del proyecto activo:

```powershell
$env:PYTHON_DOTENV_DISABLED = '1'
$pruebasTemp = Join-Path (Get-Location).Path ('salida/pytest-semana4-' + [guid]::NewGuid().ToString('N'))
python -B -m pytest --ignore=salida -q -p no:cacheprovider --basetemp "$pruebasTemp"
python -B -m unittest discover -s tests -p "test_*.py"
Remove-Item Env:PYTHON_DOTENV_DISABLED
```

La evaluación de clasificación de DS (`b141c93`) es un antecedente sobre Nemotron,
distinto de los modelos actuales; no evalúa la calidad de los activos ni reemplaza
este trabajo. La configuración para la demo debe acordarse antes de registrar
evidencia real de generación. Las pruebas de este reporte usan salidas simuladas;
no demuestran calidad semántica de un proveedor real.

## Auditoría sobre la entrega real de DS (14 de octubre)

DA: Gustavo. Ejecutada sin llamadas a IA ni red, con
`scripts/auditoria_consistencia.py` (26 pruebas propias en verde, incluidas las
ocho variantes de `casos_consistencia_semana4.json`: 12/12 coinciden con la
decisión esperada).

### Entrada auditada

| Campo | Valor |
| --- | --- |
| Archivo | `auditoria_semana4.json`, versión 1.2, enviado por Arnold (DS) el 14/10 16:49; no se versiona porque `salida/` está ignorada |
| SHA-256 del archivo | `8e2c24fc3edf755613bac85d4b1eb225ca8a9a71d39ca6eb167b66592fd4fc34` |
| Código que lo generó | `feature/DS-Semana4` `4331b6e` (working tree limpio según el archivo) |
| Dataset | `src/datos/mensajes_comunidad_simulados.json`, 23 interacciones, 0 excluidas por Datos |
| Activos | 26 en 16 interacciones |
| Modelos | NVIDIA NIM: `nemotron-3.5-lightning-30b-a3b` (rápido/estándar) y `nemotron-3-super-120b-a12b` (razonamiento); Gemini como respaldo |
| Fallback | 0 en análisis, 0 en generación |

Los modelos de la tabla "Proveedores de la base integrada" (`gemma-4-31b-it`,
`llama-3.1-8b`, `llama-3.3-70b`) son los de `develop`. DS los reemplazó en
`feature/DS-Semana4` porque NVIDIA marcó los Llama como deprecados; en el momento
de aquella corrida esa rama todavía no tenía PR. Ahora se revisa en el PR #32.

Comando:

```powershell
python -B scripts/auditoria_consistencia.py --entrega auditoria_semana4.json `
  --proveedor por_activo --version-codigo 4331b6e `
  --salida-json salida/auditoria_semana4_reporte.json --salida-md salida/auditoria_semana4_reporte.md
```

### Resultado por modelo

| Modelo | Activos | Con alertas |
| --- | --- | --- |
| `nemotron-3-super-120b-a12b` | 12 | 0 |
| `nemotron-3.5-lightning-30b-a3b` | 14 | 1 |

No se detectaron números, fechas, entidades, negaciones perdidas ni compromisos
sin respaldo en los 26 activos.

### Hallazgos para revisión humana

| ID | Ruta | Hallazgo | Decisión sugerida |
| --- | --- | --- | --- |
| int-015 | preguntas_frecuentes | `instruccion_filtrada`: la respuesta es la instrucción del prompt ("Una redacción breve que indique… No inventes descripciones…"), no un texto para el lector | Rechazar y regenerar; DS revisa el prompt de FAQ |
| int-011, int-014, int-018 | — | Datos los marca `testimonio` y elegibles (score 61–70); DS detecta `comentario` y no se generan activos | Revisar con DS; mismo patrón de divergencia documentado para `int-020` |
| int-023 | preguntas_frecuentes | Casi duplicado de `int-002` (mismo texto sin tildes); se generaron dos FAQ equivalentes | Aceptable para la demo; deduplicación aproximada queda para la S5 |

El hallazgo de `int-015` se detectó primero en la lectura manual: el auditor no
tenía una regla para instrucciones filtradas. Se agregó `instruccion_filtrada`
con su prueba antes de cerrar esta corrida. Que el resto no tenga alertas no
certifica fidelidad: las respuestas técnicas de FAQ (`int-002`, `int-017`,
`int-021`) agregan explicación general que no está en el mensaje y requieren
juicio humano o fuentes técnicas aprobadas.

### Tres perfiles obligatorios

| Perfil | Evidencia real (entrega de DS) | Evidencia controlada (fixture) |
| --- | --- | --- |
| Éxito | `int-001`: testimonio → caso de éxito, boletín y LinkedIn; "menos de 3 meses" y "portfolio" conservados, sin alertas | `s4-001-exito` y sus variantes |
| Duda técnica | `int-017`: pregunta técnica → FAQ prudente sobre indentación, sin plazos ni garantías | `s4-002-duda_tecnica` |
| Spam | No hay spam en el dataset compartido (0 excluidos) | `s4-003-spam`: excluido por Datos (`texto_repetitivo`, `bajo_umbral`); el activo forzado se marca `activo_de_mensaje_excluido` |

### Segunda corrida de DS (14 de octubre, noche)

DS corrigió el prompt de FAQ (int-015) y la definición de testimonio (int-011,
int-014, int-018) en `feature/DS-Semana4` y regeneró el paquete.

| Campo | Valor |
| --- | --- |
| Archivo | `auditoria_semana4_v2.json`, versión 1.2 |
| SHA-256 del archivo | `25bda8f78e8c968f…` |
| Código que lo generó | `feature/DS-Semana4` `8f32be8` (incluye `develop` `46f6d41`) |
| Activos | 35 en 19 interacciones; 0 fallback |

El auditor sumó dos reglas a partir de la lectura manual de esta corrida:
`comentario_interno` (notas del modelo para el revisor, como "no se especifica"
o "mensaje original") y `hashtag_sin_almohadilla`.

| Modelo | Activos | Con alertas |
| --- | --- | --- |
| `nemotron-3-super-120b-a12b` | 18 | 3 |
| `nemotron-3.5-lightning-30b-a3b` | 17 | 5 |

| ID | Ruta | Alerta | Decisión sugerida |
| --- | --- | --- | --- |
| int-011 | caso_exito | `comentario_interno`: "No se especifica el tipo de proyectos…" | Editar: quitar la nota |
| int-014 | caso_exito | `comentario_interno`: "No se menciona ningún logro adicional… en el mensaje original" | Editar; revisar si califica como caso de éxito |
| int-004, int-007, int-010, int-013 | preguntas_frecuentes | `comentario_interno`: "ya que la pregunta no proporciona/especifica…" | Menor: reformular hacia el lector |
| int-003 | linkedin | `hashtag_sin_almohadilla`: Aprendizaje, ModeloDeClasificación | Corregir formato |
| int-017 | preguntas_frecuentes | `entidad_sin_respaldo`: DataFrame | Falso positivo: término técnico de pandas |

Con las reglas nuevas, la primera corrida (`4331b6e`) también marca int-004
("No se especifica… en el mensaje recibido"). int-015 ya no aparece en la
segunda corrida.

Pendiente: repetir sobre `develop` cuando se fusione el PR de DS, con el SHA final.

### Pendiente

- Decisión humana y justificación por fila en el reporte generado (columna vacía
  a propósito).
- Versión editada y aprobada por curaduría, cuando SS la entregue.
- Repetir con el código de DS una vez fusionado, para que el SHA auditado esté en
  `develop`.

## Condiciones para cerrar el reporte

- Integrar y probar las alertas del script de Gustavo, distinguiendo errores
  detectados, falsos positivos y casos que requieren juicio humano.
- Registrar por ID el original, la salida real de IA, el activo/ruta, proveedor,
  versión del código, alerta, decisión humana y justificación.
- Añadir la versión editada y aprobada cuando exista la curaduría; su ausencia
  debe constar como pendiente, no como aprobación simulada.
- Documentar los tres perfiles completos. Para spam, verificar la exclusión y
  la ausencia de activos es el resultado válido.
- Ejecutar con el equipo la prueba de estrés y verificar el guardado aprobado
  con CE/SS. Una prueba offline por lotes no certifica concurrencia, IAM o la VM.
