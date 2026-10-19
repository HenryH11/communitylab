"""Pruebas del conector OCI sin tocar el bucket real."""

import json
import unittest
from unittest.mock import Mock, patch

from src.config.oci_client import nombre_objeto_activo, subir_json


class PruebasPersistenciaOCI(unittest.TestCase):
    def test_subida_conserva_unicode_y_devuelve_ubicacion(self):
        cliente = Mock()
        cliente.put_object.return_value.headers = {"etag": "abc123"}
        documento = {"id": "int-022", "texto": "¡Qué útil! 👩‍💻"}

        resultado = subir_json(
            documento,
            nombre_objeto_activo("int-022", "linkedin", "2026-semana-02"),
            cliente=cliente,
            namespace="namespace-prueba",
            bucket="bucket-prueba",
        )

        parametros = cliente.put_object.call_args.kwargs
        self.assertEqual(json.loads(parametros["put_object_body"]), documento)
        self.assertIn("¡Qué útil! 👩‍💻".encode(), parametros["put_object_body"])
        self.assertEqual(parametros["content_type"], "application/json; charset=utf-8")
        self.assertEqual(parametros["object_name"], "assets/2026-semana-02/linkedin/int-022.json")
        self.assertEqual(resultado["etag"], "abc123")
        self.assertEqual(resultado["bucket"], "bucket-prueba")

    def test_rechaza_datos_invalidos_antes_de_subir(self):
        cliente = Mock()
        for documento in ([], {"valor": float("nan")}, {"valor": object()}):
            with self.subTest(documento=documento), self.assertRaises((TypeError, ValueError)):
                subir_json(documento, "assets/prueba.json", cliente=cliente, namespace="prueba")
        cliente.put_object.assert_not_called()

    def test_ruta_no_admite_separadores_en_id(self):
        with self.assertRaises(ValueError):
            nombre_objeto_activo("../otro", "linkedin", "2026-semana-02")

    def test_error_de_subida_se_propaga_sin_confirmacion_falsa(self):
        cliente = Mock()
        cliente.put_object.side_effect = RuntimeError("subida fallida")
        with self.assertRaisesRegex(RuntimeError, "subida fallida"):
            subir_json({"id": "int-022"}, "assets/int-022.json", cliente=cliente, namespace="prueba")

    @patch("src.config.oci_client.crear_cliente")
    def test_usa_perfil_y_bucket_del_entorno(self, crear_cliente):
        cliente = Mock()
        cliente.put_object.return_value.headers = {}
        crear_cliente.return_value = cliente, "namespace-real"
        with patch.dict("os.environ", {"OCI_BUCKET_NAME": "communitylab-activos-marketing"}):
            resultado = subir_json({"id": "int-022"}, "processed/int-022.json", perfil="EQUIPO")
        crear_cliente.assert_called_once_with("EQUIPO")
        self.assertEqual(resultado["bucket"], "communitylab-activos-marketing")
        self.assertEqual(cliente.put_object.call_args.kwargs["namespace_name"], "namespace-real")


if __name__ == "__main__":
    unittest.main()
