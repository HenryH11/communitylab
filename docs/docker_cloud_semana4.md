# Docker para Cloud — Semana 4

Base: trabajo de Arthur en `feature/DS-Semana3-Nvidia` (PR #28).
Este ajuste no cambia modelos, contratos JSON ni el guardado de activos.

## Ejecución

Desde la raíz: `docker compose up --build -d`.
El frontend se construye con `Dockerfile.frontend` y
`requirements.frontend.txt`; el backend usa `Dockerfile.backend` y
`requirements.backend.txt`. Para desarrollo local se conserva
`pip install -r requirements.txt`, que incluye ambos manifiestos.
La aplicación de Marketing escucha en el puerto 8501. Compose lee `.env`
para interpolar solo las variables enumeradas en el servicio; no inyecta el
archivo entero. Las claves nunca se incluyen en la imagen o Git.
No publicar la app en Internet sin acordar los
controles de acceso; publicar un puerto no configura las reglas de OCI.

### Separación de Marketing y equipo técnico

- **Marketing:** `streamlit run src/app/app.py`. No incluye Datos ni la curaduría
  interna, ignora `COMMUNITYLAB_MODO_INTERNO` y no usa lotes internos de sesión.
- **Equipo técnico:** `streamlit run src/app/app_interna.py`. Conserva Datos,
  procesamiento y curaduría. Es otro proceso con sesiones independientes.
- `src/app/interfaz.py` comparte la interfaz, pero cada entrada fija explícitamente
  su modo. No hay selector de modo en el navegador ni una página de Streamlit
  que permita cambiar de aplicación.
- Para iniciar solo el servicio interno con Compose:
  `docker compose --profile interno up --build -d communitylab-interno`.
  Crear antes `.env.interno` fuera de Git, con la configuración propia del equipo
  técnico. No copiar secretos internos al entorno de Marketing.
- El servicio interno está desactivado por defecto, usa su propio volumen
  `communitylab-interno-salida` y escucha solo en `127.0.0.1:8502` del host.
  Acceder mediante túnel autorizado; no publicar ese puerto ni enrutarlo desde
  el dominio de Marketing. El servicio público conserva su volumen existente.
- Marketing recibe únicamente `DB_READ_USER`, `DB_READ_DSN` y
  `DB_READ_PASSWORD_SECRET_OCID`. Definir `DB_READ_DSN` explícitamente: el servicio
  no recibe `DB_DSN`, `DB_USER` ni `DB_PASSWORD_SECRET_OCID`.
  Al retirar la inyección completa de `.env`, cualquier ajuste adicional autorizado
  debe enumerarse expresamente en el servicio, no volver a montar el entorno interno.

**Límite importante:** separar contenedores en una misma VM no separa las
identidades OCI de Instance Principals. Cloud debe desplegar Marketing con una
identidad que solo pueda leer el secreto `ro_query`, consultar ambas tablas y
leer el catálogo. La identidad interna y la del ejecutor diario deben conservar
sus permisos de escritura por separado. Si la VM compartida accede a ambos
secretos, el aislamiento IAM todavía no está completo: usar recursos con
identidades distintas y restringir el acceso interno mediante red y autenticación
del equipo. Esta separación de código no implementa login ni crea recursos OCI.
El programador diario no se ejecuta dentro del frontend de Marketing.

La imagen tiene dos etapas y ejecuta como `appuser` (UID/GID 1000).
Solo copia los módulos necesarios de `src/`, `configuracion/`, `.streamlit/`
y el generador diario. El entorno de dependencias y el código
no son escribibles por el usuario de ejecución. El chequeo de salud usa Python.

Compose conserva las salidas en el volumen `communitylab-salida`, no en la
carpeta local `./salida` que usaba la propuesta inicial. Esto evita problemas
de permisos al ejecutar sin root. No se migran ni borran archivos existentes.
No usar `docker compose down -v` si se quieren conservar las salidas.
La configuración queda dentro de la imagen: reconstruir tras modificarla.

### Integración del ingestor (PR #56)

El backend acumulativo queda disponible como perfil optativo:
`docker compose --profile ingesta up --build -d communitylab-ingestor`.
No publica el puerto 8000 en el host y expone `/health` y `/sincronizar`
en la red puente de Compose. Marketing arranca independientemente de él:
no tiene `depends_on`, variables de escritura ni `INGESTOR_URL`.
La vista interna conserva su perfil y su puerto local; todavía no llama
al endpoint de carga. No se añade carga de Oracle a Marketing.

El lector usa `DB_READ_*` y consulta las tablas de
`rw_ingest_communitylab`, que requiere los permisos SELECT acordados por Cloud.
Materializa los CLOB antes de cerrar la conexión y no incluye API de escritura.
El frontend excluye el servicio de ingesta de todas sus capas de imagen y
conserva el script de generación diaria, sin ejecutarlo automáticamente.

La ingesta retiene lotes anteriores, rechaza conflictos de ID y usa recibos
para no duplicar spam en reintentos. Antes de una carga autorizada, revisar
el SQL de recibos documentado en `ingesta_lotes_retenidos_ce.md`.
Este merge no ejecuta SQL, no cambia IAM y no confirma cargas reales.

Este Compose es una base sencilla de pruebas, NO una certificación de
aislamiento en producción. El endpoint no autentica al llamador y una red
puente no distingue identidades de Instance Principals. No conectar la UI
pública ni exponer el endpoint. Para producción, Cloud debe acordar recursos
con identidades separadas y control de acceso entre procesos; dos contenedores
en una VM no bastan para afirmar ese aislamiento.

`.dockerignore` excluye `.env*`, llaves `.pem`/`.key`, `.oci/`, `.ssh/` y salidas,
incluso cuando las credenciales están en subcarpetas. No reemplaza una revisión
de secretos: no colocar credenciales en el código ni en archivos de configuración.

### Manifiestos separados para dos VM

Se incorporan `docker-compose.frontend.yml` y `docker-compose.backend.yml`
como alternativas independientes. El `docker-compose.yml` local se conserva
sin cambios. No combinar estos manifiestos con varios `-f` ni iniciar el
Compose local en esas VM: los servicios tienen los mismos nombres y no son
overrides para un despliegue conjunto.

Usar [.env.example](../.env.example) como referencia de nombres, no copiar
su contenido completo a ambas VM. En Marketing conservar claves IA, modelos,
`DB_READ_*` y bucket; en el backend, únicamente su configuración de escritura
y bind privado. Los valores vacíos de DSN y secreto deben completarlos con
los valores autorizados de Cloud en archivos no versionados. Los nombres de
usuario del ejemplo coinciden con los valores predeterminados de Compose;
si Cloud provisionó otros, configurar los nombres reales explícitamente.
No copiar claves entre equipos ni publicar el contenido del entorno.

El backend recibe la contraseña mediante el OCID de su secreto en Vault:
`DB_PASSWORD_SECRET_OCID` no admite un OCID de clave ni la contraseña en texto.
El DSN debe ser el servicio TLS correcto de la base escritora, no solo una IP.
La ACL, la ruta por Service Gateway y los permisos IAM son requisitos externos:
ninguna variable de este ejemplo los crea o corrige.

### Carga desde la pantalla interna

En el backend configurar `INGESTOR_DESTINO` (nombre reconocible) e
`INGESTOR_ENTORNO` (`demostracion` o `produccion`). La etiqueta no aísla datos:
Cloud debe apuntar el DSN/usuario a la base o esquema realmente acordado.
En el archivo privado `.env.interno` configurar `INGESTOR_URL` como URL base
privada, sin `/sincronizar`; con Compose local:
`http://communitylab-ingestor:8000`. No configurar esta URL en Marketing.
Permitir el acceso únicamente desde el servidor interno autorizado; estos
endpoints no incorporan autenticación HTTP y no deben exponerse públicamente.

En Datos, comprobar Oracle antes de ejecutar IA. El resultado queda disponible
para descargar como Conjunto Consultable; también se conserva por huella en
`salida/ingesta` (volumen persistente del servicio interno). Descargar una copia
antes de cerrar la sesión permite retomarla desde otro equipo.
También se puede subir un Conjunto Consultable previamente generado para
no repetir IA. Comprobar el destino, declarar si hay datos sintéticos y confirmar
el lote antes de cargar. Los sintéticos se bloquean si el destino no es de
demostración. `/destino` consulta Oracle y las tres tablas, mientras que
`/health` solo comprueba el proceso HTTP; no certifica permisos de escritura.
La escritura real sigue siendo transaccional en `/sincronizar`.
El cliente fija la identidad comprobada del destino y pide nueva confirmación
si cambia. `/verificar` compara cada ID y sus siete campos con Oracle.
No verifica por sí mismo el contador histórico de spam ni los permisos IAM.

Si hay timeout, el commit puede haberse realizado: usar “Verificar lote sin
escribir” o reintentar exactamente el mismo documento. Los recibos evitan sumar
spam otra vez. Nunca reprocesar IA para resolver un fallo de transporte.
Un ID con contenido distinto requiere conciliación: no renombrar IDs durante
el reintento ni sobrescribirlos. Esta preparación no despliega servicios ni
carga automáticamente los 1.200 casos sintéticos.

En la VM de Marketing:

```powershell
docker compose -f docker-compose.frontend.yml config --quiet
docker compose -f docker-compose.frontend.yml up --build -d
```

Conservar sus claves de generación, `DB_READ_*` y bucket de lectura. Este
manifiesto mantiene los ajustes actuales del agente, no recibe credenciales
de escritura ni `INGESTOR_URL` y no requiere al ingestor para iniciar.
Agregar una URL no conecta ninguna pantalla: actualmente la UI interna tampoco
invoca `/sincronizar`.

El valor predeterminado de `COMMUNITYLAB_MODELO_NVIDIA_ESTANDAR` en ambos
Compose coincide con el de Python: `nvidia/nemotron-3.5-super-vl-120b-a12b`.
Ese tier se usa para análisis individual y por lote, no para cambiar los
modelos de redacción. Un valor explícito del entorno prevalece: revisar
`.env` y, para la aplicación interna, su propio `.env.interno`; cambiar el
predeterminado del Compose no reemplaza una configuración existente.
El ajuste se validó con la muestra acotada documentada en
[agente_conversacional.md](agente_conversacional.md), no con los 600.
Puede tener mayor latencia y consumo de cuota. No implica que se haya
reconstruido o actualizado ningún contenedor remoto.

En la VM de ingesta, definir `INGESTOR_BIND_IP` con su IP privada real,
`DB_DSN` y `DB_PASSWORD_SECRET_OCID` en su entorno propio:

```powershell
docker compose -f docker-compose.backend.yml config --quiet
docker compose -f docker-compose.backend.yml up --build -d
```

El backend publica `${INGESTOR_BIND_IP}:8000:8000`, no `8000:8000`. Compose
rechaza una IP vacía, pero **no valida que sea privada**: Cloud debe verificar
que corresponde a una interfaz privada de la VM, no a `0.0.0.0` ni una IP
pública. La comprobación de salud de la imagen permanece local al contenedor.
No imprimir `config` completo en logs compartidos: puede mostrar valores
interpolados del entorno.

Estos archivos no crean VM, reglas de red, IAM ni autenticación del endpoint.
Antes de iniciar el backend, Cloud debe restringir TCP 8000 al ejecutor interno
autorizado mediante NSG/listas de seguridad y firewall, **excluir Marketing**
y acordar autenticación del llamador. No abrirlo a toda la VCN por ser privada.
Las VM deben usar identidades distintas: Marketing solo lee su secreto y
catálogo, sin acceso al secreto escritor. Verificar desde Marketing la
denegación de carga y de acceso a ese secreto. Dos VM por sí solas no demuestran
que esas políticas estén bien aplicadas.

## Validación y límites

Validación local realizada en AMD64:

- Suite de la rama: 216 pruebas y 132 subpruebas aprobadas.
- Imagen construida con Python 3.12; usuario efectivo UID 1000.
- Escritura en volumen anónimo de `/app/salida` correcta; código no escribible.
- Pantalla inicial verificada con Streamlit AppTest sin claves ni red.
- Servidor Streamlit iniciado dentro del contenedor: health HTTP 200.
- Imagen en formato Docker: `podman healthcheck run` exitoso, estado `healthy`.
- No se encontraron archivos `.pem`, `.key`, `.env` o directorios `.oci` en `/app`.

Con Podman, construir así para conservar el HEALTHCHECK (el formato de imagen
OCI predeterminado de Podman no lo conserva):

```sh
podman build --format docker --ignorefile .dockerignore -f Dockerfile.frontend -t localhost/communitylab:ce-semana4 .
```

Verificar usuario, escritura en `/app/salida`, inicio de Streamlit y healthcheck.
No confundir salud HTTP con funcionamiento completo del pipeline.
En una VM Ampere se debe construir/probar la imagen ARM64; una prueba local
AMD64 no demuestra compatibilidad operativa ARM64.

Para Instance Principals hacen falta la VM, su grupo dinámico, la política IAM
y acceso al servicio de metadatos desde el contenedor. No montar llaves personales
para sustituir esa validación. Este cambio no crea recursos ni prueba OCI real.

Pendientes separados: integración de aprobación/guardado con SS, configuración
final de proveedores por DS y prueba de extremo a extremo en la VM compartida.
# Acceso local de solo lectura

La VM conserva `OCI_AUTH_MODE=instance_principal`. Desde una máquina local
se puede elegir explícitamente `OCI_AUTH_MODE=api_key`; no hay fallback
automático entre identidades.

Configura fuera del repositorio un perfil OCI con una clave propia registrada
en IAM. No copies claves de la VM ni compartas claves privadas en el chat.
El archivo de configuración del SDK debe incluir `user`, `fingerprint`,
`tenancy`, `region` y `key_file` bajo el perfil elegido.

En el entorno local:

```dotenv
OCI_AUTH_MODE=api_key
OCI_CONFIG_FILE=C:\Users\TU_USUARIO\.oci\config
OCI_PROFILE=COMMUNITYLAB_READ
OCI_BUCKET_NAME=bkt-communitylab-marketing
DB_READ_USER=USUARIO_SELECT
DB_READ_DSN=CADENA_TLS_DE_CLOUD
DB_READ_PASSWORD_SECRET_OCID=OCID_SECRETO_LECTURA
```

`OCI_CONFIG_FILE` prevalece sobre `OCI_CONFIG_DIR` (por defecto `~/.oci`).
El perfil no concede permisos por su nombre: Cloud debe asignar únicamente
lectura de objetos y el acceso necesario al secreto del usuario SELECT.
El usuario Oracle debe tener SELECT sobre las tablas del conjunto, sin DML.
Nunca configurar credenciales de escritura para Marketing.

Verifica desde la raíz:

```powershell
.\.venv\Scripts\python.exe -m scripts.comprobar_cloud_lectura
```

El comando solo lee la instantánea de Oracle y una muestra de hasta cinco
objetos bajo `plantillas/`; no muestra los textos, claves o secretos ni sube
objetos. Devuelve código 1 si falla cualquiera de los dos accesos. Una lista
vacía significa que la lectura funcionó, no que exista un catálogo diario.
No prueba permisos de escritura ni certifica que IAM los haya denegado.

## Activar Analisis y Plantillas en Marketing

Analisis publico lee la misma captura de Oracle que el agente: muestra conteos
de mensajes, canales, temas, sentimientos y tipos sin invocar IA. No necesita
un lote procesado en la sesion interna. No muestra metricas de activos o
elegibilidad, porque el Conjunto Consultable no contiene esos datos.
La captura se comparte en la sesion y dura una hora; "Actualizar datos" fuerza
una nueva lectura. Una captura anterior se identifica como desactualizada si
falla la lectura. Un error sin captura se muestra como error, no como cero.
La pantalla interna conserva sus metricas del pipeline.

La vista publica permite filtrar por tema, sentimiento, canal y tipo, y buscar
texto/ID. Los filtros se combinan por interseccion. Resumen muestra porcentajes
sobre el subconjunto seleccionado con denominador visible; Cruces compara dos
dimensiones; Fuentes pagina mensajes, permite leer textos completos y descargar
el subconjunto o el cruce en CSV. No interpreta causalidad ni inventa series
temporales cuando faltan fechas. Desde Agente hay un acceso directo a esta vista:
no modifica ni envia el chat o sus adjuntos. Los calculos no llaman modelos;
el chat en lenguaje natural mantiene sus llamadas y posible consumo de cuota.
No se afirma que Oracle o la infraestructura sean gratuitos, ni que estas
clasificaciones sean una evaluacion de calidad del modelo sin etiquetas humanas.

Plantillas publico lee `plantillas/catalogo_actual.json` del bucket. Cargar
mensajes en Oracle NO genera este objeto. El generador ya existe y no debe
ejecutarse dentro del servidor publico en respuesta a una visita.

Procedimiento para Cloud (desde la raiz del checkout aprobado):

1. Desplegar la imagen construida con el commit aprobado, registrar el SHA y
   conservar la imagen anterior para rollback. No copiar archivos sueltos.
2. Verificar la lectura de Oracle y bucket desde el contenedor de Marketing:
   `python -m scripts.comprobar_cloud_lectura`. Esto no crea el catalogo.
3. Acordar una identidad/ejecutor separado con lectura de Oracle, acceso al
   secreto lector y lectura/escritura del objeto del catalogo. Marketing debe
   conservar solo lectura de ese objeto y sus permisos de guardado de activos.
   No reutilizar el secreto escritor de ingesta ni abrirle el puerto 8000.
4. Confirmar con el propietario el uso y cuota de las claves NVIDIA/Gemini.
   Configurar las claves y `DB_READ_*`, `OCI_BUCKET_NAME` e identidad OCI
   exclusivamente en el entorno privado autorizado del ejecutor.
5. Despues de las 13:00 UTC, ejecutar una primera pasada:
   `python -m scripts.generar_plantillas_diarias`.
   Este comando consume IA y escribe el catalogo; requiere autorizacion.
   Salida 0: ejecucion sin fallos (antes de las 13:00 UTC no genera).
   Salida 1: error de actualizacion/persistencia; salida 2: catalogo con
   plantillas fallidas. Revisar logs privados, sin publicar claves o textos.
6. Leer el catalogo desde la identidad de Marketing y comprobar entradas,
   fechas y fallos. Un HTTP 200 de Streamlit o listar el bucket no prueba que
   exista el catalogo. En la web pulsar "Actualizar catalogo": la cache dura
   45 segundos. La lectura no genera contenido ni consume cuota.
7. Programar el mismo comando a las 13:00 UTC, sin ejecuciones
   concurrentes. Reintentar tras corregir errores: se conservan los exitos del
   dia y las versiones anteriores de las plantillas fallidas. La renovacion
   diaria se programa externamente; no hay un scheduler integrado en la web.
   Fechas de catalogo, agrupacion diaria y avisos de antiguedad usan UTC.

Aceptacion: abrir Analisis en una sesion nueva sin importar archivos, comparar
los conteos contra Oracle y revisar el aviso de fuente/fecha. Abrir Agente y
contrastar el conteo de la misma captura. Abrir Plantillas, revisar fuentes,
fecha y estados de cada entrada sin publicar en redes. Registrar SHA, hora y
resultados; no declarar exito si falla Oracle o faltan entradas del catalogo.
También se necesita conectividad de red hacia Oracle y OCI; un perfil válido
no sustituye VPN, reglas de firewall o una ruta hacia un endpoint privado.
