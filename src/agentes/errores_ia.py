"""Errores específicos de la capa de proveedores de IA."""


class ErrorConfiguracionProveedor(Exception):
    """Configuración requerida de un proveedor ausente o inválida."""


class ErrorSalidaProveedor(Exception):
    """El proveedor respondió, pero su salida no cumple el contrato esperado."""

class ErrorFallbackProveedores(Exception):
    """Fallaron tanto el proveedor primario como el proveedor de respaldo."""

    def __init__(self, traza: dict):
        super().__init__(
            "Fallaron el proveedor primario y el proveedor de respaldo."
        )
        self.traza = traza