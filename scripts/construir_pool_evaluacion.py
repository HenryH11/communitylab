"""Construye el pool de evaluación v2: 200 casos por fuente, reproducible y con atribución.

Fuentes públicas (descargadas aparte; este script no usa red ni IA):
- uca_ia_tweets: "IA Tweets Analysis Dataset (Spanish)", Universidad de Cádiz, Zenodo
  10.5281/zenodo.10821485, CC BY 4.0. Trae polaridad P/N/NEU.
- stackoverflow_es: preguntas de es.stackoverflow.com por la API pública de Stack
  Exchange, CC BY-SA (versión por pregunta, campo content_license).

Salida con el formato del holdout congelado (tests/fixtures/holdout_final_analisis_semana3.json),
para que scripts/evaluar_holdout_proveedores.py la lea con --fixture. Cada etiqueta
esperada declara su origen ("fuente" o "regla") y queda pendiente de revisión humana.
"""

import argparse
import csv
import hashlib
import html
import json
import random
import re
from collections import Counter
from pathlib import Path

SEMILLA = 20261015
POR_FUENTE = 200
LARGO_MAXIMO = 400
LARGO_MINIMO = 40

POLARIDAD_UCA = {"P": "positivo", "N": "negativo", "NEU": "neutral"}
# Etiqueta de Stack Overflow -> tema_principal del contrato de DS (src/agentes/modelos.py).
TEMA_POR_ETIQUETA_SO = {
    "python": "programacion", "javascript": "programacion", "html": "programacion",
    "css": "programacion", "sql": "programacion", "java": "programacion",
    "git": "programacion", "pandas": "datos_ia", "machine-learning": "datos_ia",
    "docker": "cloud_infraestructura",
}
PALABRAS_ES = frozenset(
    "el la los las de del que y en un una por para con no es se lo al como más pero "
    "su sus este esta son está ya muy también hay sobre entre cuando porque".split()
)
PALABRAS_EN = frozenset(
    "the and of to is in that for with this are you we our it be on your have will".split()
)
URL = re.compile(r"https?://\S+")
MENCION = re.compile(r"@\w+")
ETIQUETA_HTML = re.compile(r"<[^>]+>")
BLOQUE_CODIGO = re.compile(r"<pre[^>]*>.*?</pre>", re.S | re.I)
PALABRA = re.compile(r"[a-záéíóúüñ]+", re.I)


def normalizar(texto):
    return " ".join(str(texto or "").split())


def recortar(texto, largo=LARGO_MAXIMO):
    texto = normalizar(texto)
    if len(texto) <= largo:
        return texto
    corte = texto[:largo - 1]
    if " " in corte:
        corte = corte[:corte.rindex(" ")]
    return corte.rstrip(" ,;:.") + "…"


def es_espanol(texto):
    palabras = [p.lower() for p in PALABRA.findall(texto)]
    espanol = sum(p in PALABRAS_ES for p in palabras)
    ingles = sum(p in PALABRAS_EN for p in palabras)
    return espanol >= 3 and espanol > 2 * ingles


def clave_duplicado(texto):
    return " ".join(PALABRA.findall(texto.lower()))[:120]


def limpiar_tuit(texto):
    """Quita enlaces, anonimiza menciones y colapsa espacios."""
    texto = URL.sub("", html.unescape(texto))
    texto = MENCION.sub("@usuario", texto)
    return normalizar(texto)


def limpiar_pregunta(titulo, cuerpo):
    """Título + primer tramo del cuerpo, sin bloques de código ni HTML."""
    cuerpo = BLOQUE_CODIGO.sub(" [código] ", cuerpo or "")
    cuerpo = html.unescape(ETIQUETA_HTML.sub(" ", cuerpo))
    titulo = html.unescape(titulo).strip()
    separador = " " if titulo.endswith(("?", "!", ".", ":")) else ". "
    return recortar(f"{titulo}{separador}{normalizar(cuerpo)}")


def candidatos_uca(ruta_csv):
    vistos, filas = set(), []
    with open(ruta_csv, encoding="utf-8", newline="") as archivo:
        for fila in csv.DictReader(archivo):
            texto = limpiar_tuit(fila["text"])
            sin_menciones = texto.replace("@usuario", "").strip()
            clave = clave_duplicado(texto)
            if (fila["polarity"] not in POLARIDAD_UCA or len(sin_menciones) < LARGO_MINIMO
                    or not es_espanol(texto) or clave in vistos):
                continue
            vistos.add(clave)
            filas.append({
                "id": f"uca-{fila['ID']}",
                "texto": recortar(texto),
                "origen": "Twitter_IA_UCA",
                "canal": "twitter-ia",
                "idioma": "es",
                "sentimiento_esperado": POLARIDAD_UCA[fila["polarity"]],
                "tema_esperado": "datos_ia",
                "tipo_esperado": "comentario",
                "subtema_referencia": "inteligencia artificial",
                "origen_etiquetas": {"sentimiento": "fuente", "tema": "regla", "tipo": "regla"},
                "revision_humana": "pendiente",
                "atribucion": {"fuente": "IA Tweets Analysis Dataset (Spanish)",
                               "doi": "10.5281/zenodo.10821485", "licencia": "CC BY 4.0"},
            })
    return filas


