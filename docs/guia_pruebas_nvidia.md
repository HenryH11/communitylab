# Guía de ejecución y pruebas — rama `feature/DS-Semana3-Nvidia`

Esta guía resume cómo validar la rama experimental NVIDIA NIM sin confundir
pruebas offline, aceptación de Data y pruebas live.

Los comandos se ejecutan desde la raíz del repositorio.

## 1. Objetivo de la guía

La rama debe demostrar por separado:

1. que el flujo estable sigue funcionando;
2. que NVIDIA NIM puede seleccionarse como proveedor;
3. que el adaptador valida salida estructurada;
4. que los retries NIM funcionan;
5. que el fallback NIM -> Gemini funciona;
6. que un doble fallo conserva información segura y puede llegar a recuperación;
7. que la suite normal no llama a APIs reales;
8. que las pruebas live se ejecutan solo de forma explícita.

## 2. Entorno

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Dependencias relevantes de la rama:

```text
langchain
langchain-core
langchain-google-genai
langchain-openai
langgraph
pydantic
python-dotenv
pytest
```

## 3. Variables de entorno

### Flujo estable

```text
GEMINI_API_KEY
```

En el diseño objetivo de esta rama, si no se define ningún proveedor, análisis y generación deben usar NVIDIA NIM como primario y Gemini debe quedar como respaldo.

### NVIDIA NIM

```text
NVIDIA_API_KEY
COMMUNITYLAB_PROVEEDOR_ANALISIS
COMMUNITYLAB_PROVEEDOR_GENERACION
COMMUNITYLAB_NVIDIA_TIMEOUT_SEGUNDOS
```

Las variables permiten sobrescribir explícitamente el proveedor si hace falta:

```powershell
$env:COMMUNITYLAB_PROVEEDOR_ANALISIS = "nvidia_nim"
$env:COMMUNITYLAB_PROVEEDOR_GENERACION = "nvidia_nim"
```

> **Importante:** esos valores no son necesarios para el uso normal de esta
rama: `configuracion_ia.py` usa NVIDIA NIM como proveedor primario por defecto
tanto en análisis como en generación. Las variables sirven para hacer un override
explícito; por ejemplo, seleccionar Gemini directamente.

Timeout por defecto:

```text
3.0 segundos por intento
```

Para una prueba del recorrido NIM -> Gemini en vivo se necesitan tanto
`NVIDIA_API_KEY` como `GEMINI_API_KEY`.

No publiques `.env` ni copies credenciales a logs compartidos.

## 4. Prueba principal: suite offline completa

Ejecuta:

```powershell
python -m pytest -q
```

Esta es la validación principal antes de cualquier prueba live.

El criterio de aceptación de la suite completa es:

```text
0 failed
pytest normal sin llamadas reales a NVIDIA/Gemini
```

El conteo total no se fija en esta guía porque aumenta cuando se agregan pruebas.

Advertencia observada:

```text
DeprecationWarning de google.genai
```

La advertencia es externa a la lógica de CommunityLab y no representa un fallo
de la suite.

### Qué valida la suite normal

Incluye:

- ingesta y contratos de Data;
- procesamiento por lotes;
- router determinista;
- prompts;
- selección de proveedor;
- configuración NVIDIA;
- adaptador NVIDIA con transporte simulado;
- retry;
- fallback de análisis;
- fallback de generación;
- doble fallo;
- recuperación;
- observabilidad;
- evaluación de regresión.

La suite normal debe permanecer sin llamadas reales a NVIDIA, Gemini u OCI.

## 5. Pruebas focales de NVIDIA

### 5.1 Adaptador y configuración NVIDIA

```powershell
python -m pytest tests/agents/test_proveedor_nvidia.py -q
```

Revisa:

- `NVIDIA_API_KEY` requerida;
- endpoint NIM;
- modelo Nemotron;
- timeout por defecto/configurable;
- `max_retries=0` en el cliente NVIDIA;
- retorno de una cadena ejecutable;
- JSON mode;
- validación Pydantic;
- rechazo de respuestas vacías, JSON roto o fuera de esquema.

### 5.2 Selección de proveedor

```powershell
python -m pytest tests/agents/test_seleccion_proveedor.py -q
```

Revisa:

```text
Gemini = default
NVIDIA = seleccionable
proveedor desconocido = rechazado
análisis y generación = configurables por separado
```

### 5.3 Fallback de análisis

```powershell
python -m pytest tests/agents/test_fallback_analisis.py -q
```

Debe proteger:

- 3 intentos NIM cuando el error es reintentable;
- Gemini llamado una sola vez desde la capa de fallback;
- fallback exitoso sin `fallos`;
- doble fallo marcado como reintentable cuando corresponde;
- correlación del retry con `id_interaccion`.

### 5.4 Fallback de generación

```powershell
python -m pytest tests/agents/test_fallback_generacion.py -q
```

Debe proteger:

- fallback por ruta;
- multirouting independiente;
- conservación de rutas exitosas;
- doble fallo de una ruta sin detener las demás;
- clasificación permanente vs reintentable;
- correlación con `id_interaccion` y `ruta`.

### 5.5 Retry, observabilidad y recuperación

```powershell
python -m pytest tests/agents/test_observabilidad_reintentos.py -q
```

Revisa:

```text
retry
backoff
clasificación transitoria
fallos estructurados
ContextVar de correlación
recuperación posterior
```

## 6. Regresión sensible después de tocar fallback

Si modificas:

```text
fallback_ia.py
modelo_ia.py
cadenas.py
nodo_analizador.py
nodos_generadores.py
observabilidad.py
reintentos.py
recuperacion.py
```

ejecuta primero:

```powershell
python -m pytest `
  tests/agents/test_fallback_analisis.py `
  tests/agents/test_fallback_generacion.py `
  tests/agents/test_observabilidad_reintentos.py `
  tests/agents/test_seleccion_proveedor.py `
  -q
```

Checkpoint observado durante el refactor:

```text
37 passed
```

Después ejecuta siempre:

```powershell
python -m pytest -q
```

## 7. Diferencia entre retry, fallback y recuperación

### Retry

Mismo proveedor:

```text
NIM -> NIM -> NIM
```

Ocurre en `ejecutar_con_reintentos()`.

### Fallback

Cambio de proveedor:

```text
NIM agotado/no utilizable -> Gemini
```

Ocurre en `invocar_modelo_con_fallback()`.

### Recuperación

Nueva pasada posterior sobre un fallo final:

```text
resultado fallido -> seleccionar ID/ruta reintentable -> reprocesar
```

Ocurre en `recuperacion.py`.

Una prueba que valida retry no sustituye una prueba de fallback; una prueba de
fallback no sustituye una prueba de recuperación.

## 8. Qué errores deben activar fallback

Casos esperados:

```text
429
timeout
conexión
500
502
503
504
configuración/clave NIM ausente
salida vacía/inválida
JSON roto
salida fuera del esquema
```

Los errores propios de la entrada, como un `ValueError` de payload, no deben
activar Gemini.

## 9. Aceptación de Data Analyst — PR #24

Data publicó en `feature/jhonattan-validacion-semana3`:

```text
tests/agents/test_adaptador_nvidia_integracion.py
tests/agents/test_respaldo_nim_gemini.py
```

Cobertura:

```text
8 pruebas del adaptador
38 pruebas del respaldo NIM -> Gemini
46 criterios totales
```

Prevalidación realizada contra esta rama:

```text
8 passed
38 passed
46/46 total
0 failed
```

Estas pruebas usan transporte/modelos sustituidos y no consumen cuota.

### Mientras el PR #24 siga abierto

Si necesitas repetir la prevalidación sin fusionar el PR:

**Git: 2. MODIFICACIÓN LOCAL — solo actualiza referencias locales**

```powershell
git fetch origin feature/jhonattan-validacion-semana3
```

Extrae temporalmente las dos pruebas fuera del repositorio:

```powershell
$tmp = Join-Path $env:TEMP "communitylab-da-acceptance"
New-Item -ItemType Directory -Force $tmp | Out-Null

git show FETCH_HEAD:tests/agents/test_adaptador_nvidia_integracion.py |
    Set-Content -Encoding utf8 `
    (Join-Path $tmp "test_adaptador_nvidia_integracion.py")

git show FETCH_HEAD:tests/agents/test_respaldo_nim_gemini.py |
    Set-Content -Encoding utf8 `
    (Join-Path $tmp "test_respaldo_nim_gemini.py")
```

Ejecuta:

```powershell
python -m pytest `
    (Join-Path $tmp "test_adaptador_nvidia_integracion.py") `
    -q --rootdir=.

python -m pytest `
    (Join-Path $tmp "test_respaldo_nim_gemini.py") `
    -q --rootdir=.
