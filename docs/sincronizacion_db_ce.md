# Ajuste CE del cliente de DB: propuesta para revisión de Marco

> Actualización 2026-10-27: el contrato vigente es 1.2, con ocho campos y
> `autor` nullable (máximo 100 caracteres). El servicio actual hace cargas
> acumulativas, no retira registros ni sobrescribe IDs en conflicto. Los
> documentos 1.0/1.1 siguen admitidos para reintentos sin perder el autor ya
> almacenado. La lectura selecciona `autor` y proyecta el contrato 1.2.
> Las secciones siguientes registran la propuesta histórica de instantánea;
> para operación vigente ver [Conjunto Consultable](conjunto_consultable.md)
> y [manual de código](manual_lectura_codigo.md). No se ha ejecutado DDL ni
> escritura en Oracle como parte de esta actualización local.

## Lectura del agente y presupuesto de IA

La captura de Oracle no se limita a 20 filas para el agente. Los filtros y
agregados se resuelven sobre las coincidencias; los listados literales de campos
se obtienen en Python, no solo el de autores. El análisis y los borradores
procesan toda la selección por lotes de contexto y consolidan los hallazgos.
No se confunde límite de tokens por llamada con cantidad máxima de registros.

Solo el equipo modifica `COMMUNITYLAB_CONTEXTO_TOKENS` (32768 inicialmente) y
`COMMUNITYLAB_SALIDA_TOKENS` (4096) en el entorno del servidor de Marketing.
No son ajustes del visitante ni cambian SQL, permisos o límites de Oracle.
El presupuesto es compartido con el proveedor de respaldo y usa una estimación
conservadora, no un tokenizer exacto. Los detalles y limitaciones están en
[flujo conversacional](agente_conversacional.md#presupuesto-de-contexto-y-cobertura).

Marketing aplica además un presupuesto total por consulta (30 intentos y 250000
tokens reservados inicialmente), con hasta dos consultas simultáneas por proceso.
Cuenta interpretación, lotes, reintentos, respaldo, correcciones y verificación.
La cuota horaria compartida es configurable pero arranca desactivada, sin techo
de gasto acumulado. No se cambian permisos ni límites de Oracle. Las referencias
de las síntesis se conservan por hallazgo, no por todo el lote procesado.
Ver [admisión y presupuesto](agente_conversacional.md#admisión-y-presupuesto-total-por-consulta).

Las consultas analíticas generadas por IA ahora requieren revisión factual de
su texto completo antes de guardarse. La revisión usa mensajes originales y
agregados calculados por Python; no trata los hallazgos del redactor como prueba.
Consume el mismo presupuesto por consulta y no ejecuta SQL ni modifica Oracle.
Los listados locales no necesitan una segunda llamada de verificación.

## Propuesta histórica de sincronización (no operación vigente)

No se ha ejecutado contra INSUMOS ni se han cambiado permisos o infraestructura.
Parte de `feature/marco-cloud-cliente-bd-w5` y conserva su conexión mediante Vault.

## Decisión que debe confirmar DA/DS/CE antes de activar

Esta implementación publica **una instantánea completa del único conjunto** de
la tabla. No es un importador incremental ni admite varios datasets en ella.
La llamada exige `instantanea_completa=True`. Sin esa confirmación, no escribe.
No inferir que un archivo parcial es completo solo porque su contador coincide.

```python
informe = sincronizar_conjunto(documento, instantanea_completa=True)
```

Valida primero versión, siete campos, total, contador de spam, duplicados,
tipos, UTF-8, contenido completo no vacío y fecha UTC de segundos o null.
`canal`, `sentimiento`, `tema` y `tipo` deben ser textos no vacíos, nunca null,
para coincidir con las columnas NOT NULL comunicadas por Marco y DA. Se validan
todos los registros antes de abrir una conexión o escribir, sin recortar ni
modificar los textos recibidos. `fecha` conserva la posibilidad de ser null.
Conserva versión 1.0 histórica; en 1.1 exige total_spam_excluido.

Dentro de una transacción, bloquea ambos objetos con NOWAIT, hace MERGE,
retira **por ID** las filas que ya no están y guarda los metadatos. Una
instantánea vacía confirmada retira todas las filas del conjunto: no usar esa
opción con cargas parciales. Un error revierte toda la operación. No usa TRUNCATE.
La conexión inyectada debe ser exclusiva, sin transacción abierta y sin autocommit.

## Migración pendiente, no automática

Actualización de texto completo: Marco confirmó `contenido_textual` como nombre
definitivo al actualizar la tabla para CLOB. El contrato JSON y el SQL usan ese
campo; regenerar los documentos antiguos que usaban `contenido_corto`.
El cargador usa
un bind explícito `DB_TYPE_CLOB`, incluso cuando el lote mezcla textos cortos
y textos que exceden los límites de VARCHAR2. La lectura materializa los LOB
mediante `read()` dentro del cursor/conexión y devuelve cadenas Python, sin
cambiar opciones globales del driver. También sigue aceptando filas devueltas
directamente como cadenas.

No se aplica DDL desde la aplicación. La prueba real de
MERGE/lectura CLOB con TLS y permisos queda pendiente de Cloud. Reconstruir
y recargar los registros desde la fuente original: los datos ya truncados no
se recuperan por cambiar el tipo de columna.

Marco/DBA debe revisar `docs/sql/conjunto_consultable_meta.sql` y aplicarlo en el
esquema propietario antes de cargar. Después, publicar una instantánea completa
validada; la lectura no inventa metadatos para la tabla antigua. No crear tablas
desde el agente ni durante el guardado (el DDL tiene implicaciones transaccionales).

La lectura usa una sola sentencia para filas y metadatos, incluso para un conjunto
vacío, y conserva la versión y total_spam_excluido. Rechaza un total inconsistente.

## Separación de usuarios

La carga usa DB_USER, DB_DSN y DB_PASSWORD_SECRET_OCID como el cliente de Marco.
La lectura por defecto exige DB_READ_USER y DB_READ_PASSWORD_SECRET_OCID; usa
DB_READ_DSN o el mismo DB_DSN. No vuelve silenciosamente al usuario de carga.

El usuario lector debe ser distinto del propietario/cargador, con CREATE SESSION
y SELECT únicamente sobre las dos tablas. Los grants reales no pueden comprobarse
offline. El DBA debe resolver los nombres sin esquema: por ejemplo, sinónimos
privados hacia ambas tablas, creados por el DBA, no dando CREATE SYNONYM al agente.
También se admite inyectar una conexión lectora ya configurada por el despliegue.

Separar las credenciales DB no aísla por sí solo los permisos IAM de una VM: si la
misma identidad puede obtener el secreto escritor, el agente conserva ese riesgo.
CE debe acordar el aislamiento del frontend público y su acceso exclusivo al
secreto de lectura. No publicar aún el agente con la identidad del cargador.

## Límites de esta entrega

No conecta la app ni el agente automáticamente, no cambia el contrato de DS,
no modifica src/datos y no crea recursos de OCI. No se ha probado SQL, TLS,
grants ni Vault en INSUMOS; eso requiere revisión de Marco y una prueba controlada.

Pruebas offline: `python -m pytest tests/test_db_client.py -q`.

Verificación del 20 oct 2026 (sin red ni credenciales): 67 pruebas del cliente y
suite completa **679 passed, 208 subtests passed**. Se importó oracledb 26.0.1;
las conexiones, Vault y las operaciones de DB se simularon. Sin oracledb, las
67 pruebas del cliente se omiten sin romper pytest. El formato y git diff --check
también se verificaron. La suite verde no reemplaza la prueba SQL en INSUMOS.

Referencias primarias usadas para transacciones y bloqueo:
- https://python-oracledb.readthedocs.io/en/latest/user_guide/txn_management.html
- https://docs.oracle.com/en/database/oracle/oracle-database/26/sqlrf/LOCK-TABLE.html
