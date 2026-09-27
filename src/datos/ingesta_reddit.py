"""Ingesta real de interacciones de Reddit mediante RSS/Atom (sin OAuth ni clave API).

Diferencial opcional de CommunityLab (Subequipo 3: Ingesta y Procesamiento
de Datos). El producto mínimo viable obligatorio ya está cubierto con datos
simulados en src/datos/mensajes_comunidad_simulados.json.

Por qué RSS y no PRAW: en 2026 Reddit deshabilitó el registro automático de
aplicaciones OAuth en reddit.com/prefs/apps como parte de su "Responsible
Builder Policy" (ver docs/fuentes_de_datos_acceso.md). Sin una aplicación
aprobada no hay client_id/client_secret para PRAW. Los canales RSS/Atom
públicos de Reddit no requieren autenticación y siguen disponibles, así que
esta versión los usa como fuente real de datos.

Fuentes RSS usadas:
    - Publicaciones nuevas de una comunidad: https://www.reddit.com/r/<comunidad>/new/.rss
    - Comentarios de una publicación: https://www.reddit.com/r/<sub>/comments/<post_id36>/.rss

Uso:
    python src/datos/ingesta_reddit.py --comunidad programacion --publicaciones 5 --comentarios-por-publicacion 20

La comunidad predeterminada es r/programacion (comunidad en español de
programación y desarrollo, más representativa del público del proyecto que
r/webdev en inglés, usado solo como prueba inicial). El idioma asignado a las
interacciones se controla con --idioma (por defecto, "es"), ya que no hay
detección automática.

Sin dependencias externas: solo biblioteca estándar (urllib, xml.etree).

Nota: se validó durante el desarrollo contra r/webdev (inglés) y r/programacion
(español) reales (ver docs/fuentes_de_datos_acceso.md). La lógica de análisis
también se prueba sin red con ejemplos XML en
tests/test_ingesta_reddit.py.
"""

import argparse
import html as biblioteca_html
import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

ATOM_NS = "{http://www.w3.org/2005/Atom}"
# r/programacion es hispanohablante; si se elige otra comunidad, hay que indicar
# --idioma explícitamente porque no hay detección automática.
IDIOMA_POR_DEFECTO = "es"
# Relativo a este archivo (no al directorio desde donde se invoque el script),
# para que "python src/datos/ingesta_reddit.py" desde la raiz del repo escriba
# en src/datos/ y no en una carpeta `datos/` nueva en la raíz. El nombre es
# genérico, sin depender de la comunidad, y acumula un lote por ejecución.
RUTA_SALIDA_POR_DEFECTO = Path(__file__).resolve().parent / "mensajes_reddit.json"
AGENTE_USUARIO_POR_DEFECTO = "communitylab-ingesta-rss/1.0 (hackathon ONE G10, uso educativo)"
PAUSA_ENTRE_PETICIONES_SEGUNDOS = 2.0
MAXIMO_REINTENTOS_429 = 3

# Textos que Reddit deja en el cuerpo de un comentario cuando fue borrado por
# el autor o removido por moderacion. El contenido eliminado no debe
# conservarse en almacenamiento externo (ver docs/fuentes_de_datos_acceso.md).
CONTENIDO_ELIMINADO = {"[deleted]", "[removed]"}


def construir_url_publicaciones_nuevas(nombre_comunidad, limite):
    return f"https://www.reddit.com/r/{nombre_comunidad}/new/.rss?limit={limite}"


def construir_url_comentarios_publicacion(nombre_comunidad, id_publicacion_base36):
    return f"https://www.reddit.com/r/{nombre_comunidad}/comments/{id_publicacion_base36}/.rss"


def _segundos_de_espera_tras_429(error, intento):
    """Calcula cuanto esperar tras un 429, priorizando los headers de Reddit."""
    for nombre_cabecera in ("x-ratelimit-reset", "Retry-After"):
        valor = error.headers.get(nombre_cabecera)
        if valor:
            try:
                return max(float(valor), 1.0) + 1.0
            except ValueError:
                pass
    return min(5.0 * (intento + 1), 30.0)


