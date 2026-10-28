"""Flujo conversacional sobre resultados de Ciencia de Datos ya procesados."""

from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import asdict, dataclass, field, replace
from datetime import date, datetime, timezone
from functools import lru_cache
import json
import re
from typing import Annotated, Any, Literal
import unicodedata

from pydantic import BaseModel, Field, PrivateAttr, ValidationError

from src.agentes.contexto import dividir_evidencia, estimar_tokens, obtener_presupuesto_contexto
from src.agentes.consumo import estimar_entrada, limitar_consulta

from src.agentes.configuracion_ia import (
    PROVEEDOR_GEMINI,
    PROVEEDOR_NVIDIA_NIM,
    obtener_proveedor_generacion,
)
from src.agentes.modelo_ia import (
    invocar_modelo_con_fallback,
    obtener_modelo_generacion_estructurado,
)
from src.agentes.interpretacion import ErrorInterpretacion, PlanConsulta, interpretar_consulta
from src.agentes.observabilidad import config_ejecucion
from src.agentes.plataformas import PlataformaPublicacion, texto_publicacion
from src.agentes.prompts.conversacion import prompt_conversacion
from src.agentes.prompts.verificacion import prompt_verificacion
from src.datos.metadatos import valor_publico


MAX_MENSAJES = 50_000
MAX_CARACTERES_DATASET = 5_000_000
MAX_CARACTERES_METADATO = 250
LIMITE_CARACTERES_X = 280
MAX_HISTORIAL = 6
MAX_CARACTERES_CONSULTA = 1_000
TEMPERATURA_MINIMA = 0.0
TEMPERATURA_MAXIMA = 1.0
TOP_P_MINIMO = 0.1
TOP_P_MAXIMO = 1.0

# Estilos de redacción para borradores: (temperatura, top_p).
ESTILOS_REDACCION: dict[str, tuple[float, float]] = {
    "preciso": (0.0, 1.0),
    "equilibrado": (0.4, 0.9),
    "creativo": (0.8, 0.95),
}
MODELOS_RESPUESTA = {
    "super": "nvidia/nemotron-3.5-super-vl-120b-a12b",
    "lightning": "nvidia/nemotron-3.5-lightning-30b-a3b",
}

ModoVerificacion = Literal["prompt_estricto", "verificacion_automatica"]

_SENTIMIENTOS_INCLUIDOS = {
    "positivo": frozenset({"positivo", "muy_positivo"}),
    "negativo": frozenset({"negativo", "muy_negativo"}),
}
_TOKEN = re.compile(r"[^\W_]+", re.UNICODE)

class BorradorMarketing(BaseModel):
    plataforma: PlataformaPublicacion
    titulo: str = Field(min_length=1, max_length=180)
    contenido: str = Field(min_length=1, max_length=5_000)
    hashtags: list[Annotated[str, Field(pattern=r"^#[^\s#]+$")]] = Field(
        min_length=3, max_length=8,
        description="De 3 a 8 etiquetas con # inicial, sin espacios: #Comunidad.",
    )

class GrupoPregunta(BaseModel):
    duda: str = Field(min_length=1, max_length=500)
    citas: list[str] = Field(min_length=1)

class HallazgoCitado(BaseModel):
    afirmacion: str = Field(min_length=1)
    citas: list[str] = Field(min_length=1)


class SalidaConversacional(BaseModel):
    _procesamiento: dict = PrivateAttr(default_factory=dict)
    respuesta: str = Field(min_length=1)
    citas: list[str] = Field(
        min_length=1,
        description=(
            "Solo IDs exactos de la evidencia, por ejemplo msg-1. "
            "Nunca textos citados, autores ni explicaciones."
        ),
    )
    borrador: BorradorMarketing | None = None
    hallazgos: list[HallazgoCitado] = Field(
        default_factory=list,
        description="Hechos atómicos pertinentes, cada uno con sus fuentes exactas; obligatorio al extraer o consolidar lotes.",
    )
    grupos_preguntas: list[GrupoPregunta] = Field(
        default_factory=list,
        description=(
            "Si filtros.agrupar_preguntas es true, agrupa TODAS las preguntas de la "
            "evidencia. Cada grupo contiene una duda y los IDs únicos que la expresan. "
            "No incluyas conteos ni respuestas en duda. En otras tareas deja []."
        ),
    )


class AfirmacionVerificada(BaseModel):
    afirmacion: str = Field(min_length=1, max_length=500)
    respaldada: bool
    citas: list[str]
    respaldo_agregado: bool = Field(
        default=False,
        description="True solo si un agregado autorizado demuestra por completo la afirmación.",
    )


class SalidaVerificacion(BaseModel):
    afirmaciones: list[AfirmacionVerificada]
    resumen: str = Field(min_length=1, max_length=1_000)


@dataclass(frozen=True)
class FiltrosConsulta:
    sentimiento: str | None = None
    tipo_detectado: str | None = None
    tipos_detectados: list[str] = field(default_factory=list)
    agrupar_preguntas: bool = False
    listar_autores: bool = False
    campos_listado: list[str] = field(default_factory=list)
    fecha_desde: date | None = None
    fecha_hasta: date | None = None
    plataforma: str | None = None
    intencion: Literal["consulta", "borrador"] = "consulta"
    cantidad: int | None = None
    canal: str | None = None


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFD", texto.casefold())
    return "".join(
        caracter if unicodedata.category(caracter) != "Mn" else ""
        for caracter in texto
    ).replace("_", " ")


def _tokens(texto: str) -> set[str]:
    return set(_TOKEN.findall(_normalizar(texto)))


def _fecha_mensaje(valor: object) -> date | None:
    if not isinstance(valor, str) or not valor.strip():
        return None
    try:
        texto = valor.strip()
        if len(texto) == 10:
            return date.fromisoformat(texto)
        fecha = datetime.fromisoformat(texto.replace("Z", "+00:00"))
        if fecha.tzinfo is None:
            fecha = fecha.replace(tzinfo=timezone.utc)
        return fecha.astimezone(timezone.utc).date()
    except ValueError:
        return None


