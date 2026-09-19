import os
import sys

import oci


BUCKET_NAME = os.getenv(
    "OCI_BUCKET_NAME",
    "communitylab-activos-marketing",
)
PROFILE_NAME = os.getenv("OCI_PROFILE", "DEFAULT")


def main() -> int:
    try:
        config = oci.config.from_file(profile_name=PROFILE_NAME)
        oci.config.validate_config(config)

        client = oci.object_storage.ObjectStorageClient(config)
        namespace = client.get_namespace().data

        bucket = client.get_bucket(
            namespace_name=namespace,
            bucket_name=BUCKET_NAME,
        ).data

        print("Conexión exitosa con OCI Object Storage.")
        print(f"Bucket: {bucket.name}")
        print(f"Región: {config['region']}")
        print(f"Nivel de almacenamiento: {bucket.storage_tier}")
        print(f"Acceso público: {bucket.public_access_type}")
        print(f"Fecha de creación: {bucket.time_created}")
        return 0

    except oci.exceptions.ServiceError as error:
        print(
            f"Error de OCI ({error.status}): {error.message}",
            file=sys.stderr,
        )
        return 1
    except (oci.exceptions.InvalidConfig, OSError, ValueError) as error:
        print(f"Error de configuración: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
