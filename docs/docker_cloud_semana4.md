# Docker para Cloud — Semana 4

Base: trabajo de Arthur en `feature/DS-Semana3-Nvidia` (PR #28).
Este ajuste no cambia modelos, contratos JSON ni el guardado de activos.

## Ejecución

Desde la raíz: `docker compose up --build -d`.
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
