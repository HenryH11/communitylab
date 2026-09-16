"""Ingesta real de interacciones de Reddit via RSS/Atom (sin OAuth, sin API key).

Diferencial opcional del proyecto CommunityLab (Sub-equipo 3 - Ingesta y
Procesamiento de Datos). El MVP obligatorio ya esta cubierto con datos
simulados en src/data/mensajes_comunidad_simulados.json.

Por que RSS y no PRAW: en 2026 Reddit deshabilito la creacion self-serve de
apps OAuth en reddit.com/prefs/apps como parte de su "Responsible Builder
Policy" (ver docs/fuentes_de_datos_acceso.md). Sin una app aprobada no hay
client_id/client_secret para PRAW. Los feeds RSS/Atom publicos de Reddit no
requieren autenticacion y siguen disponibles, asi que esta version los usa
como fuente real de datos.

Fuentes RSS usadas:
  - Posts nuevos de un subreddit:      https://www.reddit.com/r/<sub>/new/.rss
  - Comentarios de un post especifico: https://www.reddit.com/r/<sub>/comments/<post_id36>/.rss

Uso:
    python src/data/ingesta_reddit.py --subreddit webdev --posts 5 --comentarios-por-post 20

Sin dependencias externas: solo libreria estandar (urllib, xml.etree).

Nota: validado en desarrollo contra r/webdev real (ver docs/fuentes_de_datos_acceso.md).
La logica de parseo tambien se prueba sin red con fixtures de XML en
src/data/verificar_transformacion_reddit.py.
"""

import argparse
import html as html_lib
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
IDIOMA_POR_DEFECTO = "en"
# Relativo a este archivo (no al directorio desde donde se invoque el script),
# para que "python src/data/ingesta_reddit.py" desde la raiz del repo escriba
# en src/data/ y no en un data/ nuevo en la raiz.
RUTA_SALIDA_POR_DEFECTO = Path(__file__).resolve().parent / "mensajes_reddit_webdev.json"
USER_AGENT_POR_DEFECTO = "communitylab-ingesta-rss/1.0 (hackathon ONE G10, uso educativo)"
PAUSA_ENTRE_PETICIONES_SEGUNDOS = 2.0
REINTENTOS_429_MAX = 3

# Textos que Reddit deja en el cuerpo de un comentario cuando fue borrado por
# el autor o removido por moderacion. El contenido eliminado no debe
# conservarse en almacenamiento externo (ver docs/fuentes_de_datos_acceso.md).
CONTENIDO_ELIMINADO = {"[deleted]", "[removed]"}


def construir_url_posts_nuevos(subreddit_nombre, limite):
    return f"https://www.reddit.com/r/{subreddit_nombre}/new/.rss?limit={limite}"


def construir_url_comentarios_post(subreddit_nombre, post_id36):
    return f"https://www.reddit.com/r/{subreddit_nombre}/comments/{post_id36}/.rss"


def _segundos_de_espera_tras_429(error, intento):
    """Calcula cuanto esperar tras un 429, priorizando los headers de Reddit."""
    for nombre_header in ("x-ratelimit-reset", "Retry-After"):
        valor = error.headers.get(nombre_header)
        if valor:
            try:
                return max(float(valor), 1.0) + 1.0
            except ValueError:
                pass
    return min(5.0 * (intento + 1), 30.0)


def descargar_xml(url, user_agent, timeout=15, reintentos_max=REINTENTOS_429_MAX):
    """Unica funcion con efecto de red: descarga y devuelve el XML crudo.

    Reddit aplica rate limiting agresivo a peticiones sin autenticar (verificado
    en pruebas reales: 429 Too Many Requests tras un par de peticiones seguidas).
    Ante un 429 se reintenta con backoff, respetando x-ratelimit-reset/Retry-After
    si Reddit los envia."""
    solicitud = urllib.request.Request(url, headers={"User-Agent": user_agent})
    intento = 0
    while True:
        try:
            with urllib.request.urlopen(solicitud, timeout=timeout) as respuesta:
                return respuesta.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            if error.code == 429 and intento < reintentos_max:
                espera = _segundos_de_espera_tras_429(error, intento)
                print(
                    f"[WARN] 429 Too Many Requests en {url}; esperando {espera:.0f}s "
                    f"(intento {intento + 1}/{reintentos_max})...",
                    file=sys.stderr,
                )
                time.sleep(espera)
                intento += 1
                continue
            raise