def _extraer_mensajes(datos: object) -> list[dict]:
    if isinstance(datos, list):
        mensajes = datos
    elif isinstance(datos, dict):
        if isinstance(datos.get("interacciones"), list):
            mensajes = datos["interacciones"]
        elif isinstance(datos.get("resultados"), list):
            mensajes = datos["resultados"]
        elif isinstance(datos.get("resultados_por_id"), dict):
            mensajes = list(datos["resultados_por_id"].values())
        else:
            raise ValueError(
                "Se esperaba una lista de interacciones o una salida DS con "
                "'interacciones' o 'resultados'."
            )
    else:
        raise ValueError("Los datos procesados deben ser una lista o un objeto DS.")

    if len(mensajes) > MAX_MENSAJES:
        raise ValueError(f"La conversación admite hasta {MAX_MENSAJES} mensajes.")

    salida = []
    ids = set()
    caracteres_totales = 0
    for indice, mensaje in enumerate(mensajes):
        if not isinstance(mensaje, dict):
            raise ValueError(f"El mensaje {indice} debe ser un objeto.")
        identificador = mensaje.get("id")
        texto = mensaje.get("texto")
        if (
            not isinstance(identificador, str)
            or not identificador.strip()
            or identificador != identificador.strip()
        ):
            raise ValueError(f"El mensaje {indice} requiere un id no vacío.")
        if identificador in ids:
            raise ValueError(f"El id de mensaje está duplicado: {identificador}.")
        if not isinstance(texto, str) or not texto.strip():
            raise ValueError(f"El mensaje {identificador} requiere texto no vacío.")
        if len(texto) > 50_000:
            raise ValueError(f"El mensaje {identificador} supera 50.000 caracteres.")
        caracteres_totales += len(texto)
        if caracteres_totales > MAX_CARACTERES_DATASET:
            raise ValueError(
                "El conjunto de datos supera el límite de 5.000.000 caracteres."
            )
        tipo_detectado = mensaje.get("tipo_detectado") or mensaje.get("tipo_original") or ""
        if not isinstance(tipo_detectado, str):
            tipo_detectado = ""
        elegible = mensaje.get("elegible_contenido")
        if elegible is not None and type(elegible) is not bool:
            raise ValueError(
                f"elegible_contenido debe ser booleano en el mensaje {identificador}."
            )
        ids.add(identificador)
        salida.append(
            {
                "id": identificador,
                "texto": texto,
                "autor": (
                    mensaje["autor"][:MAX_CARACTERES_METADATO]
                    if isinstance(mensaje.get("autor"), str)
                    else ""
                ),
                "canal": (
                    mensaje["canal"][:MAX_CARACTERES_METADATO]
                    if isinstance(mensaje.get("canal"), str)
                    else ""
                ),
                "origen": (
                    mensaje["origen"][:MAX_CARACTERES_METADATO]
                    if isinstance(mensaje.get("origen"), str)
                    else ""
                ),
                "fecha": mensaje.get("fecha") if isinstance(mensaje.get("fecha"), str) else "",
                "sentimiento": mensaje.get("sentimiento") if isinstance(mensaje.get("sentimiento"), str) else "",
                "tema_principal": mensaje.get("tema_principal") if isinstance(mensaje.get("tema_principal"), str) else "",
                "subtema": mensaje.get("subtema") if isinstance(mensaje.get("subtema"), str) else "",
                "tipo_detectado": tipo_detectado,
                "elegible_contenido": elegible,
            }
        )
        for campo in (
            "autor", "canal", "origen", "fecha", "sentimiento",
            "tema_principal", "subtema", "tipo_detectado",
        ):
            salida[-1][campo] = valor_publico(salida[-1][campo])
    return salida


