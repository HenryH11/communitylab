from src.agentes.grafo import procesar_estados_por_lotes
from scripts.apoyo_demostraciones import cargar_paquete_demostracion


MAX_MENSAJES = 23


def principal():
    paquete = cargar_paquete_demostracion()
    estados = paquete["estados"][:MAX_MENSAJES]
    resultados = procesar_estados_por_lotes(
        estados,
        ids_contenido=set(),
    )

    coincidencias = 0
    diferencias = []

    for estado, resultado in zip(estados, resultados):
        mensaje_id = estado["id"]
        print()
        print("=" * 80)
        print("ID:", mensaje_id)
        print("Autor:", estado["autor"])
        print("Canal:", estado["canal"])

        errores = resultado.get("errores", [])
        if errores:
            print("Errores:", errores)
            diferencias.append((mensaje_id, "error de análisis"))
            continue

        tipo_preliminar = estado["tipo_original"]
        tipo_detectado = resultado.get("tipo_detectado", "sin-clasificar")
        print("Tipo preliminar de Datos:", tipo_preliminar)
        print("Tipo detectado:", tipo_detectado)
        print("Sentimiento:", resultado.get("sentimiento"))
        print("Tema principal:", resultado.get("tema_principal"))

        if tipo_preliminar == tipo_detectado:
            coincidencias += 1
        else:
            diferencias.append(
                (mensaje_id, tipo_preliminar, tipo_detectado)
            )

    total = len(estados)
    porcentaje = coincidencias / total * 100 if total else 0
    print()
    print(
        "Coincidencia con etiquetas preliminares "
        f"(sin referencia validada): {coincidencias}/{total} ({porcentaje:.1f}%)"
    )

    if diferencias:
        print("Casos para revisar:")
        for diferencia in diferencias:
            print("-", diferencia)


if __name__ == "__main__":
    principal()