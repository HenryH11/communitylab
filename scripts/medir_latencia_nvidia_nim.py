"""Ensayo aislado de NVIDIA NIM. Sin red salvo al indicar --en-vivo.

No cambia el proveedor del grafo ni implementa respaldo hacia Gemini.
Ejecutar desde la raíz con python -m scripts.medir_latencia_nvidia_nim --help.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
from statistics import mean, median
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from dotenv import load_dotenv

from src.agentes.modelos import AnalisisMensaje

# DS-Semana3 movió prompts y modelos a módulos propios; se admiten ambas ubicaciones.
try:
    from src.agentes.modelos import PublicacionLinkedIn, SugerenciaPreguntasFrecuentes
    from src.agentes.prompts.analisis import template_analisis
    from src.agentes.prompts.linkedin import prompt_linkedin as _prompt_linkedin
    from src.agentes.prompts.preguntas_frecuentes import (
        prompt_preguntas_frecuentes as _prompt_preguntas_frecuentes,
    )
except ImportError:
    from src.agentes.cadenas import template_analisis
    from src.agentes.nodos.nodos_generadores import (
        PublicacionLinkedIn, SugerenciaPreguntasFrecuentes,
        _prompt_linkedin, _prompt_preguntas_frecuentes,
    )
from src.datos.entrega_ia import preparar_paquete_ia
from src.datos.relevancia import leer_fecha


RAIZ = Path(__file__).resolve().parents[1]
ENDPOINT = "https://integrate.api.nvidia.com/v1/chat/completions"
# Verificación manual del catálogo; revisar otra vez antes de una corrida real.
MODELOS_FREE_ENDPOINT = {
    "nvidia/nemotron-3.5-lightning-30b-a3b":
        "https://build.nvidia.com/nvidia/nemotron-3.5-lightning-30b-a3b/build",
    "deepseek-ai/deepseek-v4.1-flash":
        "https://build.nvidia.com/deepseek-ai/deepseek-v4.1-flash",
}
FECHA_CATALOGO = "2026-10-06"
MODELO_NEMOTRON = "nvidia/nemotron-3.5-lightning-30b-a3b"
TAREAS = {
    "analisis": (template_analisis, AnalisisMensaje),
    "linkedin": (_prompt_linkedin, PublicacionLinkedIn),
    "faq": (_prompt_preguntas_frecuentes, SugerenciaPreguntasFrecuentes),
}


class SinRedirecciones(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class RespuestaInvalida(ValueError):
    pass


class Ritmo:
    """Intervalo mínimo entre inicios HTTP, compartido por todos los trabajadores."""

    def __init__(self, intervalo):
        self.intervalo = intervalo
        self.siguiente = 0.0
        self.lock = threading.Lock()

    def esperar(self):
        with self.lock:
            demora = max(0.0, self.siguiente - time.monotonic())
            if demora:
                time.sleep(demora)
            self.siguiente = time.monotonic() + self.intervalo


def preparar_casos(paquete, tarea):
    plantilla, esquema = TAREAS[tarea]
    ids_contenido = set(paquete["plan"]["ids_contenido"])
    casos = []
    for estado in paquete["estados"]:
        if tarea == "linkedin" and not (
            estado["tipo_original"] == "testimonio" and estado["id"] in ids_contenido
        ):
            continue
        if tarea == "faq" and not (
            (estado["tipo_original"] == "pregunta_tecnica" and estado["id"] in ids_contenido)
            or (estado["tipo_original"] == "pregunta_programa" and estado["elegible_faq"])
        ):
            continue
        # No inventar un análisis previo para las pruebas aisladas de generación.
        contexto = {**estado, "tema_principal": "", "subtema": "", "tipo_detectado": ""}
        roles = {"system": "system", "human": "user", "ai": "assistant"}
        mensajes = [
            {"role": roles[m.type], "content": m.content}
            for m in plantilla.format_messages(**contexto)
        ]
        mensajes[0]["content"] += (
            "\nDevuelve exclusivamente una INSTANCIA de datos JSON que cumpla el esquema siguiente. "
            "Analiza el mensaje del usuario y rellena los campos con los resultados. "
            "NO devuelvas ni copies el esquema: properties, required, title y type no son campos de la respuesta. "
            "No incluyas markdown. Esquema de validación (solo como referencia): "
            + json.dumps(esquema.model_json_schema(), ensure_ascii=False)
        )
        huella = hashlib.sha256(
            json.dumps(mensajes, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        casos.append({"id": estado["id"], "mensajes": mensajes, "sha256_solicitud": huella})
    if not casos:
        raise ValueError("No hay mensajes válidos para la tarea elegida")
    return casos


def solicitar(modelo, caso, clave, timeout, max_tokens, sin_razonamiento=False):
    cuerpo = {
        "model": modelo, "messages": caso["mensajes"], "stream": False,
        "temperature": 0, "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }
    if sin_razonamiento:
        if modelo != MODELO_NEMOTRON:
            raise ValueError("La desactivación de razonamiento solo se verificó para Nemotron")
        cuerpo["chat_template_kwargs"] = {"enable_thinking": False}
    peticion = Request(
        ENDPOINT, data=json.dumps(cuerpo, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": "Bearer " + clave, "Content-Type": "application/json"},
        method="POST",
    )
    with build_opener(SinRedirecciones()).open(peticion, timeout=timeout) as respuesta:
        return json.loads(respuesta.read().decode("utf-8"))


def validar_respuesta(respuesta, esquema):
    try:
        eleccion = respuesta["choices"][0]
        if eleccion.get("finish_reason") != "stop":
            raise RespuestaInvalida("finalizacion_incompleta")
        datos = json.loads(eleccion["message"]["content"])
        if not isinstance(datos, dict) or set(datos) - set(esquema.model_fields):
            raise RespuestaInvalida("campos_no_admitidos")
        return esquema.model_validate(datos, strict=True).model_dump()
    except RespuestaInvalida:
        raise
    except (ValueError, TypeError, KeyError, IndexError, AttributeError) as error:
        raise RespuestaInvalida("json_o_esquema_invalido") from error


def medir(modelo, caso, repeticion, *, tarea, clave, timeout, max_tokens, ritmo, sin_razonamiento=False):
    inicio_espera = time.perf_counter()
    ritmo.esperar()
    inicio = time.perf_counter()
    registro = {
        "id": caso["id"], "modelo": modelo, "repeticion": repeticion,
        "sha256_solicitud": caso["sha256_solicitud"],
        "espera_programacion_seg": round(inicio - inicio_espera, 6),
        "valida": False,
    }
    try:
        respuesta = solicitar(modelo, caso, clave, timeout, max_tokens, sin_razonamiento)
        registro["salida"] = validar_respuesta(respuesta, TAREAS[tarea][1])
        registro["valida"] = True
        uso = respuesta.get("usage")
        if isinstance(uso, dict):
            registro["uso_reportado_proveedor"] = {
                k: uso[k] for k in ("prompt_tokens", "completion_tokens", "total_tokens")
                if type(uso.get(k)) is int and uso[k] >= 0
            }
    except HTTPError as error:
        registro["error"] = {"tipo": "HTTPError", "codigo_http": error.code}
        error.close()
    except (URLError, TimeoutError, OSError, ValueError, TypeError) as error:
        # No volcar mensajes del proveedor, cuerpos HTTP ni cabeceras con claves.
        registro["error"] = {"tipo": type(error).__name__}
    registro["duracion_solicitud_seg"] = round(time.perf_counter() - inicio, 6)
    return registro


def estadisticas(valores):
    if not valores:
        return None
    ordenados = sorted(valores)
    return {
        "promedio": round(mean(valores), 6), "mediana": round(median(valores), 6),
        "p95": ordenados[math.ceil(0.95 * len(ordenados)) - 1],
        "minimo": ordenados[0], "maximo": ordenados[-1],
    }


def resumir(registros, modelos, umbral):
    resumen = {}
    for modelo in modelos:
        intentos = [r for r in registros if r["modelo"] == modelo]
        validos = [r for r in intentos if r["valida"]]
        tiempos = [r["duracion_solicitud_seg"] for r in validos]
        resumen[modelo] = {
            "intentos": len(intentos), "respuestas_validas": len(validos),
            "errores": len(intentos) - len(validos),
            "latencia_validas_seg": estadisticas(tiempos),
            "latencia_intentos_seg": estadisticas([r["duracion_solicitud_seg"] for r in intentos]),
            "validas_sobre_umbral": sum(t > umbral for t in tiempos) if umbral is not None else None,
        }
    return resumen


def numero_positivo(texto):
    valor = float(texto)
    if not math.isfinite(valor) or valor <= 0:
        raise argparse.ArgumentTypeError("Debe ser un número finito mayor que cero")
    return valor


def principal(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entrada", type=Path, default=RAIZ / "src/datos/mensajes_comunidad_simulados.json")
    parser.add_argument("--modelo", action="append", required=True, choices=MODELOS_FREE_ENDPOINT,
                        help="Free Endpoint verificado; repetir para comparar")
    parser.add_argument("--tarea", choices=TAREAS, default="analisis")
    parser.add_argument("--fecha-referencia", default="2026-09-17T12:00:00Z")
    parser.add_argument("--concurrencia", type=int, choices=range(1, 5), default=1)
    parser.add_argument("--repeticiones", type=int, choices=range(1, 11), default=1)
    parser.add_argument("--intervalo", type=numero_positivo, default=1.0, help="Segundos mínimos entre inicios HTTP")
    parser.add_argument("--timeout", type=numero_positivo, default=60.0, help="Timeout de operaciones de red, en segundos")
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--sin-razonamiento", action="store_true",
                        help="Desactiva enable_thinking; solo disponible para Nemotron")
    parser.add_argument("--umbral-segundos", type=numero_positivo, help="Referencia por solicitud; no activa respaldo")
    parser.add_argument("--en-vivo", action="store_true", help="Autoriza llamadas reales a NVIDIA; consume cuota")
    parser.add_argument("--salida", type=Path, help="JSON opcional; usar salida/validacion_semana3/")
    args = parser.parse_args(argv)
    try:
        if args.max_tokens < 1 or args.max_tokens > 32768:
            raise ValueError("max-tokens debe estar entre 1 y 32768")
        modelos = list(dict.fromkeys(m.strip() for m in args.modelo))
        if args.sin_razonamiento and any(m != MODELO_NEMOTRON for m in modelos):
            raise ValueError("--sin-razonamiento solo admite el modelo Nemotron")
        if any(not m or any(c.isspace() for c in m) for m in modelos):
            raise ValueError("Usa identificadores de modelo no vacíos y sin espacios")
        if args.salida is not None:
            if args.salida.resolve() == args.entrada.resolve():
                raise ValueError("El informe no puede reemplazar la entrada")
            if args.salida.suffix.lower() != ".json" or args.salida.is_dir():
                raise ValueError("La salida debe ser un archivo .json")
        contenido = args.entrada.read_bytes()
        datos = json.loads(contenido.decode("utf-8"))
        referencia = leer_fecha(args.fecha_referencia).isoformat()
        paquete = preparar_paquete_ia(datos, fecha_referencia=referencia)
        casos = preparar_casos(paquete, args.tarea)
        reporte = {
            "version": "1.0", "modo": "en_vivo" if args.en_vivo else "plan_sin_red",
            "fecha_utc": datetime.now(timezone.utc).isoformat(), "endpoint": ENDPOINT,
            "tarea": args.tarea, "modelos": modelos, "fecha_referencia": referencia,
            "catalogo_free_endpoint": {
                "verificado_el": FECHA_CATALOGO, "estado_observado": "Available",
                "fuentes": {m: MODELOS_FREE_ENDPOINT[m] for m in modelos},
                "verificacion_en_vivo": False,
            },
            "sha256_entrada": hashlib.sha256(contenido).hexdigest(),
            "casos": len(casos), "ids": [c["id"] for c in casos],
            "solicitudes_planificadas": len(casos) * len(modelos) * args.repeticiones,
            "concurrencia": args.concurrencia, "intervalo_minimo_seg": args.intervalo,
            "timeout_operaciones_red_seg": args.timeout, "max_tokens": args.max_tokens,
            "razonamiento": "desactivado_enable_thinking" if args.sin_razonamiento else "predeterminado_proveedor",
            "repeticiones": args.repeticiones, "umbral_solicitud_seg": args.umbral_segundos,
            "alcance": "Solicitudes individuales aisladas; no mide el grafo ni exactitud semántica",
            "respaldo_gemini": "no_implementado_en_este_ensayo",
        }
        registros = []
        if args.en_vivo:
            load_dotenv(RAIZ / ".env")
            clave = os.getenv("NVIDIA_API_KEY", "").strip()
            if not clave:
                raise ValueError("Falta NVIDIA_API_KEY en el entorno local")
            ritmo = Ritmo(args.intervalo)
            inicio = time.perf_counter()
            for modelo in modelos:
                trabajos = [(c, r) for r in range(1, args.repeticiones + 1) for c in casos]

                def trabajo(par):
                    return medir(modelo, par[0], par[1], tarea=args.tarea, clave=clave,
                                 timeout=args.timeout, max_tokens=args.max_tokens, ritmo=ritmo,
                                 sin_razonamiento=args.sin_razonamiento)

                with ThreadPoolExecutor(max_workers=args.concurrencia) as grupo:
                    registros.extend(grupo.map(trabajo, trabajos))
            reporte["duracion_ensayo_seg"] = round(time.perf_counter() - inicio, 6)
            reporte["resumen_por_modelo"] = resumir(registros, modelos, args.umbral_segundos)
            reporte["resultados"] = registros
        if args.salida:
            args.salida.parent.mkdir(parents=True, exist_ok=True)
            args.salida.write_text(json.dumps(reporte, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        # Las respuestas completas solo se guardan en el informe opcional.
        print(json.dumps({k: v for k, v in reporte.items() if k != "resultados"}, ensure_ascii=False, indent=2))
        return 1 if any(not r["valida"] for r in registros) else 0
    except (OSError, ValueError, TypeError) as error:
        parser.exit(2, f"Error: {error}\n")


if __name__ == "__main__":
    raise SystemExit(principal())