class AgenteConversacional:
    """Asistente efímero; cada instancia mantiene una sesión de conversación."""

    def __init__(
        self,
        datos_procesados: object,
        *,
        generador: Callable[..., SalidaConversacional | dict] | None = None,
        verificador: Callable[..., SalidaVerificacion | dict] | None = None,
        interprete: Callable[..., PlanConsulta | dict] | None = None,
    ):
        self._mensajes = _extraer_mensajes(datos_procesados)
        self._generador = generador
        self._verificador = verificador
        self._interprete = interprete
        self._historial: list[dict[str, str]] = []
        self._ultimo_plan: PlanConsulta | None = None
        self._ultimo_borrador: dict | None = None
        self._indexar()

    def actualizar_datos(self, datos_procesados: object) -> None:
        """Cambia los mensajes consultables sin perder la conversación en curso."""
        self._mensajes = _extraer_mensajes(datos_procesados)
        self._indexar()

    def _indexar(self) -> None:
        self._vocabulario = {
            campo: sorted({
                mensaje[campo][:MAX_CARACTERES_METADATO]
                for mensaje in self._mensajes if mensaje[campo]
            })[:32]
            for campo in ("sentimiento", "tipo_detectado", "canal")
        }
        self._indice_invertido: dict[str, set[int]] = defaultdict(set)
        for indice, mensaje in enumerate(self._mensajes):
            documento = _tokens(
                " ".join(
                    str(mensaje[campo])
                    for campo in (
                        "texto",
                        "canal",
                        "origen",
                        "sentimiento",
                        "tema_principal",
                        "subtema",
                        "tipo_detectado",
                    )
                )
            )
            for token in documento:
                self._indice_invertido[token].add(indice)

    @property
    def historial(self) -> list[dict[str, str]]:
        """Devuelve el historial de esta instancia, nunca persistido en disco."""
        return [dict(turno) for turno in self._historial]

    @limitar_consulta
    def consultar(
        self,
        consulta: str,
        *,
        hoy: date | None = None,
        modo_verificacion: ModoVerificacion = "prompt_estricto",
        temperatura: float | None = None,
        top_p: float | None = None,
        modelo_respuesta: str | None = None,
    ) -> dict:
        """Responde una consulta sobre los datos procesados.

        `temperatura` y `top_p` ajustan la creatividad de la redacción y solo se
        aplican a borradores; los análisis y conteos siempre son deterministas.
        """
        if not isinstance(consulta, str) or not consulta.strip():
            raise ValueError("Escribe una consulta para el agente.")
        if modelo_respuesta is not None and modelo_respuesta not in MODELOS_RESPUESTA:
            raise ValueError("El modelo de respuesta seleccionado no es válido.")
        if modo_verificacion not in {
            "prompt_estricto",
            "verificacion_automatica",
        }:
            raise ValueError("El modo de verificación seleccionado no es válido.")
        if temperatura is not None and not (
            TEMPERATURA_MINIMA <= temperatura <= TEMPERATURA_MAXIMA
        ):
            raise ValueError(
                f"La temperatura debe estar entre {TEMPERATURA_MINIMA} y "
                f"{TEMPERATURA_MAXIMA}."
            )
        if top_p is not None and not (TOP_P_MINIMO <= top_p <= TOP_P_MAXIMO):
            raise ValueError(
                f"El top_p debe estar entre {TOP_P_MINIMO} y {TOP_P_MAXIMO}."
            )
        consulta = consulta.strip()
        if len(consulta) > MAX_CARACTERES_CONSULTA:
            raise ValueError(
                f"La consulta no puede superar {MAX_CARACTERES_CONSULTA} caracteres."
            )

        hoy = hoy or datetime.now(timezone.utc).date()
        plan = self._interpretar(consulta, hoy)
        intencion = plan.intencion
        if intencion != "consulta" and intencion != "borrador":
            respuesta = plan.respuesta
            salida = {
                "respuesta": respuesta,
                "citas": [],
                "borrador": None,
                "total_coincidencias": 0,
                "resumen": {},
                "filtros": _filtros_a_dict(FiltrosConsulta()),
                "modo": plan.intencion,
                "verificacion": {
                    "modo": modo_verificacion,
                    "estado": "no_aplica",
                    "resumen": "Esta interacción no requiere consultar los mensajes.",
                    "afirmaciones": [],
                },
            }
            self._guardar_turno(consulta, respuesta)
            return salida

        filtros = FiltrosConsulta(
            sentimiento=plan.sentimiento,
            tipo_detectado=plan.tipo_detectado,
            tipos_detectados=plan.tipos_detectados,
            agrupar_preguntas=plan.agrupar_preguntas,
            listar_autores=plan.listar_autores,
            campos_listado=list(plan.campos_listado),
            canal=plan.canal,
            fecha_desde=plan.fecha_desde,
            fecha_hasta=plan.fecha_hasta,
            plataforma=plan.plataforma,
            intencion=intencion,
            cantidad=plan.cantidad,
        )
        consulta_busqueda = " ".join(plan.terminos)

        encontrados = self._buscar(consulta_busqueda, filtros)
        hubo_no_elegibles = False
        if filtros.intencion == "borrador":
            elegibles = [
                mensaje
                for mensaje in encontrados
                if mensaje["elegible_contenido"] is not False
            ]
            hubo_no_elegibles = bool(encontrados) and not elegibles
            encontrados = elegibles

        if not encontrados:
            respuesta = self._explicar_sin_resultados(
                consulta_busqueda,
                filtros,
                hubo_no_elegibles,
            )
            salida = {
                "respuesta": respuesta,
                "citas": [],
                "borrador": None,
                "total_coincidencias": 0,
                "resumen": {},
                "filtros": _filtros_a_dict(filtros),
                "modo": filtros.intencion,
                "verificacion": {
                    "modo": modo_verificacion,
                    "estado": "sin_evidencia",
                    "resumen": "No se generó contenido porque no hubo coincidencias.",
                    "afirmaciones": [],
                },
            }
            self._guardar_turno(consulta, respuesta)
            self._ultimo_plan = plan
            return salida

        resumen = _resumir(encontrados, filtros)
        resumen["universo_total"] = len(self._mensajes)
        if filtros.listar_autores or filtros.campos_listado == ["autor"]:
            autores: dict[str, tuple[str, str]] = {}
            for mensaje in encontrados:
                autor = valor_publico(mensaje["autor"])
                if autor and autor.strip():
                    nombre = autor.strip()
                    autores.setdefault(nombre.casefold(), (nombre, mensaje["id"]))
            seleccion = list(autores.values())[:filtros.cantidad]
            resumen.update(
                total_autores=len(autores),
                mensajes_sin_autor=sum(
                    not (valor_publico(m["autor"]) or "").strip() for m in encontrados
                ),
                mensajes_enviados_al_modelo=0,
            )
            if seleccion:
                respuesta = f"Nombres distintos disponibles: {len(autores)}. Mostrando {len(seleccion)}."
                if filtros.cantidad and filtros.cantidad > len(autores):
                    respuesta += f" Pediste {filtros.cantidad}; no hay más nombres registrados en las coincidencias."
                respuesta += "\n\n" + "\n".join(
                    f"{i}. {nombre}" for i, (nombre, _) in enumerate(seleccion, 1)
                )
            else:
                respuesta = "Los mensajes encontrados no tienen autor registrado; no puedo listar nombres."
            salida = {
                "respuesta": respuesta,
                "autores": [nombre for nombre, _ in seleccion],
                "citas": [identificador for _, identificador in seleccion],
                "borrador": None,
                "total_coincidencias": len(encontrados),
                "resumen": resumen,
                "filtros": _filtros_a_dict(filtros),
                "modo": "consulta",
                "verificacion": {
                    "modo": modo_verificacion,
                    "estado": "no_aplica",
                    "resumen": "Listado calculado directamente de los autores registrados, sin redacción del modelo.",
                    "afirmaciones": [],
                },
            }
            self._guardar_turno(consulta, respuesta)
            self._ultimo_plan = plan
            return salida
        if filtros.campos_listado:
            campos_internos = {
                "tema": "tema_principal", "tipo": "tipo_detectado", "contenido_textual": "texto",
            }
            registros = []
            citas = []
            vistos = set()
            for mensaje in encontrados:
                fila = {
                    campo: valor_publico(mensaje[campos_internos.get(campo, campo)]) or None
                    for campo in filtros.campos_listado
                }
                if len(fila) == 1 and filtros.campos_listado[0] not in {"id", "contenido_textual"}:
                    valor = next(iter(fila.values()))
                    clave = valor.casefold() if isinstance(valor, str) else valor
                    if valor is None or clave in vistos:
                        continue
                    vistos.add(clave)
                registros.append(fila)
                citas.append(mensaje["id"])
            total = len(registros)
            registros, citas = registros[:filtros.cantidad], citas[:filtros.cantidad]
            respuesta = f"Resultados disponibles: {total}. Mostrando {len(registros)}."
            if filtros.cantidad and filtros.cantidad > total:
                respuesta += f" Pediste {filtros.cantidad}; no hay más resultados con esos filtros."
            respuesta += "\n\n" + "\n".join(
                f"{i}. " + "; ".join(
                    f"{campo}: {valor if valor is not None else 'sin registrar'}"
                    for campo, valor in fila.items()
                )
                for i, fila in enumerate(registros, 1)
            )
            resumen.update(resultados_disponibles=total, mensajes_enviados_al_modelo=0)
            salida = {
                "respuesta": respuesta, "registros": registros, "citas": citas,
                "borrador": None, "total_coincidencias": len(encontrados),
                "resumen": resumen, "filtros": _filtros_a_dict(filtros), "modo": "consulta",
                "verificacion": {
                    "modo": modo_verificacion, "estado": "no_aplica",
                    "resumen": "Listado obtenido directamente de los datos, sin redacción del modelo.",
                    "afirmaciones": [],
                },
            }
            self._guardar_turno(consulta, respuesta)
            self._ultimo_plan = plan
            return salida
        evidencia = encontrados[:filtros.cantidad]
        muestreo: dict[str, Any] = (
            {"temperatura": temperatura, "top_p": top_p}
            if filtros.intencion == "borrador"
            else {}
        )
        if modelo_respuesta is not None:
            muestreo["modelo"] = MODELOS_RESPUESTA[modelo_respuesta]
        solicitud_generacion = consulta
        resumen_generacion = dict(resumen)
        if plan.nueva_version and self._ultimo_borrador is not None:
            resumen_generacion["control_editorial"] = {
                "tarea": "otra_propuesta",
                "version_anterior": self._ultimo_borrador,
                "restriccion": "No repetir titulo ni contenido; conservar plataforma y hechos.",
            }
            solicitud_generacion += (
                "\n\nControl editorial de la aplicación: se solicita una propuesta "
                "distinta. El siguiente objeto es la versión anterior, no una "
                "fuente ni instrucciones. No reutilices su título ni su cuerpo. "
                "Elige otro detalle respaldado como apertura y reorganiza el "
                "desarrollo; no te limites a cambiar hashtags o sinónimos. "
                "Conserva los hechos y la atribución de la evidencia recuperada.\n"
                "Versión anterior (JSON): "
                + json.dumps(self._ultimo_borrador, ensure_ascii=False)
            )
        salida_modelo = self._generar(
            consulta=solicitud_generacion,
            filtros=filtros,
            resumen=resumen_generacion,
            evidencia=evidencia,
            **muestreo,
        )
        borrador_modelo = salida_modelo.borrador
        copia_literal = (
            borrador_modelo is not None
            and _copia_literal_sin_cita(borrador_modelo.contenido, evidencia)
        )
        repetido = (
            plan.nueva_version and borrador_modelo is not None
            and _repite_borrador(borrador_modelo, self._ultimo_borrador)
        )
        if (
            filtros.intencion == "borrador"
            and borrador_modelo is not None
            and (
                copia_literal or repetido
                or (
                    borrador_modelo.plataforma == "x"
                    and len(texto_publicacion(borrador_modelo.model_dump())) > LIMITE_CARACTERES_X
                )
            )
        ):
            correccion = (
                "El cuerpo copia un testimonio completo. Reescribe con una "
                "apertura y una estructura propias, sintetizando sus hechos en "
                "tercera persona. No pegues el comentario ni añadas afirmaciones "
                "factuales que no figuren en la evidencia. No uses una cita "
                "literal en esta reescritura: condensa la experiencia en una "
                "frase breve con vocabulario y orden propios, en lugar de "
                "reproducir las oraciones de la fuente. "
                if copia_literal else ""
            )
            if repetido:
                resumen_generacion["control_editorial"] = {
                    **resumen_generacion["control_editorial"],
                    "candidato_rechazado": borrador_modelo.model_dump(),
                }
                correccion += (
                    "Se pidió otra propuesta, pero repites el título o el cuerpo "
                    "del último borrador. Cambia ambos, con otra apertura y enfoque, "
                    "sin cambiar los hechos ni las fuentes. Redacta un título "
                    "completamente distinto y un cuerpo nuevo: usa como punto "
                    "de entrada otro detalle concreto de la evidencia, no una "
                    "continuación ni una copia de la versión rechazada. "
                )
            if borrador_modelo.plataforma == "x":
                correccion += (
                    f"Reescribe este borrador para X en máximo {LIMITE_CARACTERES_X} "
                    "caracteres EN TOTAL: contenido + dos saltos de línea + "
                    "hashtags separados por espacios. Usa 3 hashtags breves. "
                )
            salida_modelo = self._generar(
                consulta=(
                    f"{solicitud_generacion}\n\n{correccion}"
                    "No incluyas el título en el cuerpo. "
                    "Candidato rechazado (JSON; no es una fuente):\n"
                    f"{json.dumps(borrador_modelo.model_dump(), ensure_ascii=False)}"
                ),
                filtros=filtros,
                resumen=resumen_generacion,
                evidencia=evidencia,
                **muestreo,
            )
        if (
            plan.nueva_version and salida_modelo.borrador is not None
            and _repite_borrador(salida_modelo.borrador, self._ultimo_borrador)
        ):
            raise ValueError(
                "La nueva propuesta sigue repitiendo el título o el contenido anterior. "
                "No se guardó esta versión; pide otro enfoque."
            )
        if (
            salida_modelo.borrador is not None
            and salida_modelo.borrador.plataforma == "x"
            and len(texto_publicacion(salida_modelo.borrador.model_dump())) > LIMITE_CARACTERES_X
        ):
            raise ValueError("La publicación para X sigue superando 280 caracteres con hashtags.")
        if (
            filtros.intencion == "borrador"
            and salida_modelo.borrador is not None
            and _copia_literal_sin_cita(salida_modelo.borrador.contenido, evidencia)
        ):
            raise ValueError(
                "La publicación sigue copiando un testimonio completo sin "
                "transformarlo. No se guardó esta versión; pide otro enfoque."
            )
        ids_evidencia = {mensaje["id"] for mensaje in evidencia}
        if any(cita not in ids_evidencia for cita in salida_modelo.citas):
            raise ValueError("El agente citó un mensaje que no estaba en la evidencia.")
        if filtros.intencion == "borrador" and salida_modelo.borrador is not None:
            if salida_modelo.borrador.plataforma != filtros.plataforma:
                raise ValueError("La plataforma del borrador no coincide con la solicitud.")
        elif salida_modelo.borrador is not None:
            raise ValueError("El agente devolvió un borrador sin que se solicitara.")

        respuesta = salida_modelo.respuesta
        if filtros.agrupar_preguntas:
            if set(salida_modelo.citas) != ids_evidencia:
                raise ValueError("Las citas no cubren todas las preguntas recuperadas.")
            respuesta = _presentar_preguntas(salida_modelo.grupos_preguntas, ids_evidencia)
        borrador = (
            salida_modelo.borrador.model_dump()
            if salida_modelo.borrador is not None
            else None
        )
        verificacion = {
            "modo": modo_verificacion,
            "estado": (
                "borrador_no_generado"
                if borrador is None and filtros.intencion == "borrador"
                else "no_aplica" if borrador is None else "no_verificado"
            ),
            "resumen": (
                (
                    "Se solicitó un borrador, pero el modelo no lo generó."
                    if filtros.intencion == "borrador"
                    else "No se solicitó un borrador."
                )
                if borrador is None
                else "Se usó un prompt estricto; las afirmaciones no se contrastaron por separado."
            ),
            "afirmaciones": [],
        }
        if (
            borrador is not None
            and modo_verificacion == "verificacion_automatica"
        ):
            resultado_verificacion = self._verificar(
                borrador=borrador,
                evidencia=evidencia,
            )
            verificacion = _preparar_verificacion(
                resultado_verificacion,
                {mensaje["id"] for mensaje in evidencia},
            )
            if verificacion["estado"] != "verificado":
                correccion_factual = (
                    f"{consulta}\n\nRevisión factual de la aplicación: corrige o elimina "
                    "las afirmaciones sin respaldo. No añadas resultados, acciones ni "
                    "beneficios nuevos. Conserva la plataforma y usa solo estas fuentes. "
                    "Devuelve una publicación completa, no expliques la revisión.\n"
                    f"Borrador a corregir: {json.dumps(borrador, ensure_ascii=False)}\n"
                    f"Observaciones: {json.dumps(verificacion, ensure_ascii=False)}"
                )
                corregida = self._generar(
                    consulta=correccion_factual, filtros=filtros, resumen=resumen_generacion,
                    evidencia=evidencia, **muestreo,
                )
                _validar_correccion(
                    corregida, filtros, evidencia,
                    self._ultimo_borrador if plan.nueva_version else None,
                )
                assert corregida.borrador is not None
                borrador = corregida.borrador.model_dump()
                verificacion = _preparar_verificacion(
                    self._verificar(borrador=borrador, evidencia=evidencia),
                    ids_evidencia,
                )
                if verificacion["estado"] != "verificado":
                    raise ValueError(
                        "La publicación sigue conteniendo afirmaciones sin respaldo "
                        "tras la corrección factual. No se guardó ni habilitó para publicar."
                    )
                salida_modelo = corregida
                respuesta = corregida.respuesta
        if filtros.intencion == "consulta":
            verificacion = self._verificar_analisis(
                respuesta=respuesta, hallazgos=salida_modelo.hallazgos,
                evidencia=evidencia, resumen=resumen,
            )
        salida = {
            "respuesta": respuesta,
            "citas": salida_modelo.citas,
            "borrador": borrador,
            "total_coincidencias": len(encontrados),
            "resumen": resumen,
            "filtros": _filtros_a_dict(filtros),
            "modo": filtros.intencion,
            "verificacion": verificacion,
            "hallazgos": [hallazgo.model_dump() for hallazgo in salida_modelo.hallazgos],
        }
        resumen["procesamiento"] = salida_modelo._procesamiento
        if filtros.agrupar_preguntas:
            salida["grupos_preguntas"] = [
                grupo.model_dump() for grupo in salida_modelo.grupos_preguntas
            ]
        self._guardar_turno(consulta, respuesta, borrador)
        self._ultimo_plan = plan
        if borrador is not None:
            self._ultimo_borrador = dict(borrador)
        return salida

    def _verificar_analisis(
        self, *, respuesta: str, hallazgos: list[HallazgoCitado],
        evidencia: list[dict], resumen: dict,
    ) -> dict:
        agregados = {
            campo: valor for campo, valor in resumen.items()
            if campo in {
                "universo_total", "total_coincidencias", "cantidad_solicitada",
                "distribucion_sentimientos", "porcentaje_sentimientos",
                "distribucion_tipos", "porcentaje_tipos",
                "distribucion_canales", "porcentaje_canales",
                "distribucion_temas", "porcentaje_temas", "filtros",
            }
        }
        resultado = self._verificar(
            borrador={
                "tipo": "analisis",
                "respuesta": respuesta,
                "hallazgos_a_comprobar": [hallazgo.model_dump() for hallazgo in hallazgos],
            },
            evidencia=evidencia,
            agregados=agregados,
        )
        ids = {mensaje["id"] for mensaje in evidencia}
        if any(cita not in ids for a in resultado.afirmaciones for cita in a.citas):
            raise ValueError("La revisión del análisis citó fuentes ajenas. No se guardó la respuesta.")
        verificacion = _preparar_verificacion(resultado, ids, permitir_agregados=True)
        if verificacion["estado"] != "verificado":
            raise ValueError(
                "No se pudo comprobar el respaldo de todas las afirmaciones del análisis. "
                "No se mostró ni guardó la respuesta como válida."
            )
        verificacion["obligatoria"] = True
        verificacion["alcance"] = "texto_final_y_hallazgos"
        return verificacion

    def _interpretar(self, consulta: str, hoy: date) -> PlanConsulta:
        resultado = (self._interprete or interpretar_consulta)(
            consulta=consulta,
            hoy=hoy,
            historial=self.historial[-MAX_HISTORIAL:],
            consulta_anterior=(
                self._ultimo_plan.model_dump(mode="json")
                if self._ultimo_plan is not None else None
            ),
            vocabulario=self._vocabulario,
        )
        try:
            return PlanConsulta.model_validate(resultado)
        except ValidationError as error:
            raise ErrorInterpretacion(
                "No pude interpretar la solicitud de forma fiable. Intenta reformularla."
            ) from error

    def _buscar(
        self,
        consulta: str,
        filtros: FiltrosConsulta,
    ) -> list[dict]:
        terminos = _tokens(consulta)
        puntajes: Counter[int] = Counter()
        for termino in terminos:
            for indice in self._indice_invertido.get(termino, ()):
                puntajes[indice] += 1

        indices = set(puntajes)
        if not terminos:
            indices = set(range(len(self._mensajes)))

        sentimientos_validos = {
            _normalizar(valor)
            for valor in _SENTIMIENTOS_INCLUIDOS.get(
                filtros.sentimiento or "",
                frozenset({filtros.sentimiento or ""}),
            )
        }
        tipos = filtros.tipos_detectados or (
            [filtros.tipo_detectado] if filtros.tipo_detectado else []
        )
        tipos_validos = {_normalizar(tipo) for tipo in tipos}
        resultados = []
        for indice in indices:
            mensaje = self._mensajes[indice]
            if filtros.sentimiento and _normalizar(mensaje["sentimiento"]) not in sentimientos_validos:
                continue
            if tipos_validos and _normalizar(mensaje["tipo_detectado"]) not in tipos_validos:
                continue
            if filtros.canal and _normalizar(mensaje["canal"]) != _normalizar(filtros.canal):
                continue
            fecha = _fecha_mensaje(mensaje["fecha"])
            if filtros.fecha_desde and (fecha is None or fecha < filtros.fecha_desde):
                continue
            if filtros.fecha_hasta and (fecha is None or fecha > filtros.fecha_hasta):
                continue
            resultados.append((puntajes.get(indice, 0), indice, mensaje))

        resultados.sort(
            key=lambda item: (
                -item[0],
                # Con «positivo», los muy positivos aparecen primero («los mejores»).
                0 if _normalizar(item[2]["sentimiento"]) == "muy positivo" else 1,
                item[1],
            )
        )
        return [mensaje for _, _, mensaje in resultados]

    def _explicar_sin_resultados(
        self,
        consulta_busqueda: str,
        filtros: FiltrosConsulta,
        hubo_no_elegibles: bool,
    ) -> str:
        motivos = []
        terminos = _tokens(consulta_busqueda)
        sin_aparicion = sorted(t for t in terminos if t not in self._indice_invertido)
        if terminos and len(sin_aparicion) == len(terminos):
            motivos.append(
                "ningún mensaje menciona " + ", ".join(f"«{t}»" for t in sin_aparicion)
            )

        sin_filtros_texto = FiltrosConsulta()
        if filtros.sentimiento:
            total = len(self._buscar("", replace(sin_filtros_texto, sentimiento=filtros.sentimiento)))
            if total == 0:
                motivos.append(f"no hay mensajes con sentimiento {filtros.sentimiento}")
        if filtros.tipo_detectado or filtros.tipos_detectados:
            total = len(self._buscar("", replace(
                sin_filtros_texto, tipo_detectado=filtros.tipo_detectado,
                tipos_detectados=filtros.tipos_detectados,
            )))
            if total == 0:
                motivos.append(
                    f"no hay mensajes de tipo {filtros.tipo_detectado or ', '.join(filtros.tipos_detectados)}"
                )
        if filtros.canal:
            total = len(self._buscar("", replace(sin_filtros_texto, canal=filtros.canal)))
            if total == 0:
                motivos.append(f"no hay mensajes del canal {filtros.canal}")
        if filtros.fecha_desde or filtros.fecha_hasta:
            if not any(_fecha_mensaje(m["fecha"]) for m in self._mensajes):
                motivos.append("estos datos no tienen fechas, así que no puedo filtrar por período")
            else:
                motivos.append("no hay mensajes en el período indicado")
        if hubo_no_elegibles:
            motivos.append(
                "los mensajes que coinciden están marcados como no aptos para "
                "contenido de marketing"
            )
        if not motivos:
            motivos.append("la combinación de filtros y términos no coincide con ningún mensaje")

        sentimientos = Counter(m["sentimiento"] or "sin_clasificar" for m in self._mensajes)
        tipos = Counter(m["tipo_detectado"] or "sin_clasificar" for m in self._mensajes)

        def listar(conteos: Counter) -> str:
            return ", ".join(f"{clave} ({cantidad})" for clave, cantidad in conteos.most_common())

        return (
            "No encontré mensajes para esa solicitud porque "
            + "; ".join(motivos)
            + f".\n\nEn esta sesión hay {len(self._mensajes)} mensajes. "
            f"Sentimientos: {listar(sentimientos)}. Tipos: {listar(tipos)}. "
            "Prueba pidiendo por alguno de esos valores o por un tema que aparezca en los mensajes."
        )

    def _generar(
        self,
        *,
        consulta: str,
        filtros: FiltrosConsulta,
        resumen: dict,
        evidencia: list[dict],
        temperatura: float | None = None,
        top_p: float | None = None,
        modelo: str | None = None,
    ) -> SalidaConversacional:
        presupuesto = obtener_presupuesto_contexto()
        llamadas = 0
        maximo_estimado = 0

        def tokens(fuentes: list[dict], datos: dict) -> int:
            entrada = self._entrada_generacion(consulta, datos, fuentes)
            return _tokens_prompt(prompt_conversacion, entrada, SalidaConversacional)

        def invocar(fuentes: list[dict], datos: dict) -> SalidaConversacional:
            nonlocal llamadas, maximo_estimado
            parcial = datos["procesamiento"]["etapa"] == "extraccion_parcial"
            filtros_etapa = replace(filtros, intencion="consulta", plataforma=None) if parcial else filtros
            datos = {**datos, "filtros": _filtros_a_dict(filtros_etapa)}
            estimacion = tokens(fuentes, datos)
            if estimacion > presupuesto.entrada:
                raise ValueError("La llamada excede el presupuesto de contexto; no se envió al modelo.")
            resultado = self._invocar_generacion(
                consulta=consulta, filtros=filtros_etapa, resumen=datos, evidencia=fuentes,
                temperatura=temperatura, top_p=top_p, modelo=modelo,
            )
            if parcial and resultado.borrador is not None:
                raise ValueError("La extracción de un lote produjo un borrador en vez de hechos; no se consolidó.")
            permitidos = {m["id"] for m in fuentes}
            if any(cita not in permitidos for cita in resultado.citas):
                raise ValueError("El agente citó un mensaje que no estaba en la evidencia del lote.")
            if (parcial or datos["procesamiento"]["nivel"] > 0) and not filtros.agrupar_preguntas:
                if not resultado.hallazgos:
                    raise ValueError("La síntesis no vinculó sus hallazgos a fuentes; no se guardó una respuesta.")
            for hallazgo in resultado.hallazgos:
                if len(hallazgo.citas) != len(set(hallazgo.citas)) or any(
                    cita not in permitidos for cita in hallazgo.citas
                ):
                    raise ValueError("Un hallazgo contiene fuentes repetidas o ajenas al lote.")
            if resultado.hallazgos and not filtros.agrupar_preguntas:
                resultado.citas = list(dict.fromkeys(
                    cita for hallazgo in resultado.hallazgos for cita in hallazgo.citas
                ))
            if filtros.agrupar_preguntas:
                _presentar_preguntas(resultado.grupos_preguntas, permitidos)
                if set(resultado.citas) != permitidos:
                    raise ValueError("Las citas no cubren todas las preguntas del lote.")
            llamadas += 1
            maximo_estimado = max(maximo_estimado, estimacion)
            return resultado

        actuales = evidencia
        procedencia = {m["id"]: [m["id"]] for m in evidencia}
        nivel = 0
        lotes_fuente = 1
        while True:
            datos = {
                **resumen,
                "filtros": _filtros_a_dict(filtros),
                "procesamiento": {
                    "etapa": "respuesta_final" if nivel == 0 else "consolidacion",
                    "nivel": nivel,
                    "fuentes_son_sintesis": nivel > 0,
                },
            }
            if tokens(actuales, datos) <= presupuesto.entrada:
                resultado = invocar(actuales, datos)
                resultado.citas = list(dict.fromkeys(
                    original for cita in resultado.citas for original in procedencia[cita]
                ))
                for grupo in resultado.grupos_preguntas:
                    grupo.citas = list(dict.fromkeys(
                        original for cita in grupo.citas for original in procedencia[cita]
                    ))
                for hallazgo in resultado.hallazgos:
                    hallazgo.citas = list(dict.fromkeys(
                        original for cita in hallazgo.citas for original in procedencia[cita]
                    ))
                resultado._procesamiento = {
                    "registros_procesados": len(evidencia),
                    "lotes_fuente": lotes_fuente,
                    "llamadas_generacion": llamadas,
                    "niveles_consolidacion": nivel,
                    "cobertura_completa": True,
                    "tokens_entrada_estimados_maximos": maximo_estimado,
                    "presupuesto_entrada_tokens": presupuesto.entrada,
                    "reserva_salida_tokens": presupuesto.salida,
                    "estimacion": "bytes_utf8_con_margen",
                }
                return resultado

            datos["procesamiento"]["etapa"] = "extraccion_parcial"
            lotes = dividir_evidencia(
                actuales, lambda fuentes: tokens(fuentes, datos) <= presupuesto.entrada,
            )
            if nivel == 0:
                lotes_fuente = len(lotes)
            siguientes = []
            origenes = {}
            for lote in lotes:
                parcial = invocar(lote, datos)
                notas = (
                    [(grupo.duda, grupo.citas) for grupo in parcial.grupos_preguntas]
                    if filtros.agrupar_preguntas else [
                        (hallazgo.afirmacion, hallazgo.citas) for hallazgo in parcial.hallazgos
                    ]
                )
                for texto, citas in notas:
                    identificador = f"sintesis-{nivel}-{len(siguientes)}"
                    siguientes.append({"id": identificador, "texto": texto})
                    origenes[identificador] = list(dict.fromkeys(
                        original for cita in citas for original in procedencia[cita]
                    ))
            siguientes_datos = {
                **datos,
                "procesamiento": {
                    "etapa": "consolidacion", "nivel": nivel + 1, "fuentes_son_sintesis": True,
                },
            }
            if (
                estimar_tokens(siguientes) >= estimar_tokens(actuales)
                and tokens(siguientes, siguientes_datos) > presupuesto.entrada
            ):
                raise ValueError(
                    "La consolidación no redujo el contexto. No se devolvió una respuesta "
                    "parcial; acota la solicitud o revisa el presupuesto del servidor."
                )
            actuales, procedencia = siguientes, origenes
            nivel += 1

    def _entrada_generacion(self, consulta: str, resumen: dict, evidencia: list[dict]) -> dict:
        return {
            "consulta": consulta,
            "historial": json.dumps(self._historial[-MAX_HISTORIAL:], ensure_ascii=False),
            "resumen": json.dumps(resumen, ensure_ascii=False, default=str),
            "evidencia": json.dumps(evidencia, ensure_ascii=False),
        }

    def _invocar_generacion(
        self,
        *,
        consulta: str,
        filtros: FiltrosConsulta,
        resumen: dict,
        evidencia: list[dict],
        temperatura: float | None = None,
        top_p: float | None = None,
        modelo: str | None = None,
    ) -> SalidaConversacional:
        if self._generador is not None:
            resultado = self._generador(
                consulta=consulta,
                filtros=filtros,
                resumen=resumen,
                evidencia=evidencia,
                historial=self.historial[-MAX_HISTORIAL:],
            )
            return (
                resultado
                if isinstance(resultado, SalidaConversacional)
                else SalidaConversacional.model_validate(resultado)
            )

        entrada = self._entrada_generacion(consulta, resumen, evidencia)
        proveedor = PROVEEDOR_NVIDIA_NIM if modelo else obtener_proveedor_generacion()
        seleccion: dict[str, Any] = {"modelo_id": modelo} if modelo else {}
        seleccion["max_tokens"] = obtener_presupuesto_contexto().salida
        config = config_ejecucion(
            "agente_conversacional",
            intento=1,
            ruta="conversacion",
        )
        if proveedor == PROVEEDOR_NVIDIA_NIM:
            primario = lambda valor: _obtener_cadena(
                PROVEEDOR_NVIDIA_NIM, temperatura, top_p, **seleccion
            ).invoke(valor, config=config)
            respaldo = lambda valor: _obtener_cadena(
                PROVEEDOR_GEMINI, temperatura, top_p, max_tokens=seleccion["max_tokens"],
            ).invoke(valor, config=config)
            primario.__name__ = PROVEEDOR_NVIDIA_NIM
            respaldo.__name__ = PROVEEDOR_GEMINI
            resultado = invocar_modelo_con_fallback(
                entrada,
                primario=primario,
                respaldo=respaldo,
            )["resultado"]
        else:
            resultado = _obtener_cadena(proveedor, temperatura, top_p, **seleccion).invoke(
                entrada, config=config
            )
        return SalidaConversacional.model_validate(resultado)

    def _verificar(
        self,
        *,
        borrador: dict,
        evidencia: list[dict],
        agregados: dict | None = None,
    ) -> SalidaVerificacion:
        presupuesto = obtener_presupuesto_contexto()

        def cabe(fuentes: list[dict], objetivos: list[str] | None = None) -> bool:
            entrada = {
                "borrador": json.dumps(borrador, ensure_ascii=False),
                "evidencia": json.dumps(fuentes, ensure_ascii=False),
                "afirmaciones_objetivo": json.dumps(objetivos or [], ensure_ascii=False),
                "agregados": json.dumps(agregados or {}, ensure_ascii=False),
            }
            return _tokens_prompt(prompt_verificacion, entrada, SalidaVerificacion) <= presupuesto.entrada

        if cabe(evidencia):
            return self._invocar_verificacion(
                borrador=borrador, evidencia=evidencia,
                agregados=agregados,
            )
        if not cabe([]):
            raise ValueError("El borrador y las instrucciones de verificación exceden el presupuesto de contexto.")
        extraccion = self._invocar_verificacion(
            borrador=borrador, evidencia=[], agregados=agregados,
        )
        objetivos = list(dict.fromkeys(a.afirmacion for a in extraccion.afirmaciones))
        if not objetivos:
            raise ValueError("No se identificaron afirmaciones verificables para procesar por lotes.")
        lotes = dividir_evidencia(evidencia, lambda fuentes: cabe(fuentes, objetivos))
        afirmaciones = {
            texto: AfirmacionVerificada(afirmacion=texto, respaldada=False, citas=[])
            for texto in objetivos
        }
        for lote in lotes:
            verificacion = self._invocar_verificacion(
                borrador=borrador, evidencia=lote, afirmaciones_objetivo=objetivos,
                agregados=agregados,
            )
            if (
                len(verificacion.afirmaciones) != len(objetivos)
                or {a.afirmacion for a in verificacion.afirmaciones} != set(objetivos)
            ):
                raise ValueError("La verificación por lotes no evaluó las mismas afirmaciones.")
            permitidos = {m["id"] for m in lote}
            for afirmacion in verificacion.afirmaciones:
                if any(cita not in permitidos for cita in afirmacion.citas):
                    raise ValueError("El verificador citó una fuente ajena al lote.")
                if afirmacion.respaldada and (
                    afirmacion.citas or (agregados is not None and afirmacion.respaldo_agregado)
                ):
                    anterior = afirmaciones[afirmacion.afirmacion]
                    anterior.respaldada = True
                    anterior.citas = list(dict.fromkeys([*anterior.citas, *afirmacion.citas]))
                    anterior.respaldo_agregado |= afirmacion.respaldo_agregado and agregados is not None
        return SalidaVerificacion(
            afirmaciones=list(afirmaciones.values()),
            resumen=(
                f"Se contrastaron las mismas afirmaciones contra {len(lotes)} lotes. "
                "Solo se marca respaldo cuando una fuente lo demuestra; una afirmación "
                "que requiera combinar fragmentos puede necesitar revisión."
            ),
        )

    def _invocar_verificacion(
        self,
        *,
        borrador: dict,
        evidencia: list[dict],
        afirmaciones_objetivo: list[str] | None = None,
        agregados: dict | None = None,
    ) -> SalidaVerificacion:
        if self._verificador is not None:
            resultado = self._verificador(
                borrador=borrador,
                evidencia=evidencia,
                **({"agregados": agregados} if agregados is not None else {}),
                **(
                    {"afirmaciones_objetivo": afirmaciones_objetivo}
                    if afirmaciones_objetivo is not None else {}
                ),
            )
            return (
                resultado
                if isinstance(resultado, SalidaVerificacion)
                else SalidaVerificacion.model_validate(resultado)
            )

        entrada = {
            "borrador": json.dumps(borrador, ensure_ascii=False),
            "evidencia": json.dumps(evidencia, ensure_ascii=False),
            "afirmaciones_objetivo": json.dumps(afirmaciones_objetivo or [], ensure_ascii=False),
            "agregados": json.dumps(agregados or {}, ensure_ascii=False),
        }
        proveedor = obtener_proveedor_generacion()
        max_tokens = obtener_presupuesto_contexto().salida
        cadena = _obtener_cadena_verificacion(proveedor, max_tokens=max_tokens)
        config = config_ejecucion(
            "verificar_borrador",
            intento=1,
            ruta="conversacion",
        )
        if proveedor == PROVEEDOR_NVIDIA_NIM:
            primario = lambda valor: _obtener_cadena_verificacion(
                PROVEEDOR_NVIDIA_NIM, max_tokens=max_tokens,
            ).invoke(valor, config=config)
            respaldo = lambda valor: _obtener_cadena_verificacion(
                PROVEEDOR_GEMINI, max_tokens=max_tokens,
            ).invoke(valor, config=config)
            primario.__name__ = PROVEEDOR_NVIDIA_NIM
            respaldo.__name__ = PROVEEDOR_GEMINI
            resultado = invocar_modelo_con_fallback(
                entrada,
                primario=primario,
                respaldo=respaldo,
            )["resultado"]
        else:
            resultado = cadena.invoke(entrada, config=config)
        return SalidaVerificacion.model_validate(resultado)

    def _guardar_turno(
        self,
        consulta: str,
        respuesta: str,
        borrador: dict | None = None,
    ) -> None:
        if borrador is not None:
            # Permite seguimientos como «hazlo más corto» sobre el último borrador.
            respuesta = (
                f"{respuesta}\n[Borrador para {borrador['plataforma']}] "
                f"{borrador['titulo']}\n{borrador['contenido']}\n"
                f"{' '.join(borrador['hashtags'])}"
            )
        self._historial.extend(
            [
                {"rol": "usuario", "contenido": consulta[:MAX_CARACTERES_CONSULTA]},
                {"rol": "asistente", "contenido": respuesta[:4_000]},
            ]
        )
        del self._historial[:-MAX_HISTORIAL * 2]


