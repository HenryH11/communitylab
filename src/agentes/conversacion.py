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

from pydantic import BaseModel, Field, ValidationError

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


MAX_MENSAJES = 50_000
MAX_CARACTERES_DATASET = 5_000_000
MAX_CARACTERES_METADATO = 250
MAX_COINCIDENCIAS = 8
MAX_EVIDENCIA_LISTADO = 20
MAX_EVIDENCIA_X = 3
LIMITE_CARACTERES_X = 280
MAX_HISTORIAL = 6
MAX_CARACTERES_CONSULTA = 1_000
MAX_CARACTERES_MENSAJE = 1_200
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
    citas: list[str] = Field(min_length=1, max_length=MAX_EVIDENCIA_LISTADO)


class SalidaConversacional(BaseModel):
    respuesta: str = Field(min_length=1, max_length=4_000)
    citas: list[str] = Field(
        min_length=1, max_length=MAX_EVIDENCIA_LISTADO,
        description=(
            "Solo IDs exactos de la evidencia, por ejemplo msg-1. "
            "Nunca textos citados, autores ni explicaciones."
        ),
    )
    borrador: BorradorMarketing | None = None
    grupos_preguntas: list[GrupoPregunta] = Field(
        default_factory=list, max_length=MAX_EVIDENCIA_LISTADO,
        description=(
            "Si filtros.agrupar_preguntas es true, agrupa TODAS las preguntas de la "
            "evidencia. Cada grupo contiene una duda y los IDs únicos que la expresan. "
            "No incluyas conteos ni respuestas en duda. En otras tareas deja []."
        ),
    )


class AfirmacionVerificada(BaseModel):
    afirmacion: str = Field(min_length=1, max_length=500)
    respaldada: bool
    citas: list[str] = Field(max_length=MAX_COINCIDENCIAS)


class SalidaVerificacion(BaseModel):
    afirmaciones: list[AfirmacionVerificada] = Field(max_length=30)
    resumen: str = Field(min_length=1, max_length=1_000)


@dataclass(frozen=True)
class FiltrosConsulta:
    sentimiento: str | None = None
    tipo_detectado: str | None = None
    tipos_detectados: list[str] = field(default_factory=list)
    agrupar_preguntas: bool = False
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
            canal=plan.canal,
            fecha_desde=plan.fecha_desde,
            fecha_hasta=plan.fecha_hasta,
            plataforma=plan.plataforma,
            intencion=intencion,
            cantidad=plan.cantidad,
        )
        consulta_busqueda = " ".join(plan.terminos)
        self._ultimo_plan = plan

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
            return salida

        resumen = _resumir(encontrados, filtros)
        resumen["universo_total"] = len(self._mensajes)
        evidencia = encontrados[:_limite_evidencia(filtros)]
        muestreo: dict[str, Any] = (
            {"temperatura": temperatura, "top_p": top_p}
            if filtros.intencion == "borrador"
            else {}
        )
        if modelo_respuesta is not None:
            muestreo["modelo"] = MODELOS_RESPUESTA[modelo_respuesta]
        salida_modelo = self._generar(
            consulta=consulta,
            filtros=filtros,
            resumen=resumen,
            evidencia=_evidencia_acotada(evidencia),
            **muestreo,
        )
        borrador_modelo = salida_modelo.borrador
        copia_literal = (
            borrador_modelo is not None
            and _copia_literal_sin_cita(borrador_modelo.contenido, evidencia)
        )
        if (
            filtros.intencion == "borrador"
            and borrador_modelo is not None
            and (
                copia_literal
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
                "factuales que no figuren en la evidencia. "
                if copia_literal else ""
            )
            if borrador_modelo.plataforma == "x":
                correccion += (
                    f"Reescribe este borrador para X en máximo {LIMITE_CARACTERES_X} "
                    "caracteres EN TOTAL: contenido + dos saltos de línea + "
                    "hashtags separados por espacios. Usa 3 hashtags breves. "
                )
            salida_modelo = self._generar(
                consulta=(
                    f"{consulta}\n\n{correccion}"
                    "No incluyas el título en el cuerpo. Texto anterior:\n"
                    f"{texto_publicacion(borrador_modelo.model_dump())}"
                ),
                filtros=filtros,
                resumen=resumen,
                evidencia=_evidencia_acotada(evidencia),
                **muestreo,
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
                evidencia=_evidencia_acotada(evidencia),
            )
            verificacion = _preparar_verificacion(
                resultado_verificacion,
                {mensaje["id"] for mensaje in evidencia},
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
        }
        if filtros.agrupar_preguntas:
            salida["grupos_preguntas"] = [
                grupo.model_dump() for grupo in salida_modelo.grupos_preguntas
            ]
        self._guardar_turno(consulta, respuesta, borrador)
        return salida

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

        entrada = {
            "consulta": consulta,
            "historial": json.dumps(
                self._historial[-MAX_HISTORIAL:],
                ensure_ascii=False,
            ),
            "resumen": json.dumps(resumen, ensure_ascii=False, default=str),
            "evidencia": json.dumps(
                _evidencia_acotada(evidencia),
                ensure_ascii=False,
            ),
        }
        proveedor = PROVEEDOR_NVIDIA_NIM if modelo else obtener_proveedor_generacion()
        seleccion = {"modelo_id": modelo} if modelo else {}
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
                PROVEEDOR_GEMINI, temperatura, top_p
            ).invoke(valor, config=config)
            primario.__name__ = PROVEEDOR_NVIDIA_NIM
            respaldo.__name__ = PROVEEDOR_GEMINI
            resultado = invocar_modelo_con_fallback(
                entrada,
                primario=primario,
                respaldo=respaldo,
            )["resultado"]
        else:
            resultado = _obtener_cadena(proveedor, temperatura, top_p).invoke(
                entrada, config=config
            )
        return SalidaConversacional.model_validate(resultado)

    def _verificar(
        self,
        *,
        borrador: dict,
        evidencia: list[dict],
    ) -> SalidaVerificacion:
        if self._verificador is not None:
            resultado = self._verificador(
                borrador=borrador,
                evidencia=evidencia,
            )
            return (
                resultado
                if isinstance(resultado, SalidaVerificacion)
                else SalidaVerificacion.model_validate(resultado)
            )

        entrada = {
            "borrador": json.dumps(borrador, ensure_ascii=False),
            "evidencia": json.dumps(evidencia, ensure_ascii=False),
        }
        proveedor = obtener_proveedor_generacion()
        cadena = _obtener_cadena_verificacion(proveedor)
        config = config_ejecucion(
            "verificar_borrador",
            intento=1,
            ruta="conversacion",
        )
        if proveedor == PROVEEDOR_NVIDIA_NIM:
            primario = lambda valor: _obtener_cadena_verificacion(
                PROVEEDOR_NVIDIA_NIM
            ).invoke(valor, config=config)
            respaldo = lambda valor: _obtener_cadena_verificacion(
                PROVEEDOR_GEMINI
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
        if len(citas) != len(grupo.citas) or vistos & citas or not citas <= ids_evidencia:
            raise ValueError("Los grupos de preguntas contienen fuentes repetidas o ajenas.")
        vistos.update(citas)
        frecuencia = f"{len(citas)} mensajes" if len(citas) > 1 else "1 mensaje"
        lineas.append(f"- {grupo.duda} — {frecuencia}. Fuentes: {', '.join(grupo.citas)}.")
    if vistos != ids_evidencia:
        raise ValueError("Los grupos no cubren todas las preguntas recuperadas.")
    repetidos = sum(len(grupo.citas) > 1 for grupo in grupos)
    return (
        f"## Dudas de la comunidad\n\n"
        f"En la muestra recuperada hay {len(vistos)} mensajes, agrupados en "
        f"{len(grupos)} dudas. Grupos con más de un mensaje: {repetidos}.\n\n"
        + "\n".join(lineas)
        + "\n\nEste resumen identifica preguntas; no propone respuestas sin contrastarlas "
        "por separado con fuentes."
    )


def _evidencia_acotada(mensajes: list[dict]) -> list[dict]:
    """Limita el texto enviado al modelo sin perderlo en el índice local."""
    return [
        {
            **mensaje,
            "texto": mensaje["texto"][:MAX_CARACTERES_MENSAJE],
        }
        for mensaje in mensajes
    ]


def _copia_literal_sin_cita(contenido: str, evidencia: list[dict]) -> bool:
    cuerpo = " ".join(contenido.casefold().split())
    for mensaje in _evidencia_acotada(evidencia):
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
) -> dict:
    afirmaciones = []
    for afirmacion in verificacion.afirmaciones:
        citas_validas = [
            cita for cita in afirmacion.citas if cita in ids_evidencia
        ]
        respaldada = afirmacion.respaldada and bool(citas_validas)
        afirmaciones.append(
            {
                "afirmacion": afirmacion.afirmacion,
                "respaldada": respaldada,
                "citas": citas_validas,
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
        resumen["mensajes_enviados_al_modelo"] = min(
            len(mensajes), _limite_evidencia(filtros)
        )
    return resumen


def _limite_evidencia(filtros: FiltrosConsulta) -> int:
    limite = min(filtros.cantidad, MAX_EVIDENCIA_LISTADO) if filtros.cantidad else (
        MAX_EVIDENCIA_LISTADO if filtros.tipos_detectados or filtros.agrupar_preguntas
        else MAX_COINCIDENCIAS
    )
    if filtros.intencion == "borrador" and filtros.plataforma == "x":
        return min(limite, MAX_EVIDENCIA_X)
    return limite


@lru_cache(maxsize=32)
def _obtener_cadena(
    proveedor: str,
    temperatura: float | None = None,
    top_p: float | None = None,
    modelo_id: str | None = None,
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
        **muestreo,
    )
    return prompt_conversacion | modelo


@lru_cache(maxsize=4)
def _obtener_cadena_verificacion(proveedor: str):
    modelo = obtener_modelo_generacion_estructurado(
        SalidaVerificacion,
        proveedor=proveedor,
        ruta="conversacion",
        modelo=MODELOS_RESPUESTA["super"] if proveedor == PROVEEDOR_NVIDIA_NIM else None,
    )
    return prompt_verificacion | modelo
