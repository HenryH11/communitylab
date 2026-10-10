# Semana 3: validación de Jhonattan

Actualizado el 10 de octubre de 2026 en `feature/jhonattan-validacion-semana3`.
Data Analyst: Gustavo y Jhonattan. Esta sección describe el estado actual; las
tablas fechadas del 6, 7 y 8 de octubre se conservan como evidencia histórica.

## Estado verificado el 10 de octubre

Se actualizó la copia local por avance directo hasta `b3d7676`. Gustavo incorporó
`develop` `415a16d` mediante `d040cb8`: ya están las correcciones de Cloud (PR #18),
Streamlit (PR #19) y la línea estable de Data Science (PR #22). La rama contiene
el [filtro de ruido de DA](filtro_ruido_da_semana3.md). No contiene DS NVIDIA.

| Comprobación local sobre `b3d7676` | Resultado |
| --- | --- |
| Suite completa de pytest, con SDK OCI instalado | 273 aprobadas, 46 omitidas, 0 fallidas, 0 fallos esperados; 132 subpruebas aprobadas |
| `unittest discover` | 85 pruebas, OK |

Las 46 omisiones son 38 criterios del respaldo y 8 pruebas del adaptador: falta
integrar la rama `feature/DS-Semana3-Nvidia`. No equivalen a pruebas aprobadas.
Gustavo retiró las seis marcas `xfail` en `9519d38` y `b3d7676` después de incorporar
las correcciones; esas seis pruebas ya pasan normalmente. Las 13 pruebas de
estructura de activos añadidas en `c67502c` también forman parte de esta suite.

La ejecución inicial dentro del entorno restringido de Windows falló en 14 pruebas
por permisos de archivos temporales. Se repitió fuera de esa restricción, sin
cambiar código ni omitir pruebas; la tabla muestra el resultado final.
No se hicieron llamadas reales a NIM, Gemini ni OCI. Streamlit se comprueba de
forma estática y OCI con clientes simulados. `unittest` no sustituye a pytest.

Comandos desde la raíz del repositorio, con el entorno Python del proyecto activo:

```powershell
$env:PYTHON_DOTENV_DISABLED = '1'
$pruebasTemp = Join-Path (Get-Location).Path ('salida/pytest-' + [guid]::NewGuid().ToString('N'))
python -B -m pytest --ignore=salida -q -p no:cacheprovider --basetemp "$pruebasTemp"
python -B -m unittest discover -s tests -p "test_*.py"
Remove-Item Env:PYTHON_DOTENV_DISABLED
```

La variable evita cargar `.env` durante las pruebas y se retira al terminar para
permitir las ejecuciones reales posteriores. El ensayo real es una acción separada.

La [revisión NIM del 8 de octubre](revision_integracion_nim_semana3.md) conserva la
reproducción del retorno faltante y la comprobación de su corrección en una copia
aislada. No se debe presentar el resultado de esa copia como resultado de esta rama.

### Complemento de Gustavo del 10 de octubre, 12:05 (Colombia)

En la captura `Captura de pantalla 2026-10-10 120659.png`, Gustavo confirma que
revisó la rama `15545da` y reporta 273 y 302 pruebas aprobadas al simular la
integración con Cloud #21 y #23, sin fallos ni conflictos. Son resultados reportados
por Gustavo; no se dispone aquí del registro detallado de esas combinaciones ni
se presentan como nuevas ejecuciones locales. Los dos PR de Cloud siguen abiertos.
La revisión mutua comprende los archivos de Gustavo revisados por Jhonattan sobre
`b3d7676` y la revisión de `15545da` confirmada por Gustavo. Las aprobaciones de
DS, CE y SS para fusionar el PR de DA siguen siendo independientes.

## Diferencias respecto al plan del 5 de octubre

Fuente: `2026-10-05_semana_3_reunion_1.pdf`, páginas 10–12. Se declaran las
diferencias de implementación y de alcance; no se presentan como cumplimiento
literal de todas las metas del plan ni como aprobación del PM.

| Punto del plan | Implementación y límite actual |
| --- | --- |
| Ráfagas de 23 peticiones concurrentes (p. 11) | El ensayo admite concurrencia de 1 a 4 como control local; las corridas documentadas usaron 1. No es un límite oficial del endpoint gratuito verificado ni una prueba de carga con 23 peticiones simultáneas. |
| Comparación Nemotron / DeepSeek (p. 11) | DA retiró DeepSeek del alcance el 8 de octubre. Se conserva Nemotron `nvidia/nemotron-3.5-lightning-30b-a3b`; los resultados anteriores de DeepSeek son históricos. |
| Respaldo al superar 1,8 s en procesamiento por lotes (pp. 11–12) | DS implementó un timeout de cliente de 3 s por intento, configurable mediante `COMMUNITYLAB_NVIDIA_TIMEOUT_SEGUNDOS`, con hasta tres intentos primarios antes de Gemini. Está en la rama NVIDIA, no en esta rama. El ensayo aislado mide solicitudes individuales: `--umbral-segundos` solo clasifica resultados y `--timeout` controla las operaciones de red; no activa Gemini ni mide el tiempo total del grafo. |
| `base_url = "https://nvidia.com"` en el ejemplo (p. 12) | La base usada por DS es `https://integrate.api.nvidia.com/v1`; el ensayo llama a `https://integrate.api.nvidia.com/v1/chat/completions`. |
| Medir latencia en `tests/test_rendimiento_datos.py` (p. 10) | Las mediciones de inferencia están separadas en `scripts/medir_latencia_nvidia_nim.py`; las pruebas de rendimiento de Datos conservan su alcance local. |
| Crear `scripts/test_nvidia_nim_latency.py` (p. 11) | El ejecutable se llama `scripts/medir_latencia_nvidia_nim.py` para evitar la colisión de nombres con `tests/test_nvidia_nim_latency.py` durante la recolección de pytest. La ejecución real está protegida por `--en-vivo` y el punto de entrada `__main__`; renombrarlo no es la protección que autoriza las llamadas. |

## Qué se añadió

- `tests/agents/test_tolerancia_fallas.py`: 19 pruebas del recorrido Datos → grafo real → contrato de salida de Data Science. Se sustituyen las llamadas a modelos por respuestas controladas.
- `scripts/medir_latencia_nvidia_nim.py`: ensayo independiente de NVIDIA con planificación sin red y ejecución real opcional.
- `tests/test_nvidia_nim_latency.py`: pruebas del ensayo con transporte simulado.
- Gustavo añadió pruebas de estados manuales, persistencia OCI, estructura de la
  aplicación y 38 criterios de aceptación del respaldo NIM → Gemini. Su evaluación
  y sus límites se detallan en la sección de revisión de sus archivos.

Las pruebas comprueban rechazo de datos inválidos antes de llamar a IA, conservación
de Unicode e IDs, exclusión de ruido, conservación de pendientes y continuidad de
los siguientes mensajes cuando falla un lote o un generador. Cubren timeouts,
errores de cuota simulados y respuestas incompletas. Las entradas de estas pruebas
son sintéticas y propias; no reemplazan los datos de referencia del equipo.

Las 19 pruebas iniciales cubren entradas que pasan por `preparar_paquete_ia`.
Ahora hay 20 en ese archivo: se añadió la entrega compuesta solo por ruido. Otras
17 pruebas en `tests/test_filtro_ruido.py` cubren las reglas y los casos que deben
conservarse. Los nuevos resultados se registran al final de este documento.
Las pruebas adicionales de Gustavo documentan también estados manuales y pendientes
de otros componentes. La revisión de Streamlit es estática; OCI usa un cliente
simulado cuando está instalado su SDK. No son pruebas con servicios reales.

## Modelos Free Endpoint

Por acuerdo de Gustavo y Jhonattan del 8 de octubre, el ensayo admite únicamente
Nemotron. Su ficha mostraba **Free Endpoint: Available** al verificarla ese día:

| ID admitido | Ficha oficial |
| --- | --- |
| `nvidia/nemotron-3.5-lightning-30b-a3b` | [Nemotron 3.5 Lightning](https://build.nvidia.com/nvidia/nemotron-3.5-lightning-30b-a3b/build) |

La lista es una verificación manual fechada, no una consulta automática de disponibilidad.
DeepSeek se retiró del catálogo del script y de los comandos sugeridos por decisión
de DA. No se etiqueta como `deprecated`: los timeouts anteriores no demuestran
retiro del servicio. Los resultados del 6 de octubre se conservan como evidencia
histórica; no hay nuevas corridas de DeepSeek pendientes dentro del alcance acordado.
Revisar las fichas antes de una ejecución real. Para incorporar otro modelo, primero
confirmar su etiqueta y actualizar `MODELOS_FREE_ENDPOINT` y la fecha en el script.
La etiqueta sirve para seleccionar candidatos al prototipo; hay medidas reales
de Nemotron, pero no una comparación completa que permita recomendar un ganador.

## Comandos para el equipo

Ejecutar desde la raíz del repositorio, con el entorno Python del proyecto activo
y sus dependencias instaladas. En este equipo, puede sustituirse `python` por
`.\.venv\Scripts\python.exe`.

Pruebas nuevas, sin llamadas a proveedores:

```powershell
python -B -m pytest tests/agents/test_tolerancia_fallas.py tests/test_nvidia_nim_latency.py -q -p no:cacheprovider
```

Si Windows devuelve `PermissionError` al acceder a `Temp/pytest-of-Vianey`, usar
una carpeta temporal nueva para cada ejecución desde la raíz del proyecto:

```powershell
$pruebasTemp = Join-Path (Get-Location).Path ('salida/pytest-' + [guid]::NewGuid().ToString('N'))
python -B -m pytest tests/agents/test_tolerancia_fallas.py tests/test_nvidia_nim_latency.py -q -p no:cacheprovider --basetemp "$pruebasTemp"
```

La ruta generada es exclusiva para pytest; no usar como `--basetemp` una carpeta
con archivos propios, porque pytest puede borrar su contenido al comenzar.

Planificar el análisis de los 23 mensajes con Nemotron, sin usar una clave:

```powershell
python -B -m scripts.medir_latencia_nvidia_nim --modelo nvidia/nemotron-3.5-lightning-30b-a3b --umbral-segundos 3 --salida salida/validacion_semana3/plan_analisis.json
```

Este comando prepara 23 solicitudes individuales, pero no las envía. El benchmark
incluye todos los estados válidos aunque algunos estén pendientes de completar un
ciclo de producción. No ejecuta el grafo ni reproduce su análisis por lotes.

También se pueden planificar generación de FAQ y LinkedIn agregando `--tarea faq`
o `--tarea linkedin`. La selección usa el tipo original y las elegibilidades del
paquete: FAQ técnicas seleccionadas o administrativas elegibles; LinkedIn para
testimonios seleccionados. No reproduce el enrutamiento posterior a la clasificación.

Para una prueba real, configurar `NVIDIA_API_KEY` en el entorno local o en el `.env`
ignorado por Git y añadir `--en-vivo`. No guardar la clave en el script, informes
ni mensajes del equipo. [NVIDIA explica cómo obtenerla en su guía oficial](https://docs.api.nvidia.com/nim/docs/api-quickstart).
Comando para una nueva corrida de Nemotron, con el razonamiento desactivado y el
umbral confirmado por DS. La corrida histórica del 6 de octubre usó 1,8 s:

```powershell
python -B -m scripts.medir_latencia_nvidia_nim --modelo nvidia/nemotron-3.5-lightning-30b-a3b --sin-razonamiento --max-tokens 1024 --timeout 30 --umbral-segundos 3 --en-vivo --salida salida/validacion_semana3/nemotron_analisis.json
```

`--sin-razonamiento` envía `chat_template_kwargs.enable_thinking=false` y solo
admite Nemotron. La configuración se registra en el informe. DeepSeek ya no es
una opción admitida por la CLI; se rechaza antes de enviar solicitudes.

La ejecución real envía los textos a NVIDIA. El ensayo usa el endpoint oficial
`https://integrate.api.nvidia.com/v1/chat/completions` y no sigue redirecciones.
La clave no se incluye en los informes. Los informes completos contienen respuestas
del modelo: guardarlos en `salida/`, que ya está ignorada por Git.

## Qué mide y cómo interpretarlo

Por defecto se ejecuta una solicitud a la vez, con un segundo mínimo entre inicios,
una repetición y un máximo de 4096 tokens de salida. `--concurrencia` permite de 1 a 4;
ese máximo es un control local del ensayo, no un límite oficial de NVIDIA verificado.
Las mediciones reales documentadas usaron concurrencia 1;
no se lanzan 23 peticiones simultáneas. El intervalo controla el ritmo local, no
garantiza la cuota del proveedor. No hay reintentos automáticos.

El informe separa espera de programación, duración de cada solicitud, respuestas
válidas y errores. Incluye promedio, mediana y percentil 95; los errores rápidos no
reducen artificialmente el promedio de las respuestas válidas. Con pocas muestras,
el percentil 95 no permite afirmar un rendimiento estable. Los tokens se registran
solo cuando el proveedor los devuelve.

Se reutilizan plantillas y esquemas actuales de Data Science, agregando la instrucción
de devolver JSON. El proveedor debe aceptar `response_format=json_object`; esto aún
requiere verificación en vivo para cada modelo. Una respuesta rechazada o truncada
cuenta como fallo. `--max-tokens` permite ajustar el presupuesto hasta 32768. No se
configura el razonamiento interno salvo al indicar `--sin-razonamiento` para Nemotron;
el valor por defecto del proveedor y el presupuesto pueden afectar la duración y
la completitud. Registrar cualquier cambio al comparar.

En la primera prueba real, Nemotron devolvió el esquema (`properties`, `required`,
`title`, `type`) en lugar de los cuatro campos del análisis. La instrucción añadida
por el ensayo ahora exige una instancia de datos y prohíbe copiar el esquema. Las
plantillas de Data Science no se modificaron. Se conservan los informes previos:
sus tiempos y errores no se mezclan con las corridas realizadas tras este ajuste.

Las tareas de generación llevan tema, subtema y tipo detectado vacíos porque este
ensayo no ejecuta un análisis previo. Miden el formato y rendimiento de esa solicitud
aislada, no la calidad del flujo completo. Validar el esquema tampoco demuestra
corrección semántica: los textos necesitan revisión humana.

El acuerdo inicial comunicado el 6 de octubre indicaba 1,8 segundos. El 8 de octubre,
DS confirmó e implementó 3 segundos en `COMMUNITYLAB_NVIDIA_TIMEOUT_SEGUNDOS`, usando
`ChatOpenAI` para NIM. Es el timeout del cliente por intento, no un plazo global del
mensaje: el fallback agota hasta tres intentos primarios con esperas antes de usar
Gemini. Las métricas del flujo completo deben incluir esas esperas y el respaldo.
La implementación está en la rama de DS NVIDIA, todavía fuera de esta rama de DA.

En este ensayo, `--umbral-segundos 3` solo cuenta respuestas válidas que superan
3 segundos **por solicitud**. No cancela llamadas ni activa Gemini. `--timeout`
es otro parámetro: mantiene 60 segundos por defecto y se aplica a operaciones de
socket, no garantiza un plazo total de respuesta. Las corridas de latencia conservan
ese timeout para observar también respuestas que superan el objetivo del PM. La
activación del respaldo debe verificarse por separado con el código de DS.

El script devuelve 0 para un plan o una corrida sin fallos, 1 cuando alguna solicitud
falla y 2 para errores de configuración o entrada. Conserva resultados de solicitudes
fallidas y continúa con las demás.

## Validación histórica hasta el 6 de octubre

El [PR #17 de Data Science](https://github.com/HenryH11/communitylab/pull/17), ya
fusionado en `develop` e incorporado a esta rama, resolvió los dos desacuerdos:
los tipos originales de `int-004` e `int-007` ahora son `pregunta_programa`, y la
aserción espera 19 seleccionados. Ya no son pendientes de conciliación.

| Entorno y versión | Aprobadas | Omitidas | Fallos esperados (`xfail`) | Fallos inesperados |
| --- | ---: | ---: | ---: | ---: |
| Verificado por Jhonattan: `develop` `1a9bcaa`, sin OCI | 127 | 0 | 0 | 0 |
| Verificado por Jhonattan: `14be025` más ajuste local de importación, sin OCI | 176 | 63 | 5 | 0 |
| Verificado por Jhonattan: incluye ajustes NIM y dos casos de prueba adicionales, sin OCI | 178 | 63 | 5 | 0 |
| Reportado por Gustavo: rama compartida `14be025`, con OCI | 208 | 38 | 6 | 0 |

Las ejecuciones locales también aprobaron 124 subpruebas. Se excluyeron
`tests/test_storage.py` y `tests/test_persistencia_oci.py` porque fallan al importar
el SDK de OCI ausente. Las nuevas pruebas de tolerancia OCI se omiten solas. Las
63 omisiones locales corresponden a 38 casos de respaldo aún no implementado y
25 casos de OCI; el número de casos OCI aumenta al disponer de sus rutas reales.
El resultado de 208 aprobadas se atribuye al entorno de Gustavo y no se presenta
como una ejecución realizada aquí.

El ajuste de importación se comprobó además en cuatro escenarios simulados: SDK
ausente, SDK disponible, dependencia interna ausente y conector con error de
importación. Solo la ausencia del SDK activa la omisión.

Los planes sin red se verificaron con 23 mensajes de análisis, nueve de FAQ y ocho
de LinkedIn. Las 39 pruebas iniciales siguen incluidas en la suite; se añadieron
dos casos que verifican el parámetro de razonamiento y que no se aplique a DeepSeek.
Ya se hicieron llamadas reales a NVIDIA, descritas en la sección de resultados.

El script se renombró a `medir_latencia_nvidia_nim.py` para evitar la colisión con
el módulo de pruebas al descubrir archivos desde la raíz. Comando para verificar
esa ejecución, manteniendo las exclusiones de OCI de este entorno:

```powershell
$pruebasTemp = Join-Path (Get-Location).Path ('salida/pytest-' + [guid]::NewGuid().ToString('N'))
python -B -m pytest --ignore=salida --ignore=tests/test_storage.py --ignore=tests/test_persistencia_oci.py -q -p no:cacheprovider --basetemp "$pruebasTemp"
```

`--ignore=salida` evita que pytest explore informes, copias de auditoría y temporales
de otras sesiones, que pueden tener permisos distintos en Windows. Las pruebas
versionadas siguen descubriéndose desde la raíz, incluidos `scripts/` y `tests/`.

Con las dependencias completas, se pueden omitir los dos `--ignore` de OCI,
manteniendo `--ignore=salida`. Un resultado
`unittest discover: OK` no sustituye este comando: unittest no ejecuta todas las
funciones ni aplica las marcas de pytest.

## Revisión de los archivos de Gustavo por Jhonattan

La revisión inicial cubrió cuatro archivos en `14be025` y sus ajustes posteriores.
El 10 de octubre se revisaron sus versiones en `b3d7676`, los cambios que retiran
los `xfail` y el nuevo archivo de estructura JSON. La suite completa anterior se
ejecutó sobre esa misma versión. Las revisiones atribuidas a Gustavo se identifican
como reportadas cuando no hay evidencia local de su ejecución; esto no certifica
una aprobación conjunta del estado final ni reemplaza las revisiones de DS, CE y SS.

| Archivo | Qué aporta | Límite o acción pendiente |
| --- | --- | --- |
| `tests/agents/test_tolerancia_estados_manuales.py` | Once casos aprobados; los cuatro defectos de DS se corrigieron en el PR #22. | Usan proveedores simulados. El caso de lote comprueba que se devuelven ambos estados con fallo cuando también falla el proveedor; por sí solo no demuestra éxito del mensaje sano. |
| `tests/test_tolerancia_persistencia_oci.py` | Serialización, nombres, errores y rutas del grafo, incluido `insight_mejora` del PR #18. | Acepta prefijos `assets/` o `activos/` y exige el resto de la clave estable. No valida servicio real, IAM ni la migración de objetos existentes. |
| `tests/test_tolerancia_app.py` | Verifica `try`, presentación de errores y ausencia de llamadas explícitas a `st.rerun`. La lectura JSON se corrigió en el PR #19. | La inspección AST no demuestra el comportamiento visual completo ni descarta otras causas de ejecuciones repetidas. |
| `tests/agents/test_respaldo_nim_gemini.py` | Define 38 criterios sobre respaldo, conservación de entrada y trazas sin secretos. | Se omiten hasta incorporar la función publicada en la rama NVIDIA. Falta medir timeout, reintentos y respaldo real. |
| `tests/agents/test_estructura_activos_referencia.py` | Trece casos aprobados de contenido JSON, Unicode y fallo trazable en LinkedIn y FAQ. | Ejecuta el generador y el contrato de salida con cadenas simuladas; no invoca el grafo completo ni el adaptador NIM. La búsqueda de fragmentos en el JSON final no comprueba por sí sola la asociación exacta de cada activo con su ID. |

`pytestmark = pytest.mark.skipif(...)` evita interrumpir la importación de esos
módulos con funciones de pytest. No debe asumirse que unittest interpreta esa marca
como una omisión propia. Las seis marcas `xfail` históricas ya se retiraron.

DS eligió `ChatOpenAI`; el ensayo aislado conserva `urllib`. El contrato de respaldo
ya fue actualizado por Gustavo en `5e73233`: reconoce errores HTTP y distingue
configuración ausente de entrada inválida. Las ocho pruebas adicionales del
adaptador ejercitan `ErrorSalidaProveedor` mediante la cadena real cuando se
incorpore el módulo NVIDIA. No se deben confundir los dos clientes ni sus excepciones.

## Resultados reales del 6 de octubre de 2026

La clave local permitió una respuesta de inferencia HTTP 200 de Nemotron. El
catálogo autenticado también respondió HTTP 200 e incluyó los dos modelos elegidos.
Las conexiones TLS a NVIDIA funcionaron. Esto no garantiza disponibilidad ni
rendimiento de cada modelo en cada solicitud.

Se conservó la evidencia en `salida/validacion_semana3/corrida-20261006T203308359Z/`, excluida de Git.
El archivo `nemotron_23_analisis.json` contiene los resultados por ID;
`metadatos_corrida.json` registra la versión de Python y huellas del código local.
El dataset conserva SHA-256
`63f19b4756d26c4f4fd64f6b289ada8fe1bee83c5f1ef1194f6009c3a7bfe045`.

### Nemotron: corrida completa de análisis

Inicio: 6 de octubre, 15:44:09, hora de Colombia (20:44:09 UTC). Una repetición de
23 mensajes, concurrencia 1, intervalo mínimo 1 segundo, temperatura 0, presupuesto
1024 tokens, timeout de operaciones de red 30 segundos, razonamiento desactivado.
La duración total fue 195,25 segundos. No hubo reintentos ni respaldo hacia Gemini.

| Medida | Resultado |
| --- | ---: |
| Solicitudes | 23 |
| Respuestas que cumplieron el esquema | 20 (86,96 %) |
| Timeouts | 3 |
| Respuestas válidas en hasta 1,8 s | 10 de 23 solicitudes |
| Respuestas válidas por encima de 1,8 s | 10 |
| Promedio de las 20 respuestas válidas | 5,23 s |
| Mediana de las 20 respuestas válidas | 1,88 s |
| Percentil 95 de las 20 respuestas válidas | 21,64 s |
| Mínimo / máximo de respuestas válidas | 1,26 s / 24,44 s |

Los timeouts corresponden a `int-011`, `int-019` e `int-021`, a los 30,18, 30,20 y
30,26 segundos, respectivamente. No se cuentan como latencia de respuestas válidas.
En esta corrida, 13 de 23 solicitudes no produjeron una respuesta válida dentro de
1,8 segundos. No se midió cuánto tardaría Gemini al activarse el respaldo.

La lectura de las 20 salidas muestra tipos detectados coincidentes con sus tipos
originales, incluyendo `pregunta_programa` para `int-004` e `int-007`. Esto no es una
medida de exactitud independiente: el prompt contiene el tipo original y el
conjunto de referencia todavía requiere revisión humana. DS debe revisar también
el grado del sentimiento y la elección del tema. No se generaron activos en esta corrida.

### DeepSeek y comprobaciones previas

DeepSeek agotó el tiempo de espera en cuatro comprobaciones: la entrada del ensayo
con 60 segundos, una petición mínima con 20 segundos, y otras dos comprobaciones
del ensayo con 30 segundos (una de ellas con la instrucción corregida). No se lanzó
su lote completo de 23 mensajes. No hay respuestas válidas para calcular su latencia
ni evaluar su contenido; la causa de esos timeouts no está establecida.

Antes de corregir la instrucción, Nemotron también agotó un timeout de 60 segundos
y devolvió una respuesta inválida con un presupuesto de 512 tokens. Desactivar el
razonamiento por sí solo no bastó: otro diagnóstico confirmó que devolvía el esquema
en vez del análisis. Tras aclarar la instrucción y desactivar el razonamiento,
la comprobación de un mensaje fue válida en 4,05 segundos y se inició el lote.
Estas comprobaciones están separadas del cálculo de las 23 solicitudes.

**Conclusión histórica de esta ejecución:** la configuración de la clave funciona, pero la
corrida de Nemotron no cumple de forma consistente el objetivo de 1,8 segundos.
No se puede declarar un ganador frente a DeepSeek ni recomendar el cambio de
proveedor de producción con estos datos. Quedaban pendientes la repetición y el
respaldo real de DS. El 8 de octubre DA retiró DeepSeek del alcance de nuevas pruebas.

## Comparación con la corrida reportada por Gustavo

Fuente: mensaje de Gustavo en Discord, captura `Captura de pantalla 2026-10-07
210230.png`. Gustavo declara una corrida del 6 de octubre a las 17:23, hora de
Colombia, con la misma configuración: sin razonamiento, 1024 tokens y timeout de
30 segundos. Las cifras de su corrida son reportadas; no se dispone aquí de su
JSON por solicitud para recalcularlas. No se mezclan ambas corridas.

| Medida | Jhonattan, evidencia JSON local | Gustavo, reporte de Discord |
| --- | ---: | ---: |
| Solicitudes | 23 | 23 |
| Respuestas válidas | 20 | 22 |
| Fallos | 3 timeouts | 1, `int-015`, reportado como inválido a los 30 s |
| Promedio de respuestas válidas | 5,23 s | 2,15 s |
| Mediana | 1,88 s | 1,84 s |
| p95 | 21,64 s | 4,45 s |
| Válidas en hasta 1,8 s | 10/23 | 8/23 |
| Válidas en hasta 2,5 s | 13/23 | 18/23 |
| Válidas en hasta 3 s | 13/23 | 19/23 |

Las filas de 2,5 y 3 segundos de Jhonattan se recalcularon el 7 de octubre sobre
`nemotron_23_analisis.json`, contando solo resultados válidos. No hubo nuevas llamadas.
Con 3 segundos, 10 solicitudes de nuestra corrida y 4 de la de Gustavo no habrían
producido una respuesta válida dentro del objetivo. Esto es una estimación sobre
solicitudes aisladas, no una ejecución real del respaldo ni una garantía de latencia
para el grafo por lotes. El fallo de `int-015` no demuestra por sí solo un problema
del mensaje; se necesita su error y respuesta para diagnosticarlo.

La evidencia justifica revisar el límite de 1,8 segundos con DS y PM, pero no
declaraba 3 segundos como valor aprobado en esa revisión. DS lo confirmó después,
el 8 de octubre. Ese día Gustavo y Jhonattan retiraron DeepSeek del ensayo.

## Actualización técnica del 7 de octubre

- Nuestra base remota es `a15631c`: incorpora el tipado y las adaptaciones de
  imports, mocks con `config` y reintentos de Gustavo.
- DS está en `fcb18df`, sobre `develop` `1a9bcaa`. Los dos árboles de ingesta son
  idénticos. DS añade reintentos, reprocesamiento y contrato 1.3; su proveedor
  continúa siendo Gemini. La función de respaldo NIM → Gemini sigue pendiente.
- El PR #18 de Cloud, `7d756df`, incluye `insight_mejora`, mueve la prueba manual
  fuera de `tests/` y omite la suite OCI cuando falta específicamente su SDK.
  Está pendiente de integración. El `xfail` de rutas se conserva en nuestra rama
  mientras use el conector anterior; debe retirarse al incorporar la corrección.
- La aplicación en la rama de DS sigue importando `procesar_paquete_entrega` desde
  `grafo.py`, aunque se trasladó a `procesamiento.py`. También mantiene `json.load`
  fuera del `try`. La suite de funciones no equivale a validar el arranque de la app.

### Validación local del 7 de octubre

Se instaló el SDK `oci` 2.187.2 en el entorno local para ejecutar también las
pruebas de persistencia con clientes simulados. No se llamaron proveedores de IA
ni se consultó o escribió en el bucket. No se copiaron credenciales a las revisiones.

| Comprobación | Aprobadas | Omitidas | Fallos esperados | Fallos inesperados |
| --- | ---: | ---: | ---: | ---: |
| DA sobre `a15631c` más este cambio de ruido, con OCI | 228 | 38 | 6 | 0 |
| DA más DS `fcb18df`, copia aislada | 252 | 38 | 6 | 0 |
| DA + DS + código de Cloud del PR #18 `7d756df`, copia aislada | 255 | 38 | 5 | 0 |

Las dos primeras ejecuciones aprobaron también 127 subpruebas; la tercera, 132.
`unittest discover` en la rama de DA ejecutó 84 pruebas y terminó en OK. La revisión
inicial focalizada de filtro, entrega, tolerancia y ensayo NIM aprobó 77 pruebas
y 76 subpruebas. Estos números pertenecen a selecciones diferentes, no se suman.

Las 38 omisiones son los criterios del respaldo NIM → Gemini. Los seis fallos
esperados en DA corresponden a cuatro estados manuales de DS, la ruta OCI
`insight_mejora` y la lectura JSON de la app. En la copia con Cloud se retiró
únicamente el `xfail` de rutas y la prueba pasó; la marca se conserva en la rama
compartida porque su conector todavía no contiene el PR #18.

Para comprobar DS se construyó el árbol de combinación de `a15631c` y `fcb18df`
con `git merge-tree` (sin conflictos) y se aplicaron los archivos locales del
filtro y sus pruebas en `salida/.revision-da-ds-20261007/`. Para Cloud se preparó
otra copia con su conector, pruebas y traslado de la comprobación manual, más la
retirada de la marca mencionada. Es una validación funcional de esos archivos,
no una fusión ni una aprobación del PR completo. La documentación de Cloud no
se superpuso a la de DS.

Comando de la suite completa en cada raíz, con sus dependencias instaladas:

```powershell
New-Item -ItemType Directory -Force salida | Out-Null
$pruebasTemp = Join-Path (Get-Location).Path ('salida/pytest-' + [guid]::NewGuid().ToString('N'))
python -B -m pytest --ignore=salida -q -p no:cacheprovider --basetemp "$pruebasTemp"
python -B -m unittest discover -s tests -p "test_*.py"
```

Durante la preparación hubo errores de permisos de temporales de Windows y de
directorio padre ausente en una copia aislada. Se corrigió el entorno de ejecución
y se repitieron las comprobaciones; la tabla contiene los resultados finales.
Que estas suites pasen no valida el arranque de Streamlit ni el respaldo real de NIM.

## Siguientes acciones

1. Presentar un único PR de DA hacia `develop`, con revisión de DS, CE y SS.
   Declarar las 46 omisiones y los límites del filtro de ruido y de las simulaciones.
   La fusión queda sujeta a las aprobaciones acordadas por los subequipos.
2. Cuando DS publique el retorno corregido y concilie NVIDIA con `develop`, ejecutar
   las 38 pruebas de respaldo y las 8 del adaptador sobre la combinación. Después
   acordar una medición real del flujo completo, incluidos lotes, reintentos y Gemini.
   DeepSeek permanece fuera del alcance; las nuevas evaluaciones se centran en Nemotron.
3. Comprobar compatibilidad al incorporar Cloud #21 (autenticación) y #23 (guardado
   de activos aprobados). La conexión al panel de aprobación corresponde a SS;
   IAM y guardado real en la VM deben validarse con CE.

Los PR #18, #19 y #22 ya están integrados. La rama NVIDIA `a989951` continúa aparte
y todavía carece del retorno del adaptador. No se modifican aquí los módulos de
producción de DS, CE o SS ni se activa NVIDIA como proveedor de la aplicación.
