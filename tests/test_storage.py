"""
Módulo para validar la conexión y subida de archivos a OCI Object Storage.

Consulta los metadatos del bucket y carga los objetos, manejando la
configuración a través de variables de entorno y emitiendo errores estándar.
"""

import os
import sys

import oci
from oci.object_storage import ObjectStorageClient


def get_oci_client(profile_name: str) -> tuple[ObjectStorageClient, str]:
    """
    Carga y valida la configuración de OCI desde ~/.oci/config
    Devuelve el cliente y su namespace.
    """
    config = oci.config.from_file(profile_name=profile_name)
    oci.config.validate_config(config)

    client = ObjectStorageClient(config)
    namespace = client.get_namespace().data

    return client, namespace


def display_bucket_info(
    client: ObjectStorageClient,
    namespace: str,
    bucket_name: str,
) -> None:
    """
    Consulta e imprime los metadatos del bucket para confirmar la conexión.
    """
    bucket = client.get_bucket(
        namespace_name=namespace,
        bucket_name=bucket_name,
    ).data

    print("Conexión exitosa con OCI Object Storage.")
    print(f"Bucket: {bucket.name} (Nivel: {bucket.storage_tier})")
    print(f"Acceso público: {bucket.public_access_type}")


def upload_object(
    client: ObjectStorageClient,
    namespace: str,
    bucket_name: str,
    object_name: str,
    content: str,
    content_type: str = "application/json",
) -> None:
    """
    Codifica en UTF-8 y sube el contenido de prueba al bucket especificado.
    """
    print(f"\nIniciando subida de '{object_name}' al bucket '{bucket_name}'...")
    client.put_object(
        namespace_name=namespace,
        bucket_name=bucket_name,
        object_name=object_name,
        put_object_body=content.encode("utf-8"),
        content_type=content_type,
    )
    print("Subida completada con éxito.")


def main() -> int:
    """
    Orquesta la configuración, la verificación del bucket y la subida del archivo.
    Retorna 0 en caso de éxito, o 1 en caso de captura de error.
    """
    bucket_name = os.getenv("OCI_BUCKET_NAME", "communitylab-activos-marketing")
    profile_name = os.getenv("OCI_PROFILE", "DEFAULT")
    
    target_object = "activos/2026-semana-00/prueba-inicial.json"
    test_content = '{"status": "exito", "mensaje": "Conexion OCI establecida."}'

    try:
        client, namespace = get_oci_client(profile_name)
        
        display_bucket_info(client, namespace, bucket_name)
        upload_object(client, namespace, bucket_name, target_object, test_content)

        return 0

    except oci.exceptions.ServiceError as error:
        print(
            f"Error de OCI ({error.status}): {error.message}",
            file=sys.stderr,
        )
        return 1
    except (oci.exceptions.InvalidConfig, OSError, ValueError) as error:
        print(
            f"Error de configuración o sistema: {error}",
            file=sys.stderr,
        )
        return 1
    except Exception as general_error:
        print(
            f"Error inesperado durante la ejecución: {general_error}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())