def descargar_xml(direccion, agente_usuario, tiempo_limite=15, maximo_reintentos=MAXIMO_REINTENTOS_429):
    """Única función con acceso a red: descarga y devuelve el XML original.

    Reddit limita las peticiones sin autenticar (verificado en pruebas: respuesta
    429 tras varias solicitudes). Ante un 429 se reintenta con espera progresiva,
    respetando las cabeceras x-ratelimit-reset y Retry-After si se reciben."""
    solicitud = urllib.request.Request(
        direccion,
        headers={"User-Agent": agente_usuario},
    )
    intento = 0
    while True:
        try:
            with urllib.request.urlopen(
                solicitud,
                timeout=tiempo_limite,
            ) as respuesta:
                return respuesta.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            if error.code == 429 and intento < maximo_reintentos:
                espera = _segundos_de_espera_tras_429(error, intento)
                print(
                    f"[AVISO] Reddit limitó las solicitudes a {direccion}; "
                    f"esperando {espera:.0f}s "
                    f"(intento {intento + 1}/{maximo_reintentos})...",
                    file=sys.stderr,
                )
                time.sleep(espera)
                intento += 1
                continue
            raise


def _texto_plano(html_contenido):
    """Convierte el HTML del feed Atom a texto plano simple (sin tags)."""
    sin_tags = re.sub(r"<[^>]+>", " ", html_contenido or "")
    return biblioteca_html.unescape(re.sub(r"\s+", " ", sin_tags)).strip()


def _obtener_id_completo(texto_id_o_enlace):
    """Extrae el identificador Reddit t1_/t3_ de un elemento Atom <id> o <link>."""
    coincidencia = re.search(r"(t[13]_[a-z0-9]+)", texto_id_o_enlace or "")
    return coincidencia.group(1) if coincidencia else None


def _normalizar_fecha(fecha_texto):
    """Normaliza updated/published a ISO 8601 UTC con sufijo Z."""
    if fecha_texto:
        texto = fecha_texto.strip()
        texto_iso = texto[:-1] + "+00:00" if texto.endswith("Z") else texto
        try:
            momento = datetime.fromisoformat(texto_iso)
            if momento.tzinfo is None:
                momento = momento.replace(tzinfo=timezone.utc)
            return momento.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        except ValueError:
            pass
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parsear_entradas_atom(xml_texto):
    """Analiza un canal Atom de Reddit sin hacer solicitudes de red.

    Devuelve diccionarios con id_completo, autor, texto, fecha_original y enlace.
    """
    raiz = ElementTree.fromstring(xml_texto)
    entradas = []
    for entrada in raiz.findall(f"{ATOM_NS}entry"):
        id_nodo = entrada.findtext(f"{ATOM_NS}id") or ""
        link_nodo = entrada.find(f"{ATOM_NS}link")
        url_enlace = link_nodo.get("href") if link_nodo is not None else ""
        id_completo = _obtener_id_completo(id_nodo) or _obtener_id_completo(url_enlace)

        autor_nodo = entrada.find(f"{ATOM_NS}author/{ATOM_NS}name")
        autor = (autor_nodo.text or "").strip() if autor_nodo is not None else ""
        if autor.startswith("/u/"):
            autor = autor[len("/u/"):]

        contenido_nodo = entrada.find(f"{ATOM_NS}content")
        texto = _texto_plano(contenido_nodo.text if contenido_nodo is not None else "")

        fecha_original = (
            entrada.findtext(f"{ATOM_NS}updated")
            or entrada.findtext(f"{ATOM_NS}published")
            or ""
        )

        entradas.append(
            {
                "id_completo": id_completo,
                "autor": autor or None,
                "texto": texto,
                "fecha_original": fecha_original,
                "enlace": url_enlace,
            }
        )
    return entradas


