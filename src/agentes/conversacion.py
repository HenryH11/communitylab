"""Flujo conversacional sobre resultados de Ciencia de Datos ya procesados."""

from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
import json
import re
from typing import Literal
import unicodedata

from pydantic import BaseModel, Field, field_validator

from src.agentes.configuracion_ia import (
    PROVEEDOR_GEMINI,
    PROVEEDOR_NVIDIA_NIM,
    obtener_proveedor_generacion,
)
from src.agentes.modelo_ia import (
    invocar_modelo_con_fallback,
    obtener_modelo_generacion_estructurado,
)
from src.agentes.observabilidad import config_ejecucion
from src.agentes.prompts.conversacion import prompt_conversacion
from src.agentes.prompts.verificacion import prompt_verificacion


MAX_MENSAJES = 50_000
MAX_CARACTERES_DATASET = 5_000_000
MAX_CARACTERES_METADATO = 250
MAX_COINCIDENCIAS = 8
MAX_HISTORIAL = 6
MAX_CARACTERES_CONSULTA = 1_000
MAX_CARACTERES_MENSAJE = 1_200

ModoVerificacion = Literal["prompt_estricto", "verificacion_automatica"]

_PALABRAS_VACIAS = frozenset(
    """
    a al algo ante aqui asi con como cual cuales cuando cuanto de del desde
    donde dos e el ella en entre era es esa ese eso esta este esto fue ha hay
    la las le les lo los mas me mi muy no nos o para pero por porque que quien
    se si sin sobre su sus te tiene un una uno y ya the a an and are as at be
    by for from how i in is it of on or that the this to was were what when
    where which with about show find tell me please
    los las una unos unas del al eso esa este esta post posts publicacion
    publicaciones mensaje mensajes comunidad datos dato mensajes
    opiniones opinion cuantos cuantas hubo resumen sentimiento sentimientos
    escribe escribir crea crear genera generar redacta redactar prepara preparar
    hazme haz write create draft positive positives negative negatives neutral
    neutrals sentiment yesterday today last week days past very highly
    ultimo ultimos ultima ultimas ayer hoy semana dias
    analytics analysis distribution count counts many happened topic topics
    frequent frecuencia distribución analitica analiticas cuantos cuantas
    which were top most common comunes principales dominante predominante
    theme themes topics tema temas qué cuál cuales cual
    """.split()
)
_TOKEN = re.compile(r"[^\W_]+", re.UNICODE)

_SINONIMOS_SENTIMIENTO = {
    "muy_positivo": (
        "muy positivo", "muy positiva", "muy positivos", "muy positivas",
        "very positive", "highly positive",
    ),
    "positivo": ("positivo", "positiva", "positivos", "positivas", "positive", "positives"),
    "neutral": ("neutral", "neutro", "neutra", "neutrales", "neutrals"),
    "negativo": ("negativo", "negativa", "negativos", "negativas", "negative", "negatives"),
    "muy_negativo": (
        "muy negativo", "muy negativa", "muy negativos", "muy negativas",
        "very negative", "highly negative",
    ),
}
_SINONIMOS_TIPO = {
    "testimonio": ("testimonio", "testimonios", "experiencia", "experiencias", "testimonial", "testimonials"),
    "pregunta_tecnica": (
        "pregunta técnica", "preguntas técnicas", "duda técnica", "dudas técnicas",
        "technical question", "technical questions",
    ),
    "pregunta_programa": (
        "pregunta del programa", "preguntas del programa", "program question",
        "program questions",
    ),
    "feedback": ("feedback", "retroalimentación", "sugerencia", "sugerencias"),
    "comentario": ("comentario", "comentarios"),
}
_PLATAFORMAS = {
    "linkedin": ("linkedin",),
    "instagram": ("instagram",),
    "x": ("twitter", "x"),
}
_SOLICITUD_BORRADOR = re.compile(
    r"\b(?:hazme|haz|crea|crear|genera|generar|redacta|redactar|"
    r"escribe|escribir|prepara|preparar|draft me|write me|create me)\b",
    re.IGNORECASE,
)
_SEGUIMIENTO = re.compile(
    r"^\s*(?:y|también|tambien|ahora|solo|sólo|qué tal|que tal|"
    r"¿?y\s+(?:los|las|el|la)|and|also|what about|only)\b",
    re.IGNORECASE,
)
_SOLICITUD_CODIGO = re.compile(
    r"\b(?:write|create|build|debug|fix|program|escribe|crea|construye|"
    r"depura|corrige|programa)\b.{0,50}\b(?:code|codigo|script|function|"
    r"funcion|app|application|api)\b|"
    r"\b(?:code|codigo|script|function|funcion|app|application|api)\b"
    r".{0,50}\b(?:write|create|build|debug|fix|escribe|crea|construye|"
    r"depura|corrige|programa)\b",
    re.IGNORECASE,
)
_SOLICITUD_ACTUALIDAD_EXTERNA = re.compile(
    r"\b(?:who is|current|latest|quien es|actual|actualmente|hoy|ahora)\b"
    r".{0,50}\b(?:president|presidente|election|eleccion|politic|politica)\b",
    re.IGNORECASE,
)


class BorradorMarketing(BaseModel):
    plataforma: Literal["linkedin", "instagram", "x"]
    titulo: str = Field(min_length=1, max_length=180)
    contenido: str = Field(min_length=1, max_length=5_000)
    hashtags: list[str] = Field(min_length=3, max_length=8)

    @field_validator("hashtags")
    @classmethod
    def validar_hashtags(cls, valores: list[str]) -> list[str]:
        if any(not valor.startswith("#") or len(valor) < 2 for valor in valores):
            raise ValueError("Cada hashtag debe comenzar con # y tener contenido.")
        return valores


class SalidaConversacional(BaseModel):
    respuesta: str = Field(min_length=1, max_length=4_000)
    citas: list[str] = Field(min_length=1, max_length=MAX_COINCIDENCIAS)
    borrador: BorradorMarketing | None = None


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
    fecha_desde: date | None = None
    fecha_hasta: date | None = None
    plataforma: str | None = None
    intencion: Literal["consulta", "borrador"] = "consulta"


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFD", texto.casefold())
    return "".join(
        caracter if unicodedata.category(caracter) != "Mn" else ""
        for caracter in texto
    ).replace("_", " ")


def _coincide_frase(texto: str, frases: tuple[str, ...]) -> bool:
    normalizado = _normalizar(texto)
    return any(_normalizar(frase) in normalizado for frase in frases)


def _parsear_filtros(consulta: str, hoy: date) -> FiltrosConsulta:
    normalizada = _normalizar(consulta)
    sentimiento = next(
        (
            clave
            for clave, sinonimos in _SINONIMOS_SENTIMIENTO.items()
            if _coincide_frase(normalizada, sinonimos)
        ),
        None,
    )
    tipo = next(
        (
            clave
            for clave, sinonimos in _SINONIMOS_TIPO.items()
            if _coincide_frase(normalizada, sinonimos)
        ),
        None,
    )
    plataforma = next(
        (
            clave
            for clave, sinonimos in _PLATAFORMAS.items()
            if any(
                re.search(r"\bx\b", normalizada)
                if sinonimo == "x"
                else _coincide_frase(normalizada, (sinonimo,))
                for sinonimo in sinonimos
            )
        ),
        None,
    )

    desde = hasta = None
    if re.search(r"\bayer\b", normalizada):
        desde = hasta = hoy - timedelta(days=1)
    elif re.search(r"\b(?:hoy|today)\b", normalizada):
        desde = hasta = hoy
    elif re.search(r"\b(?:semana pasada|la semana anterior|last week)\b", normalizada):
        inicio_semana = hoy - timedelta(days=hoy.weekday())
        desde = inicio_semana - timedelta(days=7)
        hasta = inicio_semana - timedelta(days=1)
    elif re.search(r"\b(?:ultimos? 7 dias|ultima semana|last 7 days|past week)\b", normalizada):
        desde = hoy - timedelta(days=6)
        hasta = hoy
    else:
        dias = re.search(r"\b(?:ultimos?|last)\s+(\d{1,3})\s+dias?\b", normalizada)
        if dias:
            cantidad = int(dias.group(1))
            if 1 <= cantidad <= 365:
                desde = hoy - timedelta(days=cantidad - 1)
                hasta = hoy

    return FiltrosConsulta(
        sentimiento=sentimiento,
        tipo_detectado=tipo,
        fecha_desde=desde,
        fecha_hasta=hasta,
        plataforma=(
            plataforma
            or ("linkedin" if _SOLICITUD_BORRADOR.search(consulta) else None)
        ),
        intencion="borrador" if _SOLICITUD_BORRADOR.search(consulta) else "consulta",
    )


def _tokens(texto: str) -> set[str]:
    return {
        token
        for token in _TOKEN.findall(_normalizar(texto))
        if token not in _PALABRAS_VACIAS and len(token) > 1
    }


_TERMINOS_FILTRO = frozenset(
    token
    for grupo in (
        *_SINONIMOS_SENTIMIENTO.values(),
        *_SINONIMOS_TIPO.values(),
        *_PLATAFORMAS.values(),
    )
    for frase in grupo
    for token in _TOKEN.findall(_normalizar(frase))
) | frozenset(
    """
    ayer hoy today yesterday semana pasada anterior last week ultimos dias
    pregunta preguntas tecnica tecnicas duda dudas testimonio testimonios
    experiencia experiencias feedback retroalimentacion sugerencia sugerencias
    comentario comentarios
    """
    .split()
)


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
    ):
        self._mensajes = _extraer_mensajes(datos_procesados)
        self._generador = generador
        self._verificador = verificador
        self._historial: list[dict[str, str]] = []
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
    ) -> dict:
        if not isinstance(consulta, str) or not consulta.strip():
            raise ValueError("Escribe una consulta para el agente.")
        if modo_verificacion not in {
            "prompt_estricto",
            "verificacion_automatica",
        }:
            raise ValueError("El modo de verificación seleccionado no es válido.")
        consulta = consulta.strip()
        if len(consulta) > MAX_CARACTERES_CONSULTA:
            raise ValueError(
                f"La consulta no puede superar {MAX_CARACTERES_CONSULTA} caracteres."
            )

        if _SOLICITUD_CODIGO.search(consulta) or _SOLICITUD_ACTUALIDAD_EXTERNA.search(consulta):
            respuesta = (
                "Este agente se limita a explorar los datos de la comunidad y "
                "preparar borradores de marketing basados en esos datos. "
                "Reformula la solicitud dentro de ese alcance."
            )
            salida = {
                "respuesta": respuesta,
                "citas": [],
                "borrador": None,
                "total_coincidencias": 0,
                "resumen": {},
                "filtros": _filtros_a_dict(FiltrosConsulta()),
                "modo": "fuera_de_alcance",
                "verificacion": {
                    "modo": modo_verificacion,
                    "estado": "no_aplica",
                    "resumen": "La solicitud está fuera del alcance del agente.",
                    "afirmaciones": [],
                },
            }
            self._guardar_turno(consulta, respuesta)
            return salida

        hoy = hoy or datetime.now(timezone.utc).date()
        filtros = _parsear_filtros(consulta, hoy)
        es_seguimiento = bool(self._historial) and bool(_SEGUIMIENTO.search(consulta))
        consulta_busqueda = consulta
        if es_seguimiento:
            anterior = next(
                (
                    turno["contenido"]
                    for turno in reversed(self._historial)
                    if turno["rol"] == "usuario"
                ),
                "",
            )
            consulta_busqueda = f"{anterior} {consulta}"
            filtros = _heredar_filtros(
                filtros,
                _parsear_filtros(anterior, hoy),
            )

        encontrados = self._buscar(consulta_busqueda, filtros)
        if filtros.intencion == "borrador":
            encontrados = [
                mensaje
                for mensaje in encontrados
                if mensaje["elegible_contenido"] is not False
            ]

        if not encontrados:
            respuesta = (
                "No encontré mensajes que coincidan con esos filtros en los datos "
                "procesados de esta sesión. Prueba con otro período, tema o filtro."
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
        evidencia = encontrados[:MAX_COINCIDENCIAS]
        salida_modelo = self._generar(
            consulta=consulta,
            filtros=filtros,
            resumen=resumen,
            evidencia=_evidencia_acotada(evidencia),
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
        borrador = (
            salida_modelo.borrador.model_dump()
            if salida_modelo.borrador is not None
            else None
        )
        verificacion = {
            "modo": modo_verificacion,
            "estado": "no_aplica" if borrador is None else "no_verificado",
            "resumen": (
                "No se solicitó un borrador."
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
        self._guardar_turno(consulta, respuesta)
        return salida

    def _buscar(
        self,
        consulta: str,
        filtros: FiltrosConsulta,
    ) -> list[dict]:
        terminos = _tokens(consulta) - _TERMINOS_FILTRO
        terminos = {termino for termino in terminos if not termino.isdecimal()}
        puntajes: Counter[int] = Counter()
        for termino in terminos:
            for indice in self._indice_invertido.get(termino, ()):
                puntajes[indice] += 1

        indices = set(puntajes)
        if not terminos:
            indices = set(range(len(self._mensajes)))

        resultados = []
        for indice in indices:
            mensaje = self._mensajes[indice]
            if filtros.sentimiento and _normalizar(mensaje["sentimiento"]) != filtros.sentimiento:
                continue
            if filtros.tipo_detectado and _normalizar(mensaje["tipo_detectado"]) != _normalizar(filtros.tipo_detectado):
                continue
            fecha = _fecha_mensaje(mensaje["fecha"])
            if filtros.fecha_desde and (fecha is None or fecha < filtros.fecha_desde):
                continue
            if filtros.fecha_hasta and (fecha is None or fecha > filtros.fecha_hasta):
                continue
            resultados.append((puntajes.get(indice, 0), indice, mensaje))

        resultados.sort(key=lambda item: (-item[0], item[1]))
        return [mensaje for _, _, mensaje in resultados]

    def _generar(
        self,
        *,
        consulta: str,
        filtros: FiltrosConsulta,
        resumen: dict,
        evidencia: list[dict],
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
        proveedor = obtener_proveedor_generacion()
        cadena = _obtener_cadena(proveedor)
        config = config_ejecucion(
            "agente_conversacional",
            intento=1,
            ruta="conversacion",
        )
        if proveedor == PROVEEDOR_NVIDIA_NIM:
            primario = lambda valor: _obtener_cadena(PROVEEDOR_NVIDIA_NIM).invoke(
                valor, config=config
            )
            respaldo = lambda valor: _obtener_cadena(PROVEEDOR_GEMINI).invoke(
                valor, config=config
            )
            primario.__name__ = PROVEEDOR_NVIDIA_NIM
            respaldo.__name__ = PROVEEDOR_GEMINI
            resultado = invocar_modelo_con_fallback(
                entrada,
                primario=primario,
                respaldo=respaldo,
            )["resultado"]
        else:
            resultado = cadena.invoke(entrada, config=config)
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

    def _guardar_turno(self, consulta: str, respuesta: str) -> None:
        self._historial.extend(
            [
                {"rol": "usuario", "contenido": consulta[:MAX_CARACTERES_CONSULTA]},
                {"rol": "asistente", "contenido": respuesta[:4_000]},
            ]
        )
        del self._historial[:-MAX_HISTORIAL * 2]


def _heredar_filtros(actual: FiltrosConsulta, anterior: FiltrosConsulta) -> FiltrosConsulta:
    return FiltrosConsulta(
        sentimiento=actual.sentimiento or anterior.sentimiento,
        tipo_detectado=actual.tipo_detectado or anterior.tipo_detectado,
        fecha_desde=actual.fecha_desde or anterior.fecha_desde,
        fecha_hasta=actual.fecha_hasta or anterior.fecha_hasta,
        plataforma=actual.plataforma or anterior.plataforma,
        intencion=(
            actual.intencion
            if actual.intencion == "borrador"
            else anterior.intencion
        ),
    )


def _filtros_a_dict(filtros: FiltrosConsulta) -> dict:
    valores = asdict(filtros)
    for campo in ("fecha_desde", "fecha_hasta"):
        if valores[campo] is not None:
            valores[campo] = valores[campo].isoformat()
    return valores


def _evidencia_acotada(mensajes: list[dict]) -> list[dict]:
    """Limita el texto enviado al modelo sin perderlo en el índice local."""
    return [
        {
            **mensaje,
            "texto": mensaje["texto"][:MAX_CARACTERES_MENSAJE],
        }
        for mensaje in mensajes
    ]


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
    return resumen


@lru_cache(maxsize=4)
def _obtener_cadena(proveedor: str):
    modelo = obtener_modelo_generacion_estructurado(
        SalidaConversacional,
        proveedor=proveedor,
        ruta="conversacion",
    )
    return prompt_conversacion | modelo


@lru_cache(maxsize=4)
def _obtener_cadena_verificacion(proveedor: str):
    modelo = obtener_modelo_generacion_estructurado(
        SalidaVerificacion,
        proveedor=proveedor,
        ruta="conversacion",
    )
    return prompt_verificacion | modelo
