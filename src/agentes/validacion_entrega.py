"""Validaciones de la salida interna antes de crear la entrega pública."""


def validar_resultados(
    resultados: list[dict],
    *,
    version_contrato: str = "1.4",
) -> None:
    if version_contrato not in {"1.2", "1.3", "1.4"}:
        raise ValueError(
            f"Versión de contrato no soportada: {version_contrato}"
        )

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
                raise ValueError(
                    f"{identificador}: registro de fallo inválido"
                )

        # Validar los análisis exitosos, aunque no existan fallos.
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

            # Los campos de spam son obligatorios desde v1.4.
            if version_contrato == "1.4":
                es_spam = resultado.get("es_spam_detectado")

                if type(es_spam) is not bool:
                    raise ValueError(
                        f"{identificador}: es_spam_detectado debe ser booleano"
                    )

                if "motivo_spam" not in resultado:
                    raise ValueError(
                        f"{identificador}: falta el campo motivo_spam"
                    )

                motivo = resultado["motivo_spam"]

                if es_spam:
                    if (
                        not isinstance(motivo, str)
                        or not motivo.strip()
                        or len(motivo) > 160
                    ):
                        raise ValueError(
                            f"{identificador}: spam detectado requiere "
                            "un motivo válido de máximo 160 caracteres"
                        )
                elif motivo is not None:
                    raise ValueError(
                        f"{identificador}: un mensaje sin spam "
                        "debe tener motivo_spam=None"
                    )

            elif (
                "es_spam_detectado" in resultado
                or "motivo_spam" in resultado
            ):
                raise ValueError(
                    f"{identificador}: los campos de spam no pertenecen "
                    f"al contrato v{version_contrato}"
                )

    if len(ids) != len(set(ids)):
        raise ValueError(
            "La salida de Data Science contiene IDs repetidos"
        )