def _filtros_a_dict(filtros: FiltrosConsulta) -> dict:
    valores = asdict(filtros)
    for campo in ("fecha_desde", "fecha_hasta"):
        if valores[campo] is not None:
            valores[campo] = valores[campo].isoformat()
    return valores


def _presentar_preguntas(grupos: list[GrupoPregunta], ids_evidencia: set[str]) -> str:
    vistos: set[str] = set()
    lineas = []
    for grupo in grupos:
        citas = set(grupo.citas)
        if len(citas) != len(grupo.citas) or not citas <= ids_evidencia:
            raise ValueError("Los grupos de preguntas contienen fuentes repetidas o ajenas.")
        vistos.update(citas)
        frecuencia = f"{len(citas)} mensajes" if len(citas) > 1 else "1 mensaje"
        lineas.append(f"- {grupo.duda} — {frecuencia}.")
    if vistos != ids_evidencia:
        raise ValueError("Los grupos no cubren todas las preguntas recuperadas.")
    repetidos = sum(len(grupo.citas) > 1 for grupo in grupos)
    return (
        f"## Dudas de la comunidad\n\n"
        f"En la muestra recuperada hay {len(vistos)} mensajes, agrupados en "
        f"{len(grupos)} dudas. Grupos con más de un mensaje: {repetidos}.\n\n"
        + "\n".join(lineas)
        + "\n\nConsulta las referencias de cada duda en el explorador de fuentes "
        "de la aplicación."
        + "\n\nEste resumen identifica preguntas; no propone respuestas sin contrastarlas "
        "por separado con fuentes."
    )