def candidatos_so(carpeta):
    filas, vistos, claves = [], set(), set()
    for ruta in sorted(Path(carpeta).glob("*.json")):
        etiqueta = ruta.stem
        if etiqueta not in TEMA_POR_ETIQUETA_SO:
            continue
        for pregunta in json.loads(ruta.read_bytes().decode("utf-8")).get("items", []):
            identificador = pregunta["question_id"]
            texto = limpiar_pregunta(pregunta["title"], pregunta.get("body", ""))
            clave = clave_duplicado(texto)
            if identificador in vistos or clave in claves or len(texto) < LARGO_MINIMO:
                continue
            vistos.add(identificador)
            claves.add(clave)
            filas.append({
                "id": f"so-{identificador}",
                "texto": texto,
                "origen": "StackOverflow_ES",
                "canal": f"stackoverflow-es/{etiqueta}",
                "idioma": "es",
                "sentimiento_esperado": "neutral",
                "tema_esperado": TEMA_POR_ETIQUETA_SO[etiqueta],
                "tipo_esperado": "pregunta_tecnica",
                "subtema_referencia": etiqueta,
                "origen_etiquetas": {"sentimiento": "regla", "tema": "regla", "tipo": "fuente"},
                "revision_humana": "pendiente",
                "atribucion": {"fuente": pregunta["link"],
                               "autor": (pregunta.get("owner") or {}).get("display_name"),
                               "licencia": pregunta.get("content_license", "CC BY-SA 4.0")},
            })
    return filas


def muestrear_por_grupo(filas, campo, total, semilla):
    """Muestra estratificada: reparte `total` en partes iguales entre los valores de `campo`."""
    azar = random.Random(semilla)
    grupos = {}
    for fila in sorted(filas, key=lambda f: f["id"]):
        grupos.setdefault(fila[campo], []).append(fila)
    claves = sorted(grupos)
    cuota = {c: total // len(claves) + (1 if i < total % len(claves) else 0) for i, c in enumerate(claves)}
    elegidas = []
    for clave in claves:
        if len(grupos[clave]) < cuota[clave]:
            raise ValueError(f"Faltan casos en {campo}={clave}: {len(grupos[clave])} < {cuota[clave]}")
        elegidas += azar.sample(grupos[clave], cuota[clave])
    return sorted(elegidas, key=lambda f: f["id"])


def sha256(ruta):
    return hashlib.sha256(Path(ruta).read_bytes()).hexdigest()


def distribucion(casos, campo):
    return dict(sorted(Counter(c[campo] for c in casos).items()))


def construir(uca_csv, so_dir, salida, semilla=SEMILLA, por_fuente=POR_FUENTE, excluir_textos=()):
    salida = Path(salida)
    salida.mkdir(parents=True, exist_ok=True)
    excluir = {clave_duplicado(t) for t in excluir_textos}
    fuentes = {
        "uca_ia_tweets": (candidatos_uca(uca_csv), "sentimiento_esperado",
                          "Tuits en español sobre IA (Universidad de Cádiz, CC BY 4.0), equilibrados por polaridad."),
        "stackoverflow_es": (candidatos_so(so_dir), "subtema_referencia",
                             "Preguntas de es.stackoverflow.com (CC BY-SA), equilibradas por etiqueta."),
    }
    manifiesto = {"version": "pool_v2", "semilla": semilla, "por_fuente": por_fuente,
                  "entradas": {"uca_csv_sha256": sha256(uca_csv)}, "archivos": {}}
    for nombre, (candidatos, estrato, descripcion) in fuentes.items():
        candidatos = [c for c in candidatos if clave_duplicado(c["texto"]) not in excluir]
        casos = muestrear_por_grupo(candidatos, estrato, por_fuente, semilla)
        ruta = salida / f"{nombre}.json"
        ruta.write_text(json.dumps({"descripcion": descripcion, "casos": casos},
                                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        manifiesto["archivos"][ruta.name] = {
            "sha256": sha256(ruta), "casos": len(casos), "candidatos": len(candidatos),
            "estrato": estrato,
            "sentimiento": distribucion(casos, "sentimiento_esperado"),
            "tema": distribucion(casos, "tema_esperado"),
            "tipo": distribucion(casos, "tipo_esperado"),
        }
    (salida / "manifiesto.json").write_text(json.dumps(manifiesto, ensure_ascii=False, indent=2) + "\n",
                                            encoding="utf-8")
    return manifiesto


def textos_congelados(raiz):
    """Textos del holdout v1 y del dataset base, para que el pool no los repita."""
    raiz = Path(raiz)
    holdout = json.loads((raiz / "tests/fixtures/holdout_final_analisis_semana3.json").read_text(encoding="utf-8"))
    base = json.loads((raiz / "src/datos/mensajes_comunidad_simulados.json").read_text(encoding="utf-8"))
    return [c["texto"] for c in holdout["casos"]] + [
        m["texto"] for lote in base["lotes"] for m in lote["interacciones"]]


def principal(argumentos=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--uca-csv", required=True)
    parser.add_argument("--so-dir", required=True)
    parser.add_argument("--salida", default="datos_evaluacion/pool_v2")
    parser.add_argument("--semilla", type=int, default=SEMILLA)
    parser.add_argument("--por-fuente", type=int, default=POR_FUENTE)
    args = parser.parse_args(argumentos)
    raiz = Path(__file__).resolve().parents[1]
    manifiesto = construir(args.uca_csv, args.so_dir, args.salida, args.semilla, args.por_fuente,
                           textos_congelados(raiz))
    print(json.dumps({n: {"casos": a["casos"], "candidatos": a["candidatos"]}
                      for n, a in manifiesto["archivos"].items()}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
