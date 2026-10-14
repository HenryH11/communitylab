# Docker para Cloud — Semana 4

Base: trabajo de Arthur en `feature/DS-Semana3-Nvidia` (PR #28).
Este ajuste no cambia modelos, contratos JSON ni el guardado de activos.

## Ejecución

Desde la raíz: `docker compose up --build -d`.
La app escucha en el puerto 8501. Las claves se proporcionan en `.env` local
(nunca en la imagen o Git). No publicar la app en Internet sin acordar los
controles de acceso; publicar un puerto no configura las reglas de OCI.

La imagen tiene dos etapas y ejecuta como `appuser` (UID/GID 1000).
Solo copia `src/` y `configuracion/`. El entorno de dependencias y el código
no son escribibles por el usuario de ejecución. El chequeo de salud usa Python.

Compose conserva las salidas en el volumen `communitylab-salida`, no en la
carpeta local `./salida` que usaba la propuesta inicial. Esto evita problemas
de permisos al ejecutar sin root. No se migran ni borran archivos existentes.
No usar `docker compose down -v` si se quieren conservar las salidas.
La configuración queda dentro de la imagen: reconstruir tras modificarla.

`.dockerignore` excluye `.env*`, llaves `.pem`/`.key`, `.oci/`, `.ssh/` y salidas,
incluso cuando las credenciales están en subcarpetas. No reemplaza una revisión
de secretos: no colocar credenciales en el código ni en archivos de configuración.

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
podman build --format docker --ignorefile .dockerignore -t localhost/communitylab:ce-semana4 .
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
