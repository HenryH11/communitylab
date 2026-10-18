import hashlib

from src.agentes.huellas import calcular_sha256_lf


def test_sha256_lf_es_igual_en_windows_y_linux(tmp_path):
    contenido_lf = b'{\n    "casos": []\n}\n'
    contenido_crlf = contenido_lf.replace(b"\n", b"\r\n")

    archivo_lf = tmp_path / "linux.json"
    archivo_crlf = tmp_path / "windows.json"

    archivo_lf.write_bytes(contenido_lf)
    archivo_crlf.write_bytes(contenido_crlf)

    esperado = hashlib.sha256(contenido_lf).hexdigest()

    assert calcular_sha256_lf(archivo_lf) == esperado
    assert calcular_sha256_lf(archivo_crlf) == esperado

    # Los hashes originales deben permanecer diferentes.
    assert (
        hashlib.sha256(contenido_lf).hexdigest()
        != hashlib.sha256(contenido_crlf).hexdigest()
    )


def test_auditoria_registra_sha_original_y_lf(tmp_path):
    from scripts.generar_auditoria_semana4 import construir_huellas_dataset

    archivo = tmp_path / "dataset.json"
    contenido_lf = b'{\n    "interacciones": []\n}\n'
    contenido_crlf = contenido_lf.replace(b"\n", b"\r\n")

    archivo.write_bytes(contenido_crlf)

    huellas = construir_huellas_dataset(archivo)

    assert huellas["dataset_sha256"] == hashlib.sha256(
        contenido_crlf
    ).hexdigest()

    assert huellas["dataset_sha256_lf"] == hashlib.sha256(
        contenido_lf
    ).hexdigest()