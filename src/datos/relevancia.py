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
class ConfiguracionRelevancia:
    caracteres_minimos: int = 20
    puntaje_minimo: int = 40
    maximo_por_lote: int | None = None
    puntos_por_tipo: dict = field(default_factory=lambda: {
        "testimonio": 40, "pregunta_tecnica": 40, "feedback": 30, "comentario": 10,
    })
    puntos_por_longitud: int = 20
    puntos_por_palabra: int = 5
    maximo_palabras: int = 30
    puntos_por_frescura: int = 10
    dias_de_frescura: int = 7
    palabras_clave: tuple = (
        "aprendi", "trabajo", "empleo", "certificado", "mentor", "mentores",
        "proyecto", "proyectos", "python", "sql", "oci", "langchain",
        "langgraph", "llm", "datos", "curso", "portfolio", "error",
    )

    def __post_init__(self):
        for nombre in (
            "caracteres_minimos", "puntaje_minimo", "puntos_por_longitud", "puntos_por_palabra",
            "maximo_palabras", "puntos_por_frescura", "dias_de_frescura",
        ):
            valor = getattr(self, nombre)
            if type(valor) is not int or valor < 0:
                raise ValueError(f"{nombre} debe ser un entero no negativo")
        if self.caracteres_minimos < 1 or self.puntaje_minimo > 100:
            raise ValueError("caracteres_minimos debe ser >= 1 y puntaje_minimo <= 100")
        if self.maximo_por_lote is not None and (type(self.maximo_por_lote) is not int or self.maximo_por_lote < 1):
            raise ValueError("maximo_por_lote debe ser null o un entero positivo")
        if not isinstance(self.puntos_por_tipo, dict) or set(self.puntos_por_tipo) != TIPOS:
            raise ValueError("puntos_por_tipo debe contener los cuatro tipos admitidos")
        if any(type(v) is not int or v < 0 for v in self.puntos_por_tipo.values()):
            raise ValueError("Los pesos de tipo deben ser enteros no negativos")
        maximo = (max(self.puntos_por_tipo.values()) + self.puntos_por_longitud
                  + self.maximo_palabras + self.puntos_por_frescura)
        if maximo > 100:
            raise ValueError("La suma máxima de los pesos no puede superar 100")
        if not isinstance(self.palabras_clave, (list, tuple)) or any(
            not isinstance(p, str) or not p.isalpha() for p in self.palabras_clave
        ):
            raise ValueError("palabras_clave debe ser una lista de palabras individuales")

    def como_dict(self):
        return asdict(self)


def puntuar_interaccion(interaccion, configuracion, fecha_referencia):
    """Devuelve evidencia del puntaje y exclusiones, sin modificar la entrada."""
    texto = interaccion["texto"]
    palabras = re.findall(r"\b\w+\b", normalizar_busqueda(URL.sub(" ", texto)))
    claves = {normalizar_busqueda(p) for p in configuracion.palabras_clave}
    encontradas = sorted(set(palabras) & claves)
    motivos = []
    advertencias = []
    if len(texto) < configuracion.caracteres_minimos:
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
            elif edad <= configuracion.dias_de_frescura * 86400:
                frescura = configuracion.puntos_por_frescura
        except ValueError:
            advertencias.append("fecha_invalida")
    desglose = {
        "tipo": configuracion.puntos_por_tipo[interaccion["tipo"]],
        "longitud": min(len(palabras), 20) * configuracion.puntos_por_longitud // 20,
        "palabras_clave": min(len(encontradas) * configuracion.puntos_por_palabra, configuracion.maximo_palabras),
        "frescura": frescura,
    }
    puntaje = sum(desglose.values())
    if puntaje < configuracion.puntaje_minimo:
        motivos.append("bajo_umbral")
    return {
        "puntaje": puntaje, "desglose": desglose, "palabras_clave": encontradas,
        "motivos": motivos, "advertencias": advertencias,
    }


def seleccionar_lote(lote, configuracion, fecha_referencia):
    """Filtra por lote; orden estable por puntaje y posición original."""
    vistos_id = set()
    vistos_texto = set()
    evaluaciones = []
    for indice, mensaje in enumerate(lote["interacciones"]):
        evaluacion = puntuar_interaccion(mensaje, configuracion, fecha_referencia)
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
    elegidos = candidatos if configuracion.maximo_por_lote is None else candidatos[:configuracion.maximo_por_lote]
    for e in elegidos:
        e["seleccionado"] = True
    for e in candidatos[len(elegidos):]:
        e["motivos"].append("fuera_maximo_por_lote")
    return [lote["interacciones"][e["indice"]] for e in elegidos], evaluaciones
