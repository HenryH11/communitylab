# Revisión de integración NIM — 8 de octubre de 2026

Data Analyst: Gustavo y Jhonattan. Base de DA: `5e73233`, que conserva el filtro de
ruido de `14b8032`. Los cambios de producción de DS se prepararon en copias aisladas;
no se fusionaron en la rama compartida ni se publicaron en ramas de otros equipos.

## DeepSeek y timeout confirmados

El ensayo del 6 de octubre usó exactamente `deepseek-ai/deepseek-v4.1-flash`.
La [ficha oficial](https://build.nvidia.com/deepseek-ai/deepseek-v4.1-flash)
consultada nuevamente el 8 de octubre sigue ofreciendo un endpoint gratuito.
También se comprobó la [ficha de Nemotron](https://build.nvidia.com/nvidia/nemotron-3.5-lightning-30b-a3b).
Después de esa comprobación, Gustavo y Jhonattan decidieron retirar DeepSeek del
ensayo. El catálogo y los comandos sugeridos conservan únicamente Nemotron. La
CLI rechaza DeepSeek antes de llamar al transporte. Los timeouts anteriores se
conservan como evidencia histórica, no como prueba de deprecación. No hubo nuevas
inferencias reales ni quedan corridas de DeepSeek pendientes en el alcance acordado.

DS confirmó e implementó `COMMUNITYLAB_NVIDIA_TIMEOUT_SEGUNDOS=3` y el cliente
`ChatOpenAI`, con `langchain-openai` como dependencia. El timeout se aplica en el
cliente; la capa de aplicación realiza hasta tres intentos primarios con esperas
antes de activar Gemini. No es un límite total de tres segundos por mensaje.
El ensayo aislado mantiene `--umbral-segundos` separado de `--timeout`: cambiar el
umbral no cancela llamadas ni activa respaldo.

## Defecto reproducido y corrección propuesta

En DS NVIDIA `a989951`, `obtener_modelo_nvidia_estructurado()` construye el modelo
y define la preparación de entrada y la validación, pero no devuelve la cadena.
Su resultado es `None`, y la composición del prompt produce `TypeError` antes
de enviar la solicitud. Los tests que sustituyen la cadena completa no cubren
esta construcción.

Se añadió `tests/agents/test_adaptador_nvidia_integracion.py`, con ocho casos que
usan el adaptador y la cadena de análisis reales, sustituyendo el transporte:
salida válida, cuatro salidas inutilizables, éxito NIM sin respaldo y activación
de Gemini ante timeout o JSON roto. No requieren claves ni llaman al proveedor.

La corrección consiste en devolver al final de la función:

```python
return (
    RunnableLambda(preparar_entrada)
    | modelo_json
    | RunnableLambda(validar_respuesta)
)
```

El archivo nuevo se omite si el módulo del proveedor todavía no está en la rama.
Una dependencia rota dentro de un proveedor presente no se oculta como omisión.
También se aisló `.env` en los tests del ensayo mediante `PYTHON_DOTENV_DISABLED`:
la configuración nueva de DS carga dotenv al preparar el paquete y podía reponer
la clave que la prueba de ausencia había eliminado. El bloqueo de transporte de
la prueba impidió tráfico real durante la detección de este problema.

## Conciliación de las ramas

`b5bbb81` de DS Semana 3 aporta compatibilidad con el import antiguo de
`procesar_paquete_entrega` y correcciones de los cuatro estados manuales.
La rama NVIDIA `a989951` no los contiene. Al combinar ambas aparece un conflicto
en `nodo_analizador.py`: debe conservarse `ids_lote` para los mensajes preparados
correctamente y, a la vez, `max_intentos=_max_intentos_externos()` para no multiplicar
los reintentos de NVIDIA. Esa resolución se probó junto con el retorno faltante.

El parche externo `conciliacion_ds_nvidia.patch` incluye esas correcciones en cinco
archivos de DS y se comprobó con `git apply --check` contra `a989951`. No contiene
los cambios de Cloud o de la aplicación. Está en los entregables locales del
8 de octubre para revisión por DS; no forma parte de los cambios de producción de DA.

## Resultados

Entorno local: Python 3.12, `langchain-openai` 1.7.0, `langchain-core` 1.6.9,
`openai` 3.26.1 y OCI 2.187.2. `pip check` no detectó dependencias incompatibles.

| Comprobación | Resultado |
| --- | --- |
| Ocho casos nuevos contra el adaptador publicado `a989951` | 8 fallidas: reproduce el defecto |
| Los mismos casos con el retorno corregido | 8 aprobadas |
| Rama DA `5e73233` más pruebas y documentación locales | 228 aprobadas, 46 omitidas, 6 fallos esperados; 127 subpruebas aprobadas |
| Copia conciliada descrita abajo | 328 aprobadas, 0 omitidas, 0 fallos esperados; 132 subpruebas aprobadas |
| `unittest discover` en DA | 84 pruebas, OK |

Después de retirar DeepSeek por acuerdo de DA se repitieron las 22 pruebas del
ensayo: todas aprobaron. El plan con Nemotron y dos repeticiones sobre tres
mensajes produce seis solicitudes; DeepSeek se rechaza antes de acceder a la red.
Las cifras de integración anteriores corresponden a la validación previa a ese
ajuste de catálogo; no se repitió la suite completa por ese cambio acotado.

Las 46 omisiones en DA son los 38 casos de respaldo y los ocho nuevos del adaptador,
porque DS NVIDIA todavía no está integrado allí. Los seis fallos esperados de DA
se mantienen hasta incorporar las correcciones de DS, Cloud y SS.

La copia de integración combina DA `5e73233`, DS `b5bbb81`, NVIDIA `a989951`, la
corrección del adaptador y la resolución del conflicto, el código de Cloud del
PR #18 `7d756df` y `app.py` del PR #19 `dd8aba4`. Solo en esa copia se retiraron las
seis marcas `xfail`; las pruebas correspondientes pasaron normalmente. Las fuentes
quedan en `salida/.revision-20261008-integracion/`, ignorada por Git.

Se ejecutó la suite completa con `python -B -m pytest --ignore=salida -q -p
no:cacheprovider`, usando una ruta `--basetemp` nueva dentro de `salida/`. La prueba
del adaptador puede reproducirse con:

```powershell
python -B -m pytest tests/agents/test_adaptador_nvidia_integracion.py -q -p no:cacheprovider
```

No hubo llamadas reales a NIM, Gemini u OCI. Las pruebas de la aplicación son
estáticas, no una comprobación visual ni una ejecución de Streamlit. Estos
resultados no equivalen a aprobación de los PR ni prueban latencia real del respaldo.

## Pendientes para integración formal

- DS debe revisar y aplicar el retorno, conciliar sus ramas y ejecutar los ocho
  casos nuevos antes de publicar la combinación definitiva.
- DA revisa con Gustavo la evidencia y actualiza las marcas de pruebas cuando
  esas correcciones entren efectivamente en la rama utilizada.
- Medir el tiempo completo NIM → reintentos → Gemini en una prueba real acordada,
  incluyendo el análisis por lotes; no extrapolar del ensayo individual.
- Mantener las próximas evaluaciones centradas en Nemotron y el respaldo Gemini,
  según el alcance acordado por Gustavo y Jhonattan. DeepSeek queda retirado.
