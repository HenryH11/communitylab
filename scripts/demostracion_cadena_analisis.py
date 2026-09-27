import time

from src.agentes.cadenas import cadena_analisis


mensaje = {
    "origen": "Discord_Grupo_ONE_G10",
    "canal": "#logros-y-empleos",
    "idioma": "es",
    "tipo_original": "comentario",
    "texto": (
        "Después de varios meses estudiando conseguí mi primer trabajo "
        "como analista de datos. Los proyectos de la comunidad fueron "
        "clave durante mi entrevista."
    ),
}


def principal():
    print("=" * 60)
    print("ANÁLISIS DE UN MENSAJE")
    print("=" * 60)
    print("\nMensaje a analizar:")
    print(mensaje["texto"])
    print("\nEnviando mensaje a Gemini...")

    inicio = time.perf_counter()
    try:
        resultado = cadena_analisis.invoke(mensaje)
    except Exception as error:
        tiempo_total = time.perf_counter() - inicio
        print("\nERROR")
        print("-" * 60)
        print(f"Tipo de error: {type(error).__name__}")
        print(f"Detalle: {error}")
        print(f"Tiempo transcurrido: {tiempo_total:.2f} segundos")
        return

    tiempo_total = time.perf_counter() - inicio
    print("\nRESULTADO")
    print("-" * 60)
    print("Sentimiento:", resultado.sentimiento)
    print("Tema principal:", resultado.tema_principal)
    print("Subtema:", resultado.subtema)
    print("Tipo original:", mensaje["tipo_original"])
    print("Tipo detectado:", resultado.tipo_detectado)
    print(f"\nTiempo de respuesta: {tiempo_total:.2f} segundos")


if __name__ == "__main__":
    principal()