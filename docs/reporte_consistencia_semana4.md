# Semana 4: preparación de la auditoría de consistencia

Fecha: 12 de octubre de 2026. DA: Gustavo y Jhonattan.

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

Rama: `feature/jhonattan-auditoria-semana4`, creada desde DA `f5e059c`. Esa base
contiene `develop` `415a16d` y el PR #24 aprobado pero aún pendiente de fusión.
Los cambios de esta rama se limitan a casos sintéticos, pruebas y este reporte.
No cambia el dataset compartido ni código de producción de Datos, DS, SS o CE.
Antes del PR de Semana 4, incorporar el `develop` que incluya #24 y volver a
comprobar la compatibilidad con los componentes que se hayan integrado.

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

Resultados locales del 12 de octubre sobre DA `f5e059c` más estos archivos:

| Ejecución | Resultado |
| --- | --- |
| Pruebas focalizadas de Semana 4 | 7 aprobadas |
| Suite completa | 280 aprobadas, 46 omitidas, 132 subpruebas aprobadas; sin fallos |
| `unittest discover` | 85 pruebas, OK |

Las 46 omisiones siguen correspondiendo a NVIDIA, aún fuera de esta base. Unittest
no ejecuta las siete funciones nuevas de pytest ni sustituye su resultado.
La suite completa se ejecutó fuera del entorno restringido por los problemas de
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

La evaluación de clasificación de DS (`b141c93`) es un antecedente distinto: no
evalúa la calidad de los activos ni reemplaza este trabajo. El proveedor para la
demo debe acordarse antes de registrar evidencia real de generación.

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