def _texto_plano(html_contenido):
    """Convierte el HTML del feed Atom a texto plano simple (sin tags)."""
    sin_tags = re.sub(r"<[^>]+>", " ", html_contenido or "")
    return html_lib.unescape(re.sub(r"\s+", " ", sin_tags)).strip()


def _fullname_de_id(id_o_link_texto):
    """Extrae el fullname t1_xxxxx (comentario) / t3_xxxxx (post) de un <id> o <link>."""
    coincidencia = re.search(r"(t[13]_[a-z0-9]+)", id_o_link_texto or "")
    return coincidencia.group(1) if coincidencia else None


def _normalizar_fecha(fecha_texto):
    """Normaliza updated/published del feed a ISO 8601 UTC con sufijo Z."""
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
    """Parsea un feed Atom de Reddit. Funcion pura, no hace red.
    Devuelve una lista de dicts: {fullname, autor, texto, fecha_raw, link}.
    """
    raiz = ElementTree.fromstring(xml_texto)
    entradas = []
    for entrada in raiz.findall(f"{ATOM_NS}entry"):
        id_nodo = entrada.findtext(f"{ATOM_NS}id") or ""
        link_nodo = entrada.find(f"{ATOM_NS}link")
        link_href = link_nodo.get("href") if link_nodo is not None else ""
        fullname = _fullname_de_id(id_nodo) or _fullname_de_id(link_href)

        autor_nodo = entrada.find(f"{ATOM_NS}author/{ATOM_NS}name")
        autor = (autor_nodo.text or "").strip() if autor_nodo is not None else ""
        if autor.startswith("/u/"):
            autor = autor[len("/u/"):]

        contenido_nodo = entrada.find(f"{ATOM_NS}content")
        texto = _texto_plano(contenido_nodo.text if contenido_nodo is not None else "")

        fecha_raw = entrada.findtext(f"{ATOM_NS}updated") or entrada.findtext(f"{ATOM_NS}published") or ""

        entradas.append(
            {
                "fullname": fullname,
                "autor": autor or None,
                "texto": texto,
                "fecha_raw": fecha_raw,
                "link": link_href,
            }
        )
    return entradas


def es_comentario(entrada):
    return (entrada.get("fullname") or "").startswith("t1_")


def comentario_fue_eliminado(entrada):
    """True si el comentario fue borrado/removido en Reddit y no debe conservarse."""
    texto = (entrada.get("texto") or "").strip()
    autor = (entrada.get("autor") or "").strip()
    return texto in CONTENIDO_ELIMINADO or autor == "[deleted]"


def transformar_entrada(entrada, subreddit_nombre):
    """Mapea una entrada de comentario ya parseada al esquema de interaccion
    del proyecto (ver data/mensajes_comunidad_simulados.json). Funcion pura."""
    autor = entrada.get("autor") or "usuario_eliminado"
    texto = entrada.get("texto") or ""

    # Heuristica simple y explicitamente provisional: la clasificacion fina
    # (sentimiento/temas/tipo real) la hace el pipeline de IA del Sub-equipo 2.
    tipo = "pregunta_tecnica" if "?" in texto else "comentario"

    fullname = entrada.get("fullname") or "sin-id"

    return {
        "id": f"reddit-{fullname}",
        "autor": autor,
        "canal": f"r/{subreddit_nombre}",
        "tipo": tipo,
        "texto": texto,
        "fecha": _normalizar_fecha(entrada.get("fecha_raw")),
        "idioma": IDIOMA_POR_DEFECTO,
    }


def construir_lote(subreddit_nombre, periodo_referencia, interacciones):
    return {
        "origen_comunidad": f"Reddit_r_{subreddit_nombre}",
        "periodo_referencia": periodo_referencia,
        "interacciones": interacciones,
    }


