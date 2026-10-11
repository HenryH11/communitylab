"""Agregaciones del resumen comunitario incluido en la entrega de Datos."""

from collections import Counter
from collections.abc import Sequence

from src.agentes.contrato_salida_ciencia_datos import (
    ActivoEntregado,
    ResumenComunidad,
    TemaPrincipalResumen,
)


def _ordenar_distribucion(contador: Counter) -> dict[str, int]:
    return {
        clave: cantidad
        for clave, cantidad in sorted(
            contador.items(),
            key=lambda item: (-item[1], item[0]),
        )
    }


def _obtener_sentimientos_predominantes(contador: Counter) -> list[str]:
    if not contador:
        return []

    maximo = max(contador.values())
    return sorted(
        sentimiento
        for sentimiento, cantidad in contador.items()
        if cantidad == maximo
    )


def _obtener_temas_principales(
    contador: Counter,
    limite: int = 3,
) -> list[TemaPrincipalResumen]:
    return [
        {"tema": tema, "cantidad": cantidad}
        for tema, cantidad in sorted(
            contador.items(),
            key=lambda item: (-item[1], item[0]),
        )[:limite]
    ]


def construir_resumen_comunidad(
    resultados: list[dict],
    activos: Sequence[ActivoEntregado],
    fallos: list[dict],
    total_pendientes: int,
) -> ResumenComunidad:
    """Construye los contadores y distribuciones del resumen de entrega."""
    sentimientos = Counter(
        resultado["sentimiento"]
        for resultado in resultados
        if isinstance(resultado.get("sentimiento"), str)
        and resultado["sentimiento"].strip()
    )
    temas = Counter(
        resultado["tema_principal"]
        for resultado in resultados
        if isinstance(resultado.get("tema_principal"), str)
        and resultado["tema_principal"].strip()
    )
    tipos_detectados = Counter(
        resultado["tipo_detectado"]
        for resultado in resultados
        if isinstance(resultado.get("tipo_detectado"), str)
        and resultado["tipo_detectado"].strip()
    )

    fallos_por_etapa = _ordenar_distribucion(
        Counter(fallo["etapa"] for fallo in fallos)
    )
    fallos_reintentables = [
        fallo for fallo in fallos if fallo.get("reintentable") is True
    ]
    sentimientos_predominantes = _obtener_sentimientos_predominantes(sentimientos)
    sentimiento_predominante = (
        sentimientos_predominantes[0]
        if len(sentimientos_predominantes) == 1
        else None
    )

    return {
        "total_interacciones_procesadas": len(resultados),
        "total_pendientes": total_pendientes,
        "total_elegibles_contenido": sum(
            resultado.get("elegible_contenido") is True
            for resultado in resultados
        ),
        "total_elegibles_faq": sum(
            resultado.get("elegible_faq") is True
            for resultado in resultados
        ),
        "total_con_activos": sum(
            bool(resultado.get("activos_generados", {}))
            for resultado in resultados
        ),
        "total_activos_generados": len(activos),
        "total_con_errores": sum(
            bool(resultado.get("errores", [])) for resultado in resultados
        ),
        "total_fallos": len(fallos),
        "total_fallos_reintentables": len(fallos_reintentables),
        "fallos_por_etapa": fallos_por_etapa,
        "sentimiento_predominante": sentimiento_predominante,
        "sentimientos_predominantes": sentimientos_predominantes,
        "distribucion_sentimientos": _ordenar_distribucion(sentimientos),
        "temas_principales": _obtener_temas_principales(temas),
        "distribucion_temas": _ordenar_distribucion(temas),
        "distribucion_tipos_detectados": _ordenar_distribucion(tipos_detectados),
    }