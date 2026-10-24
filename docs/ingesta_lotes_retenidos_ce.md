# Carga acumulativa interna — propuesta CE

Base: `feature/marco-cloud-ingesta-aislada-w5`, `a03f793`.
Preparación local; no instala servicios, no modifica INSUMOS ni concede IAM.

## Código y contrato

- `scripts/ingesta_db.py` contiene el escritor interno. Se extrajo de
  `tests/test_func_ingesta_oci.py`, que ahora contiene pruebas reales.
- `src/config/db_client.py` sigue siendo exclusivamente lector. No se
  reintroduce `sincronizar_conjunto` en la aplicación de Marketing.
- Se conserva el documento de siete campos con `contenido_textual`, versión
  1.0/1.1 y `total_spam_excluido`. No se cambia el contrato de salida de DS.
- Se elimina el máximo de 160. El texto no vacío se conserva literalmente,
  incluidos Unicode y saltos de línea, y se enlaza como `DB_TYPE_CLOB`.
- El FDK solo se importa al invocar el adaptador opcional `handler`. No es
  necesario instalar Functions para importar el módulo o correr sus pruebas.
  El adaptador no configura autenticación HTTP ni exposición de puertos.

## Reglas conservadoras para revisar con Marco y Arthur

1. Cargar A y luego B con IDs distintos conserva A y agrega B. No hay DELETE.
2. Repetir exactamente el lote no agrega filas ni suma otra vez su spam.
3. Un ID existente con contenido distinto rechaza el lote entero. Hasta acordar
   una política de IDs, no se sobrescriben datos de otra carga silenciosamente.
4. Un lote solapado sin recibo previo y con spam se rechaza: el JSON no trae
   los IDs del spam y no permite saber qué parte del contador ya se contó.
5. La huella incluye versión, registros completos ordenados por ID y contador
   de spam. Dos documentos idénticos son un reintento, no dos lotes distintos.
   Para diferenciar lotes genuinamente distintos pero idénticos (en particular
   vacíos con igual spam) hará falta acordar un identificador externo de lote.
6. Los metadatos reflejan el total acumulado de filas y spam de cargas únicas,
   no el total del último archivo. La respuesta indica insertados y repetido.
7. `instantanea_completa=True` sigue siendo una confirmación obligatoria del
   documento completo recibido; ya NO significa reemplazar toda la tabla.
   Los metadatos de salida se publican como versión 1.1 incluso para entrada 1.0.
8. Si hay filas sin metadatos o el total almacenado es incoherente, se rechaza
   la carga para revisar el estado previo en vez de inventar contadores.

## Requisito antes de probar contra Oracle

Revisar y aplicar manualmente `docs/sql/conjunto_consultable_cargas.sql`
como propietario escritor. Es una tabla de recibos por huella para que el
contador de spam sea idempotente; el lector público no necesita SELECT sobre
ella. El módulo Python no ejecuta DDL. Si no existe, la carga falla y revierte:
no omite silenciosamente esta protección. Mantener también las dos tablas
existentes, la columna `contenido_textual CLOB` y los permisos del escritor.

Las filas y sus metadatos existentes se conservan como base. No se inventa un
historial de recibos para cargas antiguas. Un reintento antiguo con spam y sin
recibo requiere conciliación explícita antes de cargarlo.

La escritura de filas nuevas, metadatos y recibo usa una sola transacción
con bloqueo NOWAIT de las tres tablas. Un error revierte todo; se requiere una
conexión exclusiva sin autocommit ni trabajo anterior activo.

Para llamar desde el proceso interno autorizado:

```python
from scripts.ingesta_db import sincronizar_conjunto

resultado = sincronizar_conjunto(documento, instantanea_completa=True)
```

Este import reemplaza la ubicación anterior de la escritura, no el del lector.
Coordinar con Marco el adaptador concreto del contenedor; aquí no se define
otro despliegue ni se modifica el trabajo que está preparando.

## Pruebas y límites

```sh
python -m pytest tests/test_db_client.py tests/test_func_ingesta_oci.py -q
```

Los dos fixtures `tests/fixtures/ingesta_ce/lote-*.json` son ficticios y no se
cargan automáticamente. Las conexiones y Vault están sustituidos por dobles;
el driver es real, pero el modelo transaccional no interpreta SQL Oracle.
Cubren A → B → B, textos mayores de 160 y 4000, Unicode, fecha nula, conflictos,
contador de spam, reversión, recibos y ausencia de escritura en el lector.
Queda pendiente probar SQL, CLOB, privilegios y flujo completo contra un esquema
de prueba autorizado. No usar estos resultados como evidencia de carga real.

La preparación de DA de esta rama todavía emite `contenido_corto`. No se cambia
su ownership: la carga final debe coordinarse con la versión de texto completo
de Genio/DA y la fuente original. Renombrar un texto ya recortado no lo recupera.

Referencia del driver para tipos y enlaces:
https://python-oracledb.readthedocs.io/en/latest/user_guide/bind.html

## Seguridad pendiente de infraestructura

Separar el código o no publicar puertos NO aísla Instance Principals entre dos
contenedores de la misma VM. Este parche no certifica que Marketing no pueda
leer el secreto escritor. CE debe revisar la identidad y las políticas reales
antes de exponer el frontend. No hay cambios de OCI, cuotas ni modelos aquí.