```

### Cuando el PR #24 llegue a `develop`

Repite la aceptación desde los archivos versionados normales y vuelve a ejecutar
la suite completa antes del PR final NVIDIA -> `develop`.

## 10. Confirmar que las pruebas live no entran a pytest normal

```powershell
python -m pytest tests/integracion --collect-only -q
```

Resultado esperado con la nomenclatura actual:

```text
no tests collected
```

Los archivos live comienzan con `prueba_`, no con `test_`.

## 11. Pruebas live NVIDIA

> Ejecutar solo cuando se quiera consumir red/cuota y `NVIDIA_API_KEY` esté
> configurada.

Archivos disponibles:

```text
tests/integracion/prueba_nvidia_nim_estructurado.py
tests/integracion/prueba_nvidia_nodo_analizador.py
tests/integracion/prueba_nvidia_analisis_lote.py
tests/integracion/prueba_nvidia_analisis_router.py
tests/integracion/prueba_nvidia_generacion_faq.py
tests/integracion/prueba_nvidia_generacion_multiruta.py
```

### Orden recomendado

#### 1. Adaptador estructurado

```powershell
python -B -m pytest `
  tests\integracion\prueba_nvidia_nim_estructurado.py `
  -v -s -p no:cacheprovider
```

#### 2. Nodo analizador

```powershell
python -B -m pytest `
  tests\integracion\prueba_nvidia_nodo_analizador.py `
  -v -s -p no:cacheprovider
```

#### 3. Análisis por lote

```powershell
python -B -m pytest `
  tests\integracion\prueba_nvidia_analisis_lote.py `
  -v -s -p no:cacheprovider
```

#### 4. Análisis + router

```powershell
python -B -m pytest `
  tests\integracion\prueba_nvidia_analisis_router.py `
  -v -s -p no:cacheprovider
```

#### 5. Generación FAQ

```powershell
python -B -m pytest `
  tests\integracion\prueba_nvidia_generacion_faq.py `
  -v -s -p no:cacheprovider
```

#### 6. Generación multiruta

```powershell
python -B -m pytest `
  tests\integracion\prueba_nvidia_generacion_multiruta.py `
  -v -s -p no:cacheprovider
```

Estas pruebas validan inferencia real de NIM. No deben presentarse como prueba
del recorrido completo de fallback NIM -> Gemini salvo que el caso ejecutado
realmente provoque y observe dicho fallback.

## 12. Pruebas live Gemini heredadas

```powershell
python -B -m pytest `
  tests\integracion\prueba_paquete_completo_datos.py `
  -v -s -p no:cacheprovider

python -B -m pytest `
  tests\integracion\prueba_entrega_resultados_funcional.py `
  -v -s -p no:cacheprovider
```

Requieren:

```text
Internet
GEMINI_API_KEY
cuota
```

La prueba de entrega funcional escribe artefactos en `output/`.

## 13. Evidencia de validación del cambio de proveedor por defecto

Pruebas focales confirmadas después de cambiar el default:

```text
tests/agents/test_seleccion_proveedor.py
10 passed

tests/agents/test_observabilidad_reintentos.py
20 passed

aceptación temporal de Data Analyst
test_adaptador_nvidia_integracion.py
8 passed

