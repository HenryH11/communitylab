"""
Módulo para probar la conexión y subida de archivos a OCI Object Storage.
"""

import oci


def upload_test_file(bucket_name: str, file_content: str, object_name: str) -> None:
    """
    Sube un archivo de texto de prueba a un bucket de OCI Object Storage
    utilizando la configuración predeterminada del sistema.
    """
    try:
        # La configuración se carga automáticamente desde ~/.oci/config
        config = oci.config.from_file()
        storage_client = oci.object_storage.ObjectStorageClient(config)

        # El namespace es requerido para interactuar con Object Storage en OCI
        namespace = storage_client.get_namespace().data

        print(f"Iniciando subida de '{object_name}' al bucket '{bucket_name}'...")
        
        # Ejecución de la subida del objeto
        storage_client.put_object(
            namespace_name=namespace,
            bucket_name=bucket_name,
            object_name=object_name,
            put_object_body=file_content.encode('utf-8')
        )
        print("Subida completada con éxito.")

    except oci.exceptions.ConfigFileNotFound:
        print("Error: No se encontró el archivo de configuración de OCI.")
    except oci.exceptions.ServiceError as error:
        print(f"Error en el servicio OCI: {error.message}")
    except Exception as general_error:
        print(f"Ha ocurrido un error inesperado: {general_error}")


if __name__ == "__main__":
    # Variables de configuración del entorno de prueba
    TARGET_BUCKET = "communitylab-activos-marketing"
    TARGET_OBJECT = "activos/2026-semana-00/prueba-inicial.json"
    TEST_CONTENT = '{"status": "exito", "mensaje": "Conexion OCI establecida."}'

    upload_test_file(TARGET_BUCKET, TEST_CONTENT, TARGET_OBJECT)