def _repite_borrador(borrador: BorradorMarketing, anterior: dict | None) -> bool:
    if anterior is None:
        return False
    return any(
        " ".join(_normalizar(getattr(borrador, campo)).split())
        == " ".join(_normalizar(anterior[campo]).split())
        for campo in ("titulo", "contenido")
    )


def _validar_correccion(
    salida: SalidaConversacional,
    filtros: FiltrosConsulta,
    evidencia: list[dict],
    anterior: dict | None,
) -> None:
    borrador = salida.borrador
    if borrador is None:
        raise ValueError("La corrección factual no produjo una publicación; no se guardó.")
    if borrador.plataforma != filtros.plataforma:
        raise ValueError("La plataforma de la corrección no coincide con la solicitud.")
    ids = {mensaje["id"] for mensaje in evidencia}
    if not salida.citas or any(cita not in ids for cita in salida.citas):
        raise ValueError("Las citas de la corrección no corresponden a la evidencia.")
    if _copia_literal_sin_cita(borrador.contenido, evidencia):
        raise ValueError("La corrección sigue copiando un testimonio completo.")
    if borrador.plataforma == "x" and len(texto_publicacion(borrador.model_dump())) > LIMITE_CARACTERES_X:
        raise ValueError("La corrección para X sigue superando 280 caracteres con hashtags.")
    if _repite_borrador(borrador, anterior):
        raise ValueError("La corrección sigue repitiendo el título o el contenido anterior.")