aceptación temporal de Data Analyst
test_respaldo_nim_gemini.py
38 passed
```

Las dos pruebas históricas de retry de generación en
`test_observabilidad_reintentos.py` fuerzan `COMMUNITYLAB_PROVEEDOR_GENERACION=gemini`
de forma explícita. Así prueban el retry directo histórico sin depender del nuevo
default. El comportamiento NIM -> retries -> Gemini se prueba por separado en
`test_fallback_generacion.py` y en las pruebas de aceptación de Data.

También se actualizó la expectativa de `tests/test_entrega_ia.py` para que
`informe["modelo_ia"]` describa NVIDIA NIM cuando no existe override. No se
modificó lógica de `src/datos/*`.

Antes de commit/push es obligatorio ejecutar:

```powershell
python -m pytest -q
```

y exigir cero fallos.

La aceptación de los 46 casos de Data se ejecutó desde copias temporales mientras
el PR #24 continúa fuera de `develop`. Después de que ese PR se fusione, debe
repetirse la validación usando las pruebas ya versionadas en `develop`.

## 14. Logs durante las pruebas

Logger:

```text
communitylab.ciencia_datos
```

Archivo por defecto:

```text
salida/logs/ciencia_datos.jsonl
```

Variables:

```text
COMMUNITYLAB_LOGS
COMMUNITYLAB_LOG_DIR
COMMUNITYLAB_LOG_LEVEL
```

Eventos útiles:

```text
reintento_programado
operacion_fallida
proveedor_ia_resuelto
llm_inicio
llm_fin
llm_error
reprocesamiento_finalizado
```

Para retries NVIDIA, revisa especialmente:

```text
id_interaccion
ids_interaccion
ruta
etapa = proveedor_primario
proveedor = nvidia_nim
intento
```

## 15. Errores frecuentes

### `ErrorConfiguracionProveedor: No se encontró NVIDIA_API_KEY`

La rama intenta usar NVIDIA pero no encuentra su credencial.

Comprueba:

```powershell
$env:NVIDIA_API_KEY
```

No imprimas la clave en capturas o documentación compartida.

### Timeout NVIDIA

El valor por defecto es:

```text
3 segundos por intento
```

No significa tres segundos totales. Pueden existir varios intentos y después un
fallback a Gemini.

### `ErrorSalidaProveedor`

NVIDIA respondió, pero el contenido no cumple el contrato esperado.

Puede provocar retries NIM y después fallback.

### `ErrorFallbackProveedores`

Fallaron NIM y Gemini.

Revisa `fallos[]`, `reintentable`, `error_primario` y `error_respaldo`.

### Gemini respondió después del fallo NIM

Eso es fallback exitoso, no un fallo final. La salida debe continuar sin añadir
un fallo únicamente por haber cambiado de proveedor.

## 16. Orden de validación antes de un PR NVIDIA -> develop

1. Trabajar con working tree limpio.
2. Sincronizar la referencia de `develop`.
3. Revisar diferencias antes de mergear.
4. Resolver conflictos respetando ownership.
5. Ejecutar pruebas focales.
6. Ejecutar `python -m pytest -q`.
7. Ejecutar aceptación DA cuando ya esté integrada en `develop`.
8. Ejecutar únicamente las pruebas live acordadas.
9. Revisar logs y tiempos.
10. Hacer un último sync de `develop`.
11. Repetir la suite offline.
12. Abrir/revisar el PR NVIDIA por separado.

No reemplazar la implementación estable por esta experimental sin pruebas y
revisión del equipo.

## 17. Comandos Git: clasificación requerida

Antes de ejecutar Git en este proyecto, clasifica el comando.

### 1. SOLO LECTURA

Ejemplos:

```powershell
git status --short --branch
git log -5 --oneline --decorate
git diff --check
git diff
git rev-list --left-right --count HEAD...origin/develop
git ls-tree -r --name-only origin/develop
```

### 2. MODIFICACIÓN LOCAL

Ejemplos:

```powershell
git fetch origin develop
git add ...
git commit ...
git merge origin/develop
```

`merge` puede introducir conflictos; revisar antes de ejecutarlo.

### 3. MODIFICACIÓN REMOTA

Ejemplos:

```powershell
git push origin feature/DS-Semana3-Nvidia
```

Push, merge remoto y operaciones destructivas requieren confirmación explícita.

## 18. Checklist rápido

Antes de declarar la rama lista:

```text
[ ] working tree limpio
[ ] sincronizada con develop
[ ] adaptador NVIDIA devuelve cadena
[ ] timeout NVIDIA validado
[ ] NVIDIA NIM es default de análisis y generación
[ ] Gemini sigue seleccionable explícitamente
[ ] fallback análisis validado
[ ] fallback generación validado
[ ] doble fallo validado
[ ] recuperación validada
[ ] observabilidad conserva ID/ruta
[ ] suite completa offline verde
[ ] aceptación DA verde
[ ] live ejecutado solo si corresponde
[ ] sin claves ni secretos en commits/logs compartidos
```
## 19. Resultado de la evaluación comparativa de proveedores

La rama `feature/DS-Semana3-Nvidia` mantiene NVIDIA NIM como proveedor
primario por defecto porque su propósito es experimental.

Sin embargo, la evaluación semántica final realizada con un holdout congelado
de 30 casos favoreció a Gemini.

Resultados por moda de 3 corridas:

| Dimensión | NVIDIA NIM / Nemotron | Gemini |
| --- | ---: | ---: |
| Sentimiento | 66.7% | 86.7% |
| Tema principal | 86.7% | 96.7% |
| Tipo detectado | 86.7% | 90.0% |
| Triple correcto | 56.7% | 76.7% |

El holdout fue etiquetado antes de ejecutar ambos proveedores y su SHA-256 es:

La conclusión de esta prueba no cambia automáticamente la configuración de
esta rama experimental.
Estado actual:
feature/DS-Semana3-Nvidia:
NVIDIA NIM -> primario
Gemini     -> fallback

Propuesta para discutir antes de integrar a la línea estable:
Gemini      -> primario
NVIDIA NIM  -> posible respaldo

La inversión del fallback Gemini -> NVIDIA NIM todavía no está implementada
y requeriría cambios y pruebas específicas.
La evaluación completa está documentada en:
docs/evaluacion_proveedores_semana3.md