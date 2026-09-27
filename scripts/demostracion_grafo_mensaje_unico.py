from src.datos.ingesta import construir_estado_agente
from src.agentes.grafo import grafo


def principal():
    mensaje = {
        "id": "int-prueba-001",
        "autor": "Arnold",
        "canal": "#logros-y-empleos",
        "tipo": "comentario",
        "texto": (
            "Después de varios meses estudiando conseguí mi primer "
            "trabajo como analista de datos. Los proyectos que hice "
            "durante el programa fueron clave en mi entrevista."
        ),
    }
    estado_inicial = construir_estado_agente(
        mensaje,
        90,
        "Discord_Grupo_ONE_G10",
    )
    resultado = grafo.invoke(estado_inicial)

    print("\nRESULTADO FINAL DEL GRAFO")
    print("=" * 70)
    print("ID:", resultado.get("id"))
    print("Tipo original:", resultado.get("tipo_original"))
    print("Tipo detectado:", resultado.get("tipo_detectado"))
    print("Sentimiento:", resultado.get("sentimiento"))
    print("Tema principal:", resultado.get("tema_principal"))
    print("Subtema:", resultado.get("subtema"))
    print("Puntaje:", resultado.get("score_relevancia"))
    print("Rutas:", resultado.get("rutas", []))
    print("Activos:", resultado.get("activos_generados", {}))
    print("Errores:", resultado.get("errores", []))


if __name__ == "__main__":
    principal()
