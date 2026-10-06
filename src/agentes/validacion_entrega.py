"""Validaciones de la salida interna antes de crear la entrega pública."""


def validar_resultados(resultados: list[dict]) -> None:
    ids = []

    for resultado in resultados:
        identificador = resultado.get("id")

        if (
            not isinstance(identificador, str)
            or not identificador.strip()
            or identificador != identificador.strip()
        ):
            raise ValueError(
                "Cada resultado de Data Science debe tener un ID válido"
            )

        ids.append(identificador)

        rutas = resultado.get("rutas", [])
        activos = resultado.get("activos_generados", {})
        errores = resultado.get("errores", [])

        if not isinstance(rutas, list):
            raise ValueError(f"{identificador}: rutas debe ser una lista")

        if not isinstance(activos, dict):
            raise ValueError(
                f"{identificador}: activos_generados debe ser un diccionario"
            )

        if not isinstance(errores, list):
            raise ValueError(f"{identificador}: errores debe ser una lista")

        fallos = resultado.get("fallos", [])
        if not isinstance(fallos, list):
            raise ValueError(f"{identificador}: fallos debe ser una lista")
        for fallo in fallos:
            if (
                not isinstance(fallo, dict)
                or fallo.get("id") != identificador
                or not isinstance(fallo.get("etapa"), str)
                or not isinstance(fallo.get("tipo_error"), str)
                or not isinstance(fallo.get("mensaje"), str)
            ):
                raise ValueError(f"{identificador}: registro de fallo inválido")

        if not errores:
            for campo in (
                "sentimiento",
                "tema_principal",
                "subtema",
                "tipo_detectado",
            ):
                valor = resultado.get(campo)

                if not isinstance(valor, str) or not valor.strip():
                    raise ValueError(
                        f"{identificador}: falta el campo de análisis {campo}"
                    )

    if len(ids) != len(set(ids)):
        raise ValueError("La salida de Data Science contiene IDs repetidos")