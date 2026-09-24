from src.agents.state import AgentState


def generar_activos_mock(state: AgentState) -> dict:
    """
    Simula la generación de activos según las rutas seleccionadas.

    Semana 1:
    todavía no genera contenido real con LLM.
    """

    activos = {}

    for ruta in state.get("rutas", []):

        if ruta == "faq":
            activos["faq"] = {
                "status": "mock",
                "mensaje": "Aquí se generará una FAQ.",
            }

        elif ruta == "caso_exito":
            activos["caso_exito"] = {
                "status": "mock",
                "mensaje": "Aquí se generará un caso de éxito.",
            }

        elif ruta == "linkedin":
            activos["linkedin"] = {
                "status": "mock",
                "mensaje": "Aquí se generará un post de LinkedIn.",
            }

        elif ruta == "newsletter":
            activos["newsletter"] = {
                "status": "mock",
                "mensaje": "Aquí se generará contenido para Newsletter.",
            }

    return {
        "activos_generados": activos
    }