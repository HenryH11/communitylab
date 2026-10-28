"""Presupuesto operativo de contexto, configurable solo en el servidor."""

from collections.abc import Callable
from dataclasses import dataclass
import json
import os

from dotenv import load_dotenv

from src.agentes.errores_ia import ErrorConfiguracionProveedor


@dataclass(frozen=True)
class PresupuestoContexto:
    total: int
    salida: int

    @property
    def entrada(self) -> int:
        return self.total - self.salida


def obtener_presupuesto_contexto() -> PresupuestoContexto:
    load_dotenv()
    valores = []
    for variable, defecto in (
        ("COMMUNITYLAB_CONTEXTO_TOKENS", 32768),
        ("COMMUNITYLAB_SALIDA_TOKENS", 4096),
    ):
        try:
            valor = int(os.getenv(variable, str(defecto)))
        except ValueError as error:
            raise ErrorConfiguracionProveedor(f"{variable} debe ser un entero positivo.") from error
        if valor <= 0:
            raise ErrorConfiguracionProveedor(f"{variable} debe ser un entero positivo.")
        valores.append(valor)
    presupuesto = PresupuestoContexto(*valores)
    if presupuesto.salida >= presupuesto.total:
        raise ErrorConfiguracionProveedor(
            "COMMUNITYLAB_SALIDA_TOKENS debe ser menor que COMMUNITYLAB_CONTEXTO_TOKENS."
        )
    return presupuesto


def estimar_tokens(valor: object) -> int:
    """Cuenta bytes UTF-8 como estimación conservadora, no tokens del proveedor."""
    texto = valor if isinstance(valor, str) else json.dumps(valor, ensure_ascii=False, default=str)
    return len(texto.encode("utf-8"))


def dividir_evidencia(
    evidencia: list[dict],
    cabe: Callable[[list[dict]], bool],
) -> list[list[dict]]:
    """Empaqueta por presupuesto y fragmenta textos grandes sin descartar caracteres."""
    if not cabe([]):
        raise ValueError(
            "Las instrucciones, el historial y los agregados exceden el presupuesto "
            "de contexto del servidor. No se procesó una muestra parcial."
        )
    lotes: list[list[dict]] = []
    actual: list[dict] = []
    for mensaje in evidencia:
        pendientes = [mensaje]
        while pendientes:
            fragmento = pendientes.pop()
            if cabe([*actual, fragmento]):
                actual.append(fragmento)
            elif actual:
                lotes.append(actual)
                actual = []
                pendientes.append(fragmento)
            else:
                texto = fragmento["texto"]
                if len(texto) < 2:
                    raise ValueError(
                        "Un registro no cabe en el presupuesto de contexto ni fragmentando "
                        "su texto. No se omitieron registros para producir una respuesta."
                    )
                mitad = len(texto) // 2
                pendientes.extend([
                    {**fragmento, "texto": texto[mitad:]},
                    {**fragmento, "texto": texto[:mitad]},
                ])
    if actual:
        lotes.append(actual)
    return lotes
