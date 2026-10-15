# Semana 4: preparación de la auditoría de consistencia

Preparado el 12 y actualizado el 14 de octubre de 2026. DA: Gustavo y Jhonattan.

**Estado: preparación y validación offline. No es el cierre de la auditoría con
IA real, curaduría, estrés ni OCI.**

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
`feature/DS-Semana4` porque NVIDIA marcó los Llama como deprecados; esa rama aún
no tiene PR.

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
