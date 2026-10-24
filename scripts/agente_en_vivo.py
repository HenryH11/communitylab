"""Agente en vivo de CommunityLab desde la terminal.

Uso:
    python -m scripts.agente_en_vivo "Crea un post de LinkedIn con testimonios positivos"
    python -m scripts.agente_en_vivo            # abre un chat
    python -m scripts.agente_en_vivo --verificar "Crea un post para Instagram"
"""

import argparse
import json
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

from src.agentes.conversacion import LIMITE_CARACTERES_X as LIMITE_X, AgenteConversacional
from src.agentes.observabilidad import LOGGER, configurar_logging


RAIZ_REPOSITORIO = Path(__file__).resolve().parents[1]
RUTA_DATOS = RAIZ_REPOSITORIO / "docs/evidencia2_entrega_ciencia_datos_completa.json"

NOMBRES_MODO = {
    "prompt_estricto": "estricto (1 llamada, rápido, sin verificación separada)",
    "verificacion_automatica": "verificación automática (2 llamadas, revisa cada afirmación)",
}
COMANDOS_MODO = {
    "/estricto": "prompt_estricto",
    "/verificar": "verificacion_automatica",
}
AYUDA_CHAT = (
    "Comandos: /estricto · /verificar · /modo (ver modo actual) · /ayuda · salir"
)


def _mostrar(salida: dict, detalle: bool) -> None:
    print(f"\n{salida['respuesta']}")

    borrador = salida.get("borrador")
    if borrador:
        print(f"\n--- Borrador para {borrador['plataforma']} ---")
        print(borrador["titulo"])
        print(f"\n{borrador['contenido']}")
        print(f"\n{' '.join(borrador['hashtags'])}")
        if borrador["plataforma"] == "x" and len(borrador["contenido"]) > LIMITE_X:
            print(f"\n⚠ Excede el límite de X: {len(borrador['contenido'])}/{LIMITE_X} "
                  "caracteres. Pide «hazlo más corto».")

    if salida["citas"]:
        print(f"\nFuentes: {', '.join(salida['citas'])}")

    verificacion = salida["verificacion"]
    if salida.get("borrador"):
        if verificacion["estado"] == "no_verificado":
            print("Verificación: no verificado (modo estricto). Usa /verificar para revisar afirmaciones.")
        else:
            print(f"Verificación: {verificacion['estado']} — {verificacion['resumen']}")
            for afirmacion in verificacion.get("afirmaciones", []):
                if not afirmacion["respaldada"]:
                    print(f"  ✗ Sin respaldo: {afirmacion['afirmacion']}")

    if detalle:
        filtros = {clave: valor for clave, valor in salida["filtros"].items() if valor}
        print(f"\n[modo={salida['modo']} coincidencias={salida['total_coincidencias']} "
              f"filtros={json.dumps(filtros, ensure_ascii=False)}]")


def _explicar_error(error: Exception) -> str:
    if isinstance(error, ValueError):
        return str(error)
    actual: BaseException | None = error
    while actual is not None:
        codigo = getattr(actual, "status_code", None)
        if codigo == 404:
            return (
                "el modelo configurado no está disponible (404). Revisa "
                "COMMUNITYLAB_MODELO_NVIDIA_* en .env."
            )
        if codigo in {401, 403}:
            return f"el proveedor rechazó las credenciales ({codigo}). Revisa la API key en .env."
        if codigo == 429:
            return "se alcanzó el límite de uso del proveedor (429). Intenta en unos minutos."
        actual = actual.__cause__ or actual.__context__
    return f"el proveedor de IA falló ({type(error).__name__}). Revisa salida/logs/ciencia_datos.jsonl."


def _responder(agente: AgenteConversacional, consulta: str, modo: str, detalle: bool) -> bool:
    try:
        salida = agente.consultar(consulta, modo_verificacion=modo)
    except Exception as error:  # noqa: BLE001 - el chat debe seguir disponible
        print(f"\nNo pude responder: {_explicar_error(error)}", file=sys.stderr)
        return False
    _mostrar(salida, detalle)
    return True


def principal() -> int:
    parser = argparse.ArgumentParser(
        description="Pregunta al agente en vivo sobre los datos de la comunidad."
    )
    parser.add_argument(
        "consulta",
        nargs="*",
        help="Lo que quieres pedir. Si se omite, se abre un chat.",
    )
    parser.add_argument(
        "--verificar",
        action="store_true",
        help="Verifica las afirmaciones del borrador con una segunda llamada.",
    )
    parser.add_argument(
        "--datos",
        type=Path,
        default=RUTA_DATOS,
        help="Archivo JSON con la salida de Ciencia de Datos.",
    )
    parser.add_argument(
        "--detalle",
        action="store_true",
        help="Muestra filtros detectados y número de coincidencias.",
    )
    argumentos = parser.parse_args()

    # La terminal de VS Code puede conservar valores viejos de .env; aquí manda el archivo.
    load_dotenv(dotenv_path=RAIZ_REPOSITORIO / ".env", override=True)
    configurar_logging()
    if not argumentos.detalle and not LOGGER.handlers:
        # Sin manejador, Python imprimiría reintentos internos en la terminal.
        LOGGER.addHandler(logging.NullHandler())
    with argumentos.datos.open("r", encoding="utf-8") as archivo:
        agente = AgenteConversacional(json.load(archivo))
    modo = "verificacion_automatica" if argumentos.verificar else "prompt_estricto"

    consulta = " ".join(argumentos.consulta).strip()
    if consulta:
        return 0 if _responder(agente, consulta, modo, argumentos.detalle) else 1

    print("Agente en vivo de CommunityLab. Escribe tu pedido ('salir' para terminar).")
    print(AYUDA_CHAT)
    print(f"Modo actual: {NOMBRES_MODO[modo]}")
    while True:
        try:
            consulta = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        comando = consulta.lower()
        if comando in {"salir", "exit", "q"}:
            return 0
        if comando in COMANDOS_MODO:
            modo = COMANDOS_MODO[comando]
            print(f"Modo cambiado a: {NOMBRES_MODO[modo]}")
            continue
        if comando == "/modo":
            print(f"Modo actual: {NOMBRES_MODO[modo]}")
            continue
        if comando == "/ayuda":
            print(AYUDA_CHAT)
            continue
        if consulta:
            _responder(agente, consulta, modo, argumentos.detalle)


if __name__ == "__main__":
    sys.exit(principal())
