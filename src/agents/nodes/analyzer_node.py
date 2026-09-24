from src.agents.chains import cadena_analisis
from src.agents.state import AgentState


def analizar_mensaje(state: AgentState) -> dict:
    """
    Analiza una interacción utilizando la cadena de LangChain.

    Recibe el estado actual y devuelve únicamente
    los nuevos campos generados por la IA.

    Si ocurre un error, lo registra en AgentState
    para que LangGraph pueda finalizar el flujo
    de forma controlada.
    """

    try:
        resultado = cadena_analisis.invoke(
            {
                "origen": state.get("origen", ""),
                "canal": state.get("canal", ""),
                "idioma": state.get("idioma", "es"),
                "tipo_original": state.get("tipo_original", ""),
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
            f"analizar_mensaje: "
            f"{type(error).__name__}: {error}"
        )

        return {
            "errores": errores
        }