def _copia_literal_sin_cita(contenido: str, evidencia: list[dict]) -> bool:
    cuerpo = " ".join(contenido.casefold().split())
    for mensaje in evidencia:
        texto = " ".join(mensaje["texto"].casefold().split())
        # Los hechos breves y las citas delimitadas no equivalen a pegar un post.
        if len(texto) < 80 or texto not in cuerpo:
            continue
        if not any(
            f"{inicio}{texto}{fin}" in cuerpo
            for inicio, fin in (('"', '"'), ("«", "»"), ("“", "”"))
        ):
            return True
    return False


def _preparar_verificacion(
    verificacion: SalidaVerificacion,
    ids_evidencia: set[str],
    *,
    permitir_agregados: bool = False,
) -> dict:
    afirmaciones = []
    for afirmacion in verificacion.afirmaciones:
        citas_validas = [
            cita for cita in afirmacion.citas if cita in ids_evidencia
        ]
        respaldada = afirmacion.respaldada and (
            bool(citas_validas) or (permitir_agregados and afirmacion.respaldo_agregado)
        )
        afirmaciones.append(
            {
                "afirmacion": afirmacion.afirmacion,
                "respaldada": respaldada,
                "citas": citas_validas,
                **({"respaldo_agregado": afirmacion.respaldo_agregado} if permitir_agregados else {}),
            }
        )
    todas_respaldadas = bool(afirmaciones) and all(
        afirmacion["respaldada"] for afirmacion in afirmaciones
    )
    return {
        "modo": "verificacion_automatica",
        "estado": "verificado" if todas_respaldadas else "requiere_revision",
        "resumen": verificacion.resumen,
        "afirmaciones": afirmaciones,
    }


