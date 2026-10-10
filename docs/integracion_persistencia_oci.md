# Guardado de activos aprobados después del grafo

`src/app/guardado.py` conecta la salida final de
`procesar_paquete_entrega()` con el conector `src/config/oci_client.py`.
Usa `preparar_entrega_resultados()` y conserva cada activo de DS como
`{id_interaccion, tipo, contenido}`. No agrega campos al contrato de DS.

## Punto de integración con SS

El procesamiento de IA por sí solo no sube archivos. La interfaz debe conservar
su resultado y llamar a `guardar_resultado_aprobado()` después de que una persona
revise y seleccione los activos. El panel de aprobación aún no está conectado
en `app.py`; esta entrega prepara y prueba ese tramo del backend.

```python
from src.app.guardado import guardar_resultado_aprobado

# resultado es la salida ya generada por procesar_paquete_entrega(paquete).
# Esta selección debe venir de la revisión humana de ESE resultado.
informe = await guardar_resultado_aprobado(
    resultado,
    aprobados={("int-022", "linkedin"), ("int-002", "preguntas_frecuentes")},
    periodo="2026-semana-03",
    bucket="bkt-communitylab-marketing",
)
```

El ejemplo con `await` se ejecuta dentro de una función asíncrona. Un manejador
síncrono, sin bucle asyncio activo, puede usar `asyncio.run(...)`. El SDK trabaja
secuencialmente en un hilo; la función no lanza subidas en segundo plano sin
esperar su resultado. No hay llamadas a IA en el guardado.

SS debe asociar la selección a la salida que la persona vio y descartar las
aprobaciones si se regenera o reemplaza esa salida. La API recibe pares
`(id_interaccion, tipo)`; no considera automáticamente aprobados todos los
activos de un mensaje. Una selección vacía no requiere el SDK ni credenciales.

## Validación y resultado

- Se rechazan aprobaciones ajenas a la salida, nombres de objeto inseguros y
  contenido no serializable antes de la primera subida del lote aprobado.
- Se usan las cinco rutas de DS, incluida `insight_mejora`.
- El cuerpo JSON conserva el activo completo en UTF-8.
- El informe contiene `guardados`, `fallidos` y `omitidos`, separado del contrato
  de DS. La UI solo debe confirmar los elementos de `guardados`.
- Un error de servicio o timeout queda en `fallidos`, sin exponer el mensaje
  interno del SDK. Las demás subidas del lote continúan. No hay transacción ni
  reversión de objetos ya guardados.
- Se puede reintentar únicamente la selección fallida, sin volver a generar IA.
  La misma combinación de período, tipo e ID usa la misma clave y puede
  sobrescribir el objeto previo. Un timeout no demuestra que OCI no lo recibió;
  significa que el cliente no confirmó el guardado.

## Compatibilidad con el conector de Cloud

La integración solo usa `nombre_objeto_activo()` y `subir_json()`. No utiliza
`crear_cliente`, `obtener_cliente` ni el argumento `perfil`. La elección entre
perfil local e Instance Principals pertenece al conector.

El bucket es obligatorio y explícito. Para el entorno compartido acordado se
usa `bkt-communitylab-marketing` en Ashburn (`us-ashburn-1`). El prefijo de los
objetos lo define `nombre_objeto_activo`: `assets/` en la base actual de
`develop`, o `activos/` cuando se integre el cambio de Marco. Esta capa no
duplica esa regla ni cambia credenciales o infraestructura.

## Pruebas sin servicios reales

```text
python -m pytest tests/test_guardado_activos.py -q -rs
python -m pytest -q
```

Las pruebas usan un cliente simulado y no suben objetos ni invocan un LLM.
Incluyen selección vacía, aprobación por activo, las cinco rutas, JSON inválido,
errores 429/500/503, timeout, reintento parcial y ejecución del grafo real con
respuestas de IA simuladas. Los casos que necesitan OCI se omiten si falta el
SDK; los de aprobación vacía o inválida se ejecutan igualmente.

Quedan pendientes la llamada desde el panel de aprobación de SS, la integración
del conector definitivo del PR #21 y la prueba con Instance Principals desde la
VM. Esta evidencia offline no confirma permisos IAM ni una subida real.

### Resultados del 10 de octubre de 2026

Base: `develop` en `415a16d`. Entorno temporal con Python 3.14 y las dependencias
de `requirements.txt`; el entorno habitual del proyecto no se modificó.

| Comprobación | Resultado |
| --- | --- |
| Suite completa con OCI | 186 passed |
| Pruebas nuevas de guardado | 29 passed |
| Aceptación OCI de DA, copia temporal de `b3d7676` | 29 passed |
| Suite completa sin OCI | 159 passed, 22 skipped |
| unittest discover sin OCI | 80 pruebas, OK (1 omitida) |

El aviso de deprecación proviene de `google.genai` con Python 3.14. Las pruebas
asíncronas se ejecutaron fuera del sandbox, donde el bucle pudo recibir las
notificaciones del hilo; dentro del aislamiento también se bloqueaba un
ejemplo mínimo de `asyncio.to_thread`. No se usaron servicios remotos en estas
pruebas.
