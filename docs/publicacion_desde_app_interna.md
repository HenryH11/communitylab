# Publicacion revisada desde la app interna

Este cambio conecta Datos con el ingestor existente. No cambia DS, DA,
SQL, el protocolo de recibos, los permisos ni la aplicacion de Marketing.

## Flujo

1. El equipo abre `src/app/app_interna.py` por un acceso restringido.
2. Importa el JSON y ejecuta el procesamiento habitual.
3. La app conserva una copia del origen ligada al resultado exitoso. Una
   seleccion posterior de otro archivo no cambia el origen del ultimo
   resultado procesado ni sus fechas.
4. En Datos revisa el Conjunto Consultable y su contador de spam, y marca
   la confirmacion. Solo entonces pulsa **Publicar lote en Oracle**.
5. La UI utiliza `preparar_entrega_resultados` (DS) y
   `construir_conjunto_consultable` (DA). No vuelve a llamar a la IA al
   publicar. Un lote pendiente, con errores o incompleto no se envia.
6. La UI hace un POST a `/sincronizar` y comprueba el recibo completo.
   La conservacion de lotes y la idempotencia siguen siendo responsabilidad
   del ingestor ya existente; no se duplican esas reglas en la pantalla.

Un timeout no significa que Oracle no haya confirmado: el servidor podria
haber terminado despues. La pantalla permite reenviar exactamente el mismo
lote sin reprocesarlo con IA; no hace reintentos automaticos. El ingestor
usa su recibo para no duplicar filas ni spam. Si llega un recibo valido,
la sesion conserva la confirmacion y no repite la publicacion al navegar.

## Configuracion exclusivamente interna

Definir `INGESTOR_URL` en el proceso interno con una IP privada o localhost
y ruta exacta `/sincronizar`. No incluir credenciales, query ni fragmento.
La app rechaza destinos publicos, DNS arbitrario, metadatos link-local y
redirecciones; no usa los proxies HTTP heredados para este envio.

La UI NO obtiene `DB_PASSWORD_SECRET_OCID`, `DB_USER`, `DB_DSN` ni el secreto
escritor. Esas credenciales siguen exclusivamente en el ingestor. La URL no
es autenticacion: el endpoint actual requiere proteccion real de red/acceso.

Ejemplo de arranque del proceso interno, solo en loopback:

```sh
streamlit run src/app/app_interna.py --server.address 127.0.0.1 --server.port 8502
```

El operador debe establecer antes `INGESTOR_URL` en ese proceso. Puede usar
un tunel SSH/Bastion autorizado hacia el ingestor y apuntar a localhost.
Las claves de IA del procesamiento se configuran privadamente como en el
flujo existente. No subirlas, copiar secretos escritores ni publicarlas.

## Despliegue a coordinar con Cloud

Este parche no arranca procesos ni modifica ninguna VM. Para ponerlo en
marcha hace falta:

- Imagen/codigo de esta revision y un proceso interno separado, accesible
  solo al equipo mediante el acceso privado acordado.
- Un camino autorizado desde ESE proceso al ingestor. No publicar la app
  interna desde el dominio de Marketing ni habilitar el 8000 a la VM publica.
- Mantener `app.py` como entrada de Marketing: `modo_interno=False` es fijo.
- Configurar la URL solo en el proceso interno; no se agrega al Compose
  publico. Tener la URL en Marketing no habilita la funcion ni concede red.

No montar app interna y Marketing con una identidad compartida para resolver
el acceso. Dos contenedores por si solos no separan Instance Principals ni
permisos de red de la VM. Si el entorno interno aun no esta disponible,
acordarlo antes de desplegar; este cambio no lo da por configurado.

## Verificacion

```sh
python -m pytest -q tests/test_publicacion_oracle.py tests/test_publicacion_oracle_ui.py
```

46 casos aprobados: conversion DS/DA, fecha original, spam,
rechazo de lotes incompletos, confirmacion humana, recibos, errores,
timeouts/reintentos manuales, URLs privadas y ausencia del control en
Marketing. Incluye pantalla -> HTTP real sobre loopback -> IngestHandler,
con procesamiento y DB transaccional simulados; no usa OCI ni IA reales.

La prueba A/B/reintento de Cloud contra Oracle real es evidencia separada
del escritor. Estos tests no se presentan como un E2E ya desplegado en OCI.
El caso extremo de texto agregado durante pruebas previas no forma parte
de este cambio ni del criterio de aceptacion de esta integracion.

Comparacion completa en Linux, sin red ni credenciales, sobre base a817032
(merge #59):

| Version | Pruebas aprobadas | Fallos | Subpruebas aprobadas |
| --- | --- | --- | --- |
| develop3 intacto | 1203 | 2 | 221 |
| Con esta integracion | 1249 | 2 | 221 |

Los dos fallos son los mismos en ambas versiones y no se modificaron aqui:
`tests/test_autenticacion_oci.py::test_directorio_y_perfil_predeterminados`
espera una ruta fija de Windows en Linux; `tests/test_saneamiento_json.py`
detecta indentacion 2 en `tests/datos_validacion_semantica_nueva.json`.
No se afirma que la suite completa este en verde. El codigo se monto en
solo lectura con una salida temporal escribible para la prueba CLI existente.
