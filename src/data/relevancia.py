"""Selección determinista de mensajes. Solo biblioteca estándar; no usa LLMs."""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import re
import unicodedata


TIPOS = {"testimonio", "pregunta_tecnica", "comentario", "feedback"}
URL = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)


def normalizar_busqueda(texto):
    """Normalización para comparar; nunca sustituye el texto de salida."""
    return "".join(
        c for c in unicodedata.normalize("NFD", texto.casefold())
        if unicodedata.category(c) != "Mn"
    )


def leer_fecha(texto):
    """Acepta ISO 8601 con zona horaria. No inventa fechas faltantes."""
    fecha = datetime.fromisoformat(texto.replace("Z", "+00:00"))
    if fecha.tzinfo is None:
        raise ValueError("La fecha debe incluir zona horaria, por ejemplo +00:00 o Z")
    return fecha.astimezone(timezone.utc)


@dataclass(frozen=True)
class ConfigRelevancia:
    min_caracteres: int = 20
    min_puntaje: int = 40
    top_n: int | None = None
    puntos_tipo: dict = field(default_factory=lambda: {
        "testimonio": 40, "pregunta_tecnica": 40, "feedback": 30, "comentario": 10,
    })
    puntos_longitud: int = 20
    puntos_palabra: int = 5
    tope_palabras: int = 30
    puntos_frescura: int = 10
    dias_frescura: int = 7
    palabras_clave: tuple = (
        "aprendi", "trabajo", "empleo", "certificado", "mentor", "mentores",
        "proyecto", "proyectos", "python", "sql", "oci", "langchain",
        "langgraph", "llm", "datos", "curso", "portfolio", "error",
    )

    def __post_init__(self):
        for nombre in (
            "min_caracteres", "min_puntaje", "puntos_longitud", "puntos_palabra",
            "tope_palabras", "puntos_frescura", "dias_frescura",
        ):
            valor = getattr(self, nombre)
            if type(valor) is not int or valor < 0:
                raise ValueError(f"{nombre} debe ser un entero no negativo")
        if self.min_caracteres < 1 or self.min_puntaje > 100:
            raise ValueError("min_caracteres debe ser >= 1 y min_puntaje <= 100")
        if self.top_n is not None and (type(self.top_n) is not int or self.top_n < 1):
            raise ValueError("top_n debe ser null o un entero positivo")
        if not isinstance(self.puntos_tipo, dict) or set(self.puntos_tipo) != TIPOS:
            raise ValueError("puntos_tipo debe contener los cuatro tipos admitidos")
        if any(type(v) is not int or v < 0 for v in self.puntos_tipo.values()):
            raise ValueError("Los pesos de tipo deben ser enteros no negativos")
        maximo = (max(self.puntos_tipo.values()) + self.puntos_longitud
                  + self.tope_palabras + self.puntos_frescura)
        if maximo > 100:
            raise ValueError("La suma máxima de los pesos no puede superar 100")
        if not isinstance(self.palabras_clave, (list, tuple)) or any(
            not isinstance(p, str) or not p.isalpha() for p in self.palabras_clave
        ):
            raise ValueError("palabras_clave debe ser una lista de palabras individuales")

    def como_dict(self):
        return asdict(self)


def puntuar_interaccion(interaccion, config, fecha_referencia):
    """Devuelve evidencia del puntaje y exclusiones, sin modificar la entrada."""
    texto = interaccion["texto"]
    palabras = re.findall(r"\b\w+\b", normalizar_busqueda(URL.sub(" ", texto)))
    claves = {normalizar_busqueda(p) for p in config.palabras_clave}
    encontradas = sorted(set(palabras) & claves)
    motivos = []
    advertencias = []
    if len(texto) < config.min_caracteres:
        motivos.append("texto_corto")
    if URL.search(texto) and not re.search(r"\w", URL.sub(" ", texto)):
        motivos.append("solo_enlaces")
    if len(palabras) >= 6 and len(set(palabras)) == 1:
        motivos.append("texto_repetitivo")
    if texto.casefold() in {"[deleted]", "[removed]"} or interaccion["autor"] == "[deleted]":
        motivos.append("contenido_eliminado")
    frescura = 0
    fecha = interaccion.get("fecha")
    if fecha is None:
        advertencias.append("sin_fecha")
    else:
        try:
            edad = (fecha_referencia - leer_fecha(fecha)).total_seconds()
            if edad < 0:
                advertencias.append("fecha_futura")
            elif edad <= config.dias_frescura * 86400:
                frescura = config.puntos_frescura
        except ValueError:
            advertencias.append("fecha_invalida")
    desglose = {
        "tipo": config.puntos_tipo[interaccion["tipo"]],
        "longitud": min(len(palabras), 20) * config.puntos_longitud // 20,
        "palabras_clave": min(len(encontradas) * config.puntos_palabra, config.tope_palabras),
        "frescura": frescura,
    }
    puntaje = sum(desglose.values())
    if puntaje < config.min_puntaje:
        motivos.append("bajo_umbral")
    return {
        "puntaje": puntaje, "desglose": desglose, "palabras_clave": encontradas,
        "motivos": motivos, "advertencias": advertencias,
    }


def seleccionar_lote(lote, config, fecha_referencia):
    """Filtra por lote; orden estable por puntaje y posición original."""
    vistos_id = set()
    vistos_texto = set()
    evaluaciones = []
    for indice, mensaje in enumerate(lote["interacciones"]):
        evaluacion = puntuar_interaccion(mensaje, config, fecha_referencia)
        clave = tuple(normalizar_busqueda(mensaje[c]) for c in ("autor", "canal", "texto"))
        identificador = mensaje.get("id")
        if clave in vistos_texto or (identificador is not None and identificador in vistos_id):
            evaluacion["motivos"].append("duplicado")
        vistos_texto.add(clave)
        if identificador is not None:
            vistos_id.add(identificador)
        evaluacion.update(indice=indice, id=identificador, seleccionado=False)
        evaluaciones.append(evaluacion)
    candidatos = sorted(
        (e for e in evaluaciones if not e["motivos"]),
        key=lambda e: (-e["puntaje"], e["indice"]),
    )
    elegidos = candidatos if config.top_n is None else candidatos[:config.top_n]
    for e in elegidos:
        e["seleccionado"] = True
    for e in candidatos[len(elegidos):]:
        e["motivos"].append("fuera_top_n")
    return [lote["interacciones"][e["indice"]] for e in elegidos], evaluaciones
