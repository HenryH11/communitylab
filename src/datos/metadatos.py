"""Marcas tecnicas de ausencia; nunca son evidencia sobre la comunidad."""

PREFIJO_AUSENTE = "__communitylab_ausente__:"


def valor_publico(valor: object) -> str:
    if not isinstance(valor, str) or valor.startswith(PREFIJO_AUSENTE):
        return ""
    return valor