def _resumir(mensajes: list[dict], filtros: FiltrosConsulta) -> dict:
    sentimientos = Counter(
        m["sentimiento"] or "sin_clasificar" for m in mensajes
    )
    tipos = Counter(
        m["tipo_detectado"] or "sin_clasificar" for m in mensajes
    )
    canales = Counter(
        m["canal"] or "sin_clasificar" for m in mensajes
    )
    temas = Counter(
        m["tema_principal"] or "sin_clasificar" for m in mensajes
    )

    def porcentajes(conteos: Counter) -> dict[str, float]:
        return {
            clave: round(cantidad * 100 / len(mensajes), 1)
            for clave, cantidad in conteos.items()
        }

    resumen = {
        "total_coincidencias": len(mensajes),
        "distribucion_sentimientos": dict(sentimientos),
        "porcentaje_sentimientos": porcentajes(sentimientos),
        "distribucion_tipos": dict(tipos),
        "porcentaje_tipos": porcentajes(tipos),
        "distribucion_canales": dict(canales),
        "porcentaje_canales": porcentajes(canales),
        "distribucion_temas": dict(temas),
        "porcentaje_temas": porcentajes(temas),
        "filtros": _filtros_a_dict(filtros),
    }
    if filtros.cantidad:
        resumen["cantidad_solicitada"] = filtros.cantidad
    resumen["mensajes_enviados_al_modelo"] = (
        min(len(mensajes), filtros.cantidad) if filtros.cantidad is not None else len(mensajes)
    )
    return resumen


