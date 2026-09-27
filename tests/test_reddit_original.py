"""Incluye las ocho comprobaciones originales de Gustavo en unittest discover."""

import unittest
import verificar_transformacion_reddit as originales


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(
        unittest.FunctionTestCase(getattr(originales, nombre))
        for nombre in sorted(dir(originales)) if nombre.startswith("test_")
    )
