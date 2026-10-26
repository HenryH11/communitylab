"""Catálogo diario: una captura, conversaciones aisladas y reemplazo parcial."""

from datetime import datetime, time, timezone
from collections.abc import Callable, Mapping
import logging
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.agentes.conversacion import AgenteConversacional, SalidaConversacional
from src.agentes.plataformas import PlataformaPublicacion
from src.app.fuente_agente import adaptar_conjunto, leer_base


ZONA = timezone.utc
HORA = time(13)
OBJETO = "plantillas/catalogo_actual.json"
_log = logging.getLogger(__name__)


class PlantillaDiaria(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str
    nombre: str
    prompt: str
    plataforma: PlataformaPublicacion | None = None


PLANTILLAS_DIARIAS = (
    PlantillaDiaria(
        id="linkedin", nombre="Publicación para LinkedIn", plataforma="linkedin",
        prompt="Crea un post profesional para LinkedIn con los 5 mejores comentarios positivos de la comunidad. Incluye una invitación a compartir experiencias.",
    ),
    PlantillaDiaria(
        id="instagram", nombre="Publicación para Instagram", plataforma="instagram",
        prompt="Crea un texto para Instagram con los 3 mejores comentarios positivos de la comunidad, cercano y con un llamado a participar. No prometas crear una imagen.",
    ),
    PlantillaDiaria(
        id="x", nombre="Publicación para X", plataforma="x",
        prompt="Crea un post para X con un comentario positivo destacado de la comunidad. Respeta 280 caracteres con hashtags.",
    ),
    PlantillaDiaria(
        id="boletin", nombre="Destacado para newsletter",
        prompt="Redacta una sección de máximo 180 palabras para un boletín de marketing sobre los comentarios positivos de la comunidad. En respuesta empieza con un titular Markdown (##), seguido de un único párrafo de síntesis. No enumeres ni copies los testimonios. Aclara que los conteos y porcentajes describen el subconjunto positivo, no toda la comunidad. Incluye fuentes en citas.",
    ),
    PlantillaDiaria(
        id="caso_exito", nombre="Caso de éxito", plataforma="linkedin",
        prompt="Crea un post para LinkedIn sobre un caso de éxito explícito de la comunidad. Tanto el título como el cuerpo deben describir solo el logro de una misma persona. No añadas un punto de partida como 'desde cero' si esa persona no lo dice. Si no hay evidencia de un logro real, explica la falta de evidencia sin inventarlo.",
    ),
    PlantillaDiaria(
        id="sentimiento", nombre="Sentimiento de comunidad",
        prompt="Analiza la distribución de sentimiento de toda la comunidad con conteos exactos y un resumen breve para marketing.",
    ),
    PlantillaDiaria(
        id="temas", nombre="Temas y tendencias",
        prompt="Resume los temas de toda la comunidad. Enumera todos los temas de distribucion_temas con su conteo exacto, de mayor a menor, conservando los empates. Añade una síntesis breve y fuentes. No afirmes cambios temporales sin evidencia.",
    ),
    PlantillaDiaria(
        id="insight_mejora", nombre="Oportunidades de mejora",
        prompt="Analiza los comentarios negativos de la comunidad e identifica oportunidades de mejora respaldadas por fuentes. Distingue problemas reportados por usuarios de sus sugerencias; no presentes los reportes como hechos comprobados.",
    ),
    PlantillaDiaria(
        id="preguntas_frecuentes", nombre="Preguntas de la comunidad",
        prompt="Identifica preguntas frecuentes entre todos los tipos de pregunta de la comunidad, técnicas y del programa, sin filtrar sentimiento. Resume las dudas con sus fuentes; no confundas cantidad de preguntas con repetición de una misma duda. Solo ofrece respuestas respaldadas por los mensajes.",
    ),
)


class EntradaDiaria(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nombre: str
    prompt: str
    generado_en: datetime
    salida: dict


class CatalogoDiario(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Literal[1] = 1
    intentado_en: datetime
    captura_en: datetime | None = None
    entradas: dict[str, EntradaDiaria] = Field(default_factory=dict)
    fallos: dict[str, str] = Field(default_factory=dict)


class VerificacionSinEvidencia(BaseModel):
    estado: Literal["sin_evidencia"]
    resumen: str = Field(min_length=1)


class SalidaSinEvidencia(BaseModel):
    respuesta: str = Field(min_length=1, max_length=4_000)
    citas: list[str] = Field(max_length=0)
    borrador: None
    total_coincidencias: Literal[0]
    modo: Literal["consulta", "borrador"]
    verificacion: VerificacionSinEvidencia


def validar_salida_catalogo(salida: dict) -> SalidaConversacional | SalidaSinEvidencia:
    verificacion = salida.get("verificacion")
    if isinstance(verificacion, dict) and verificacion.get("estado") == "sin_evidencia":
        return SalidaSinEvidencia.model_validate(salida)
    return SalidaConversacional.model_validate(salida)


class RepositorioCatalogo:
    """Un único objeto actual; el ETag impide sobrescribir cambios concurrentes."""

    def __init__(self, cliente, namespace: str, bucket: str):
        if not namespace.strip() or not bucket.strip():
            raise ValueError("Namespace y bucket son obligatorios.")
        self.cliente = cliente
        self.namespace = namespace
        self.bucket = bucket

    @classmethod
    def desde_entorno(cls):
        import os
        from src.config.oci_client import BUCKET_PREDETERMINADO, obtener_cliente

        cliente, namespace = obtener_cliente()
        return cls(cliente, namespace, os.getenv("OCI_BUCKET_NAME", BUCKET_PREDETERMINADO))

    def leer(self) -> tuple[CatalogoDiario | None, str | None]:
        try:
            respuesta = self.cliente.get_object(
                namespace_name=self.namespace, bucket_name=self.bucket, object_name=OBJETO,
            )
        except Exception as error:
            # Solo la ausencia del objeto es un catálogo todavía no publicado.
            if getattr(error, "status", None) == 404 and getattr(error, "code", None) == "ObjectNotFound":
                return None, None
            raise
        etag = respuesta.headers.get("etag")
        if not etag:
            raise ValueError("OCI no devolvió el ETag del catálogo.")
        catalogo = CatalogoDiario.model_validate_json(respuesta.data.content)
        fechas = [catalogo.intentado_en, catalogo.captura_en]
        fechas.extend(e.generado_en for e in catalogo.entradas.values())
        if any(f is not None and f.tzinfo is None for f in fechas):
            raise ValueError("Las fechas del catálogo requieren zona horaria.")
        for entrada in catalogo.entradas.values():
            validar_salida_catalogo(entrada.salida)
        return catalogo, etag

    def guardar(self, catalogo: CatalogoDiario, etag: str | None) -> None:
        condicion = {"if_match": etag} if etag else {"if_none_match": "*"}
        self.cliente.put_object(
            namespace_name=self.namespace, bucket_name=self.bucket, object_name=OBJETO,
            put_object_body=catalogo.model_dump_json().encode("utf-8"),
            content_type="application/json; charset=utf-8", **condicion,
        )


def fecha_programada(ahora: datetime):
    if ahora.tzinfo is None:
        raise ValueError("La hora de ejecución requiere zona horaria.")
    local = ahora.astimezone(ZONA)
    return local.date() if local.time() >= HORA else None


def actualizar_catalogo(
    repositorio: RepositorioCatalogo, *, ahora: datetime | None = None,
    plantillas: tuple[PlantillaDiaria, ...] = PLANTILLAS_DIARIAS,
    lector: Callable[[], Mapping] = leer_base,
    crear_agente: Callable[..., AgenteConversacional] = AgenteConversacional,
) -> CatalogoDiario | None:
    """Reintenta fallidas, no regenera éxitos del día ni hereda chats entre prompts."""
    ahora = ahora or datetime.now(timezone.utc)
    fecha = fecha_programada(ahora)
    if fecha is None:
        return None
    anterior, etag = repositorio.leer()
    if anterior and anterior.intentado_en > ahora:
        raise ValueError("El catálogo tiene una ejecución posterior a la solicitada.")
    ids = {p.id for p in plantillas}
    if len(ids) != len(plantillas) or not plantillas:
        raise ValueError("El catálogo requiere plantillas con identificadores únicos.")
    entradas = {
        k: v for k, v in (anterior.entradas.items() if anterior else []) if k in ids
    }
    pendientes = [
        p for p in plantillas
        if p.id not in entradas or entradas[p.id].generado_en.astimezone(ZONA).date() != fecha
        or entradas[p.id].prompt != p.prompt
    ]
    if not pendientes:
        return anterior
    catalogo = CatalogoDiario(
        intentado_en=ahora, captura_en=anterior.captura_en if anterior else None,
        entradas=entradas,
        fallos={k: v for k, v in (anterior.fallos.items() if anterior else []) if k in ids},
    )
    try:
        mensajes = adaptar_conjunto(lector())
        if not mensajes:
            raise ValueError("La captura no contiene mensajes consultables.")
    except Exception:
        _log.exception("Falló la captura para las plantillas diarias")
        for plantilla in pendientes:
            catalogo.fallos[plantilla.id] = "No se pudo obtener la información de la comunidad."
    else:
        catalogo.captura_en = ahora
        for plantilla in pendientes:
            try:
                # Cada prompt es una conversación independiente sobre la misma captura.
                salida = crear_agente(mensajes).consultar(
                    plantilla.prompt, hoy=fecha,
                    modo_verificacion="verificacion_automatica", modelo_respuesta="super",
                )
                validada = validar_salida_catalogo(salida)
                if plantilla.plataforma is None and validada.borrador is not None:
                    raise ValueError("Una plantilla analítica no debe generar una publicación.")
                if plantilla.id == "boletin" and not isinstance(validada, SalidaSinEvidencia):
                    if not validada.respuesta.startswith("## ") or len(validada.respuesta.split()) > 180:
                        raise ValueError("El boletín requiere titular y un máximo de 180 palabras.")
                if plantilla.plataforma and not isinstance(validada, SalidaSinEvidencia) and (
                    validada.borrador is None
                    or validada.borrador.plataforma != plantilla.plataforma
                ):
                    raise ValueError("No se generó contenido para el destino solicitado.")
            except Exception:
                _log.exception("Falló la plantilla diaria %s", plantilla.id)
                catalogo.fallos[plantilla.id] = "No se pudo preparar una nueva versión con evidencia."
            else:
                catalogo.entradas[plantilla.id] = EntradaDiaria(
                    nombre=plantilla.nombre, prompt=plantilla.prompt,
                    generado_en=ahora, salida=salida,
                )
                catalogo.fallos.pop(plantilla.id, None)
    # Un PUT reemplaza el documento entero: nunca se expone medio catálogo.
    # Un fallo de escritura o conflicto ETag se propaga; no se anuncia éxito.
    repositorio.guardar(catalogo, etag)
    return catalogo