def _tokens_prompt(prompt, entrada: dict, esquema: type[BaseModel]) -> int:
    return estimar_entrada(prompt.format_messages(**entrada), esquema.model_json_schema())


@lru_cache(maxsize=32)
def _obtener_cadena(
    proveedor: str,
    temperatura: float | None = None,
    top_p: float | None = None,
    modelo_id: str | None = None,
    max_tokens: int = 4096,
):
    muestreo: dict[str, Any] = {
        clave: valor
        for clave, valor in (("temperatura", temperatura), ("top_p", top_p))
        if valor is not None
    }
    if modelo_id is not None:
        muestreo["modelo"] = modelo_id
    modelo = obtener_modelo_generacion_estructurado(
        SalidaConversacional,
        proveedor=proveedor,
        ruta="conversacion",
        max_tokens=max_tokens,
        **muestreo,
    )
    return prompt_conversacion | modelo


@lru_cache(maxsize=8)
def _obtener_cadena_verificacion(proveedor: str, max_tokens: int = 4096):
    modelo = obtener_modelo_generacion_estructurado(
        SalidaVerificacion,
        proveedor=proveedor,
        ruta="conversacion",
        modelo=MODELOS_RESPUESTA["super"] if proveedor == PROVEEDOR_NVIDIA_NIM else None,
        max_tokens=max_tokens,
    )
    return prompt_verificacion | modelo