def cargar_o_crear_estructura_salida(ruta_salida):
    if ruta_salida.exists():
        with ruta_salida.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "metadata": {
            "descripcion": (
                "Lotes de interacciones reales ingeridas desde los feeds RSS/Atom "
                "publicos de Reddit (sin OAuth), con el mismo esquema que "
                "data/mensajes_comunidad_simulados.json (diferencial opcional, "
                "no forma parte del MVP obligatorio)."
            ),
            "version": "0.2.0-borrador",
            "generado_por": "Gustavo Vasquez (Data Analyst, Sub-equipo 3) via scripts/ingesta_reddit.py",
            "fuente": "Reddit RSS/Atom (sin API key)",
        },
        "lotes": [],
    }


def guardar_lote(ruta_salida, nuevo_lote):
    estructura = cargar_o_crear_estructura_salida(ruta_salida)
    estructura["lotes"].append(nuevo_lote)
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)
    with ruta_salida.open("w", encoding="utf-8") as f:
        json.dump(estructura, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return estructura


def ejecutar_ingesta(subreddit_nombre, num_posts, comentarios_por_post, periodo_referencia, ruta_salida, user_agent):
    url_posts = construir_url_posts_nuevos(subreddit_nombre, num_posts)
    try:
        xml_posts = descargar_xml(url_posts, user_agent)
    except (urllib.error.URLError, urllib.error.HTTPError) as error:
        print(f"[ERROR] No se pudo obtener posts de r/{subreddit_nombre}: {error}", file=sys.stderr)
        sys.exit(1)

    posts = [e for e in parsear_entradas_atom(xml_posts) if not es_comentario(e)]
    print(f"Se encontraron {len(posts)} posts recientes en r/{subreddit_nombre}.")

    interacciones = []
    for post in posts:
        fullname = post.get("fullname") or ""
        post_id36 = fullname.split("_", 1)[1] if "_" in fullname else None
        if not post_id36:
            continue

        time.sleep(PAUSA_ENTRE_PETICIONES_SEGUNDOS)
        url_comentarios = construir_url_comentarios_post(subreddit_nombre, post_id36)
        try:
            xml_comentarios = descargar_xml(url_comentarios, user_agent)
        except (urllib.error.URLError, urllib.error.HTTPError) as error:
            print(f"[WARN] No se pudieron leer comentarios del post {post_id36}: {error}", file=sys.stderr)
            continue

        comentarios = [e for e in parsear_entradas_atom(xml_comentarios) if es_comentario(e)]
        for comentario in comentarios[:comentarios_por_post]:
            if comentario_fue_eliminado(comentario):
                continue
            interacciones.append(transformar_entrada(comentario, subreddit_nombre))

    if interacciones:
        lote = construir_lote(subreddit_nombre, periodo_referencia, interacciones)
        guardar_lote(ruta_salida, lote)
        print(f"Lote guardado: {len(interacciones)} interacciones en {ruta_salida}")
    else:
        print("No se obtuvieron interacciones; no se escribio ningun lote.")


def construir_parser_argumentos():
    parser = argparse.ArgumentParser(
        description="Ingesta de interacciones de Reddit via RSS/Atom publico (sin API key)."
    )
    parser.add_argument("--subreddit", default="webdev", help="Subreddit sin 'r/' (default: webdev).")
    parser.add_argument("--posts", type=int, default=5, help="Cantidad de posts recientes a recorrer.")
    parser.add_argument("--comentarios-por-post", type=int, default=20, help="Max. comentarios a tomar por post.")
    parser.add_argument("--periodo-referencia", default="Semana_00")
    parser.add_argument("--salida", default=str(RUTA_SALIDA_POR_DEFECTO))
    parser.add_argument("--user-agent", default=USER_AGENT_POR_DEFECTO)
    return parser


def main():
    parser = construir_parser_argumentos()
    args = parser.parse_args()
    ejecutar_ingesta(
        args.subreddit,
        args.posts,
        args.comentarios_por_post,
        args.periodo_referencia,
        Path(args.salida),
        args.user_agent,
    )


if __name__ == "__main__":
    main()
