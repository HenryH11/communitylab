# Diagrama conceptual de persistencia con OCI

Este diagrama representa cómo el backend recibirá el JSON preparado por Data
Analysis y lo almacenará en OCI Object Storage mediante el SDK oficial `oci`.

## Flujo

```mermaid
flowchart LR
    A["JSON de Data Analysis<br/>id, autor, canal, tipo,<br/>texto, fecha e idioma"]
    B["Backend de CommunityLab"]
    C["Validar y serializar<br/>JSON UTF-8"]
    D["Tarea de almacenamiento<br/>asíncrono"]
    E["SDK oficial de OCI<br/>ObjectStorageClient"]
    F["put_object"]
    G["Bucket privado<br/>communitylab-activos-marketing"]
    H["Confirmación de almacenamiento"]
    I["Registro controlado del error"]

    A --> B --> C --> D --> E --> F
    F -->|Éxito| G --> H
    F -->|Error| I
```

## Mapeo conceptual

| Origen | Persistencia en OCI |
| --- | --- |
| JSON validado por Data Analysis | Cuerpo del objeto almacenado en formato JSON |
| `id` de la interacción | Identificador para conservar la trazabilidad |
| `origen_comunidad` y `periodo_referencia` | Datos para organizar la ruta del objeto |
| Configuración local o variables de entorno | Perfil, bucket y conexión del SDK |

Ejemplo de ruta conceptual:

```text
processed/2026/semana-02/int-022.json
```

Las credenciales y llaves de OCI permanecen fuera del repositorio. La lógica
Python del conector se desarrollará en `src/config/` durante la Semana 2.
