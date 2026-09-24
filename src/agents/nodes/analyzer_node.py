from src.agents.chains import cadena_analisis
from src.agents.state import AgentState


def analizar_mensaje(state: AgentState) -> dict:
    """
    Analiza una interacción utilizando la cadena de LangChain.

    Recibe el estado actual y devuelve únicamente
    los nuevos campos generados por la IA.
    """

    try:
        resultado = cadena_analisis.invoke(
            {
                "origen": state["origen"],
                "canal": state["canal"],
                "idioma": state["idioma"],
                "tipo_original": state["tipo_original"],
                "texto": state["texto"],
            }
        )

        return {
            "sentimiento": resultado.sentimiento,
            "tema_principal": resultado.tema_principal,
            "subtema": resultado.subtema,
            "tipo_detectado": resultado.tipo_detectado,
        }

    except Exception as error:
        errores = list(state.get("errores", []))

        errores.append(
            f"Error durante el análisis del mensaje: {error}"
        )

        return {
            "errores": errores
        }