def es_comentario(entrada):
    return (entrada.get("id_completo") or "").startswith("t1_")


def comentario_fue_eliminado(entrada):
    """Indica si Reddit borró o retiró el comentario y no debe conservarse."""
    texto = (entrada.get("texto") or "").strip()
    autor = (entrada.get("autor") or "").strip()
    return texto in CONTENIDO_ELIMINADO or autor == "[deleted]"


def transformar_entrada(entrada, nombre_comunidad, idioma=IDIOMA_POR_DEFECTO):
    """Adapta un comentario analizado al esquema de interacción del proyecto.

    El idioma se recibe de forma explícita porque no se detecta automáticamente.
    """
    autor = entrada.get("autor") or "usuario_eliminado"
    texto = entrada.get("texto") or ""

    # Clasificación provisional: la IA determina sentimiento, temas y tipo real.
    # Esta regla funciona en español e inglés porque ambos usan "?" en preguntas.
    tipo = "pregunta_tecnica" if "?" in texto else "comentario"

    id_completo = entrada.get("id_completo") or "sin-id"

    return {
        "id": f"reddit-{id_completo}",
        "autor": autor,
        "canal": f"r/{nombre_comunidad}",
        "tipo": tipo,
        "texto": texto,
        "fecha": _normalizar_fecha(entrada.get("fecha_original")),
        "idioma": idioma,
    }


def construir_lote(nombre_comunidad, periodo_referencia, interacciones):
    return {
        "origen_comunidad": f"Reddit_r_{nombre_comunidad}",
        "periodo_referencia": periodo_referencia,
        "interacciones": interacciones,
    }


def cargar_o_crear_estructura_salida(ruta_salida):
    if ruta_salida.exists():
        with ruta_salida.open("r", encoding="utf-8") as archivo:
            return json.load(archivo)
    return {
        "metadata": {
            "descripcion": (
                "Lotes de interacciones reales ingeridas desde los feeds RSS/Atom "
                "públicos de Reddit (sin OAuth), con el mismo esquema que "
                "src/datos/mensajes_comunidad_simulados.json (diferencial opcional, "
                "no forma parte del producto mínimo viable obligatorio)."
            ),
            "version": "0.3.0-borrador",
            "generado_por": "Gustavo Vásquez (Analista de datos, Sub-equipo 3), mediante src/datos/ingesta_reddit.py",
            "fuente": "Reddit RSS/Atom (sin clave API)",
        },
        "lotes": [],
    }


def guardar_lote(ruta_salida, nuevo_lote):
    estructura = cargar_o_crear_estructura_salida(ruta_salida)
    estructura["lotes"].append(nuevo_lote)
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)
    with ruta_salida.open("w", encoding="utf-8") as archivo:
        json.dump(estructura, archivo, ensure_ascii=False, indent=2)
        archivo.write("\n")
    return estructura


def ejecutar_ingesta(
    nombre_comunidad,
    cantidad_publicaciones,
    comentarios_por_publicacion,
    periodo_referencia,
    ruta_salida,
    agente_usuario,
    idioma=IDIOMA_POR_DEFECTO,
):
    url_publicaciones = construir_url_publicaciones_nuevas(
        nombre_comunidad,
        cantidad_publicaciones,
    )
    try:
        xml_publicaciones = descargar_xml(url_publicaciones, agente_usuario)
    except (urllib.error.URLError, urllib.error.HTTPError) as error:
        print(
            f"[ERROR] No se pudieron obtener publicaciones de "
            f"r/{nombre_comunidad}: {error}",
            file=sys.stderr,
        )
        sys.exit(1)

    publicaciones = [
        entrada
        for entrada in parsear_entradas_atom(xml_publicaciones)
        if not es_comentario(entrada)
    ]
    print(
        f"Se encontraron {len(publicaciones)} publicaciones recientes "
        f"en r/{nombre_comunidad}."
    )

    interacciones = []
    for publicacion in publicaciones:
        id_completo = publicacion.get("id_completo") or ""
        id_publicacion_base36 = (
            id_completo.split("_", 1)[1]
            if "_" in id_completo
            else None
        )
        if not id_publicacion_base36:
            continue

        time.sleep(PAUSA_ENTRE_PETICIONES_SEGUNDOS)
        url_comentarios = construir_url_comentarios_publicacion(
            nombre_comunidad,
            id_publicacion_base36,
        )
        try:
            xml_comentarios = descargar_xml(url_comentarios, agente_usuario)
        except (urllib.error.URLError, urllib.error.HTTPError) as error:
            print(
                f"[AVISO] No se pudieron leer los comentarios de la "
                f"publicación {id_publicacion_base36}: {error}",
                file=sys.stderr,
            )
            continue

        comentarios = [
            entrada
            for entrada in parsear_entradas_atom(xml_comentarios)
            if es_comentario(entrada)
        ]
        for comentario in comentarios[:comentarios_por_publicacion]:
            if comentario_fue_eliminado(comentario):
                continue
            interacciones.append(
                transformar_entrada(
                    comentario,
                    nombre_comunidad,
                    idioma=idioma,
                )
            )

    if interacciones:
        lote = construir_lote(
            nombre_comunidad,
            periodo_referencia,
            interacciones,
        )
        guardar_lote(ruta_salida, lote)
        print(f"Lote guardado: {len(interacciones)} interacciones en {ruta_salida}")
    else:
        print("No se obtuvieron interacciones; no se guardó ningún lote.")


def construir_parser_argumentos():
    parser = argparse.ArgumentParser(
        description="Ingesta interacciones de Reddit desde RSS/Atom público (sin clave API)."
    )
    parser.add_argument(
        "--comunidad",
        dest="nombre_comunidad",
        default="programacion",
        help="Comunidad sin 'r/' (por defecto: programacion).",
    )
    parser.add_argument(
        "--subreddit",
        dest="nombre_comunidad",
        default=argparse.SUPPRESS,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--publicaciones",
        dest="cantidad_publicaciones",
        type=int,
        default=5,
        help="Cantidad de publicaciones recientes que se consultan.",
    )
    parser.add_argument(
        "--posts",
        dest="cantidad_publicaciones",
        type=int,
        default=argparse.SUPPRESS,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--comentarios-por-publicacion",
        dest="comentarios_por_publicacion",
        type=int,
        default=20,
        help="Cantidad máxima de comentarios por publicación.",
    )
    parser.add_argument(
        "--comentarios-por-post",
        dest="comentarios_por_publicacion",
        type=int,
        default=argparse.SUPPRESS,
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--periodo-referencia", default="Semana_00")
    parser.add_argument("--salida", default=str(RUTA_SALIDA_POR_DEFECTO))
    parser.add_argument(
        "--agente-usuario",
        dest="agente_usuario",
        default=AGENTE_USUARIO_POR_DEFECTO,
        help="Identificador enviado en la cabecera HTTP User-Agent.",
    )
    parser.add_argument(
        "--user-agent",
        dest="agente_usuario",
        default=argparse.SUPPRESS,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--idioma",
        default=IDIOMA_POR_DEFECTO,
        help=f"Código ISO 639-1 de las interacciones (por defecto: {IDIOMA_POR_DEFECTO}). "
        "No se detecta automáticamente; indícalo si la comunidad usa otro idioma.",
    )
    return parser


def principal():
    parser = construir_parser_argumentos()
    argumentos = parser.parse_args()
    ejecutar_ingesta(
        argumentos.nombre_comunidad,
        argumentos.cantidad_publicaciones,
        argumentos.comentarios_por_publicacion,
        argumentos.periodo_referencia,
        Path(argumentos.salida),
        argumentos.agente_usuario,
        idioma=argumentos.idioma,
    )


if __name__ == "__main__":
    principal()
