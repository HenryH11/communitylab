"""Auditoría de coherencia semántica (Semana 4, Análisis de Datos).

Compara el texto original de cada interacción con los activos generados por la IA
y emite alertas para revisión humana. Las alertas son señales, no un veredicto:
una paráfrasis fiel puede parecerse poco al original y un cambio de negación puede
conservar casi todas las palabras. La decisión final la toma una persona.

Solo usa la biblioteca estándar. No llama a modelos de IA ni a la red.

Modos:
    python scripts/auditoria_consistencia.py --casos tests/fixtures/casos_consistencia_semana4.json
    python scripts/auditoria_consistencia.py --entrega salida.json [--informe-datos informe.json]

Opciones comunes: --palabras-excluidas lista.json · --fuentes-aprobadas lista.json ·
--proveedor NOMBRE · --version-codigo SHA · --salida-json ruta · --salida-md ruta
"""

import argparse
from difflib import SequenceMatcher
import json
from pathlib import Path
import re
import sys
import unicodedata

NEGADORES = {"no", "ni", "sin", "nunca", "jamas", "tampoco", "ningun", "ninguna", "ninguno", "nada"}
# Palabras gramaticales que no cuentan como término negado ni como entidad.
FUNCIONALES = {
    "a", "al", "con", "de", "del", "el", "en", "es", "esta", "este", "la", "las", "lo", "los",
    "mi", "mis", "para", "por", "que", "se", "su", "sus", "te", "tu", "tus", "un", "una", "y",
    "o", "u", "ya", "aun", "todavia", "hay", "he", "ha", "han", "me", "le", "les", "nos",
}
# "un"/"una"/"uno" quedan fuera: casi siempre son artículos.
NUMEROS_EN_TEXTO = {
    "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7, "ocho": 8,
    "nueve": 9, "diez": 10, "once": 11, "doce": 12, "quince": 15, "veinte": 20,
    "treinta": 30, "cuarenta": 40, "cincuenta": 50, "cien": 100, "ciento": 100, "mil": 1000,
}
MESES = {
    "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
    "septiembre", "setiembre", "octubre", "noviembre", "diciembre",
}
PLAZO = re.compile(r"\ben\s+(\d+|[a-z]+)\s+(?:minutos?|horas?|dias?|semanas?|meses?)\b")
GARANTIA = re.compile(r"\bgarantiz\w*|\bte\s+aseguro\b|\bsin\s+falta\b")
# Futuro simple con tilde (resolverá, entregarán, obtendrás); se busca en el texto con tildes.
FUTURO = re.compile(r"\b\w{2,}(?:rá|rán|rás|ré)\b")
# Frases dirigidas al modelo, no al lector: el prompt se coló en la salida.
INSTRUCCION = re.compile(
    r"\bno\s+(?:inventes|agregues|incluyas|menciones|compares|uses|asumas)\b"
    r"|\b(?:una|la)\s+redaccion\s+(?:\w+\s+)?que\s+indique\b"
    r"|\bdevuelve\s+(?:solo|unicamente|un\s+json)\b"
    r"|\bcomo\s+(?:modelo|asistente)\s+de\s+(?:ia|lenguaje)\b"
)
# Campos de etiqueta o destino: no son afirmaciones sobre el mensaje.
CAMPOS_SIN_AFIRMACIONES = {"canal_recomendado", "hashtags", "seccion", "area"}
PALABRA = re.compile(r"#?[\w][\w'-]*", re.UNICODE)
FIN_FRASE = re.compile(r"[.!?:;¿¡\n]")


def sin_tildes(texto):
    descompuesto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


def palabras(texto):
    return [m.group(0) for m in PALABRA.finditer(texto)]


def texto_de(contenido):
    """Aplana el contenido de un activo (dict, lista o texto) a un solo texto."""
    if isinstance(contenido, str):
        return contenido
    if isinstance(contenido, dict):
        return ". ".join(texto_de(v) for k, v in contenido.items() if k not in CAMPOS_SIN_AFIRMACIONES)
    if isinstance(contenido, list):
        return " ".join(texto_de(v) for v in contenido)
    return ""


def numeros(texto):
    plano = sin_tildes(texto)
    hallados = {int(n) for n in re.findall(r"\d+", plano)}
    hallados |= {NUMEROS_EN_TEXTO[p] for p in palabras(plano) if p in NUMEROS_EN_TEXTO}
    return hallados


def entidades(texto):
    """Palabras con mayúscula que no abren frase. Ignora hashtags."""
    encontradas, inicio = [], True
    for m in re.finditer(r"#?[\w][\w'-]*|[.!?:;¿¡\n]", texto):
        token = m.group(0)
        if FIN_FRASE.fullmatch(token):
            inicio = True
            continue
        if not token.startswith("#") and token[0].isupper() and not inicio:
            encontradas.append(token)
        inicio = False
    return encontradas


def terminos_negados(texto):
    """Términos de contenido que siguen a un negador (ventana de 3 palabras)."""
    lista = [sin_tildes(p) for p in palabras(texto)]
    negados = set()
    for i, p in enumerate(lista):
        if p in NEGADORES:
            for q in lista[i + 1:i + 4]:
                if q not in NEGADORES and q not in FUNCIONALES and len(q) > 3:
                    negados.add(q)
    return negados


def negado_en(texto, termino):
    lista = [sin_tildes(p) for p in palabras(texto)]
    for i, p in enumerate(lista):
        if p == termino and not any(q in NEGADORES for q in lista[max(0, i - 4):i]):
            return False
    return True


def similitud(original, salida):
    a, b = sin_tildes(original), sin_tildes(salida)
    ta, tb = set(palabras(a)) - FUNCIONALES, set(palabras(b)) - FUNCIONALES
    jaccard = len(ta & tb) / len(ta | tb) if ta | tb else 1.0
    return round(SequenceMatcher(None, a, b).ratio(), 3), round(jaccard, 3)


def auditar_activo(original, salida, *, metadatos=(), fuentes=(), excluidas=(), excluido=None):
    """Devuelve las alertas de un activo frente a su original."""
    alertas = []
    if excluido:
        alertas.append({"tipo": "activo_de_mensaje_excluido",
                        "detalle": f"el mensaje se excluyó antes de la IA ({excluido})"})
    respaldo = " ".join([original, *metadatos, *fuentes])
    respaldo_plano = sin_tildes(respaldo)
    salida_plana = sin_tildes(salida)

    nuevos = sorted(numeros(salida) - numeros(respaldo))
    if nuevos:
        alertas.append({"tipo": "numero_sin_respaldo", "detalle": ", ".join(map(str, nuevos))})

    meses = sorted({p for p in palabras(salida_plana) if p in MESES} - set(palabras(respaldo_plano)))
    if meses:
        alertas.append({"tipo": "fecha_sin_respaldo", "detalle": ", ".join(meses)})

    vocabulario = set(palabras(respaldo_plano))
    ajenas = []
    for e in entidades(salida):
        plano = sin_tildes(e)
        if plano not in vocabulario and plano not in FUNCIONALES and e not in ajenas:
            ajenas.append(e)
    if ajenas:
        alertas.append({"tipo": "entidad_sin_respaldo", "detalle": ", ".join(ajenas)})

    perdidas = sorted(t for t in terminos_negados(original)
                      if t in palabras(salida_plana) and not negado_en(salida, t))
    if perdidas:
        alertas.append({"tipo": "negacion_perdida", "detalle": ", ".join(perdidas)})

    compromisos = []
    for m in PLAZO.finditer(salida_plana):
        cifra = numeros(m.group(1))
        if not cifra or not cifra <= numeros(respaldo):
            compromisos.append(m.group(0))
    compromisos += [m.group(0) for m in GARANTIA.finditer(salida_plana) if m.group(0) not in respaldo_plano]
    compromisos += [m.group(0) for m in FUTURO.finditer(salida.lower()) if m.group(0) not in respaldo.lower()]
    if compromisos:
        alertas.append({"tipo": "compromiso_sin_respaldo", "detalle": ", ".join(dict.fromkeys(compromisos))})

    filtradas = [m.group(0) for m in INSTRUCCION.finditer(salida_plana) if m.group(0) not in respaldo_plano]
    if filtradas:
        alertas.append({"tipo": "instruccion_filtrada", "detalle": ", ".join(dict.fromkeys(filtradas))})

    vetadas = [p for p in excluidas if sin_tildes(p) in salida_plana]
    if vetadas:
        alertas.append({"tipo": "palabra_excluida", "detalle": ", ".join(vetadas)})
    return alertas


def fila(id_interaccion, ruta, original, salida, alertas, **extra):
    secuencia, jaccard = similitud(original, salida)
    return {
        "id_interaccion": id_interaccion,
        "ruta": ruta,
        "original": original,
        "salida": salida,
        "similitud_secuencia": secuencia,
        "similitud_palabras": jaccard,
        "alertas": alertas,
        "decision_sugerida": "revisar" if alertas else "sin_alertas",
        "decision_humana": None,
        "justificacion": None,
        **extra,
    }


def auditar_casos(casos, opciones):
    """Modo de validación: activos simulados y variantes del fixture de DA."""
    filas = []
    for perfil in casos["perfiles"]:
        entrada = perfil["entrada"]
        autor = entrada["autor"]
        metadatos = (autor, entrada.get("canal", ""))
        excluido = perfil.get("motivo_exclusion")
        comunes = dict(metadatos=metadatos, fuentes=opciones["fuentes"],
                       excluidas=opciones["excluidas"], excluido=excluido)
        for ruta, contenido in (perfil.get("activos_simulados") or {}).items():
            salida = texto_de(contenido).replace("{autor}", autor)
            filas.append(fila(perfil["perfil"], ruta, entrada["texto"], salida,
                              auditar_activo(entrada["texto"], salida, **comunes),
                              esperado="aceptable", origen="activo_simulado"))
        for variante in perfil.get("variantes_para_auditor", []):
            filas.append(fila(perfil["perfil"], variante["id"], entrada["texto"], variante["salida"],
                              auditar_activo(entrada["texto"], variante["salida"], **comunes),
                              esperado=variante["decision_humana_esperada"], origen="variante"))
    return filas


def excluidos_del_informe(informe):
    """IDs descartados por Datos con su motivo, leídos del informe de ingesta."""
    excluidos = {}
    for lote in (informe or {}).get("lotes", []):
        for evaluacion in lote.get("evaluaciones", []):
            if evaluacion.get("motivos") and evaluacion.get("id"):
                excluidos[evaluacion["id"]] = ", ".join(evaluacion["motivos"])
    return excluidos


def trazabilidad(activo):
    """Proveedor, modelo y uso de respaldo que DS declara en cada activo."""
    return {
        "proveedor": activo.get("proveedor", "no_indicado"),
        "modelo": activo.get("modelo", "no_indicado"),
        "uso_fallback": activo.get("uso_fallback"),
    }


def normalizar_entrega(entrega):
    """Aplana el formato anidado de DS (version_auditoria 1.2) al contrato plano.

    Devuelve la entrega plana y los IDs que Datos excluyó según la propia entrega.
    """
    interacciones = entrega.get("interacciones", [])
    if not interacciones or "entrada" not in interacciones[0]:
        return entrega, {}
    planas, activos, excluidos = [], [], {}
    for interaccion in interacciones:
        entrada, datos = interaccion["entrada"], interaccion.get("datos") or {}
        planas.append({"id": interaccion["id"], "autor": entrada.get("autor", ""),
                       "canal": entrada.get("canal", ""), "texto": entrada["texto"]})
        if datos.get("excluido_por_data"):
            excluidos[interaccion["id"]] = ", ".join(datos.get("motivos_exclusion") or ["excluido_por_data"])
        for ruta, activo in (interaccion.get("activos") or {}).items():
            traza = activo.get("trazabilidad") or {}
            activos.append({
                "id_interaccion": interaccion["id"], "tipo": ruta, "contenido": activo["contenido"],
                "proveedor": traza.get("proveedor_usado", "no_indicado"),
                "modelo": traza.get("modelo", "no_indicado"),
                "uso_fallback": traza.get("fallback_activado"),
            })
    return {"interacciones": planas, "activos": activos}, excluidos


def auditar_entrega(entrega, informe, opciones):
    """Modo real: contrato de salida de DS (interacciones + activos)."""
    entrega, excluidos = normalizar_entrega(entrega)
    originales = {i["id"]: i for i in entrega.get("interacciones", [])}
    excluidos = {**excluidos, **excluidos_del_informe(informe)}
    filas = []
    for activo in entrega.get("activos", []):
        ident = activo["id_interaccion"]
        salida = texto_de(activo["contenido"])
        interaccion = originales.get(ident)
        if interaccion is None:
            filas.append(fila(ident, activo["tipo"], "", salida,
                              [{"tipo": "sin_original", "detalle": "el ID no está entre las interacciones"}],
                              **trazabilidad(activo)))
            continue
        metadatos = (interaccion.get("autor", ""), interaccion.get("canal", ""))
        alertas = auditar_activo(interaccion["texto"], salida, metadatos=metadatos,
                                 fuentes=opciones["fuentes"], excluidas=opciones["excluidas"],
                                 excluido=excluidos.get(ident))
        filas.append(fila(ident, activo["tipo"], interaccion["texto"], salida, alertas, **trazabilidad(activo)))
    return filas


def resumen(filas):
    datos = {"activos": len(filas), "con_alertas": sum(1 for f in filas if f["alertas"])}
    por_tipo = {}
    for f in filas:
        for a in f["alertas"]:
            por_tipo[a["tipo"]] = por_tipo.get(a["tipo"], 0) + 1
    datos["alertas_por_tipo"] = dict(sorted(por_tipo.items()))
    if any("modelo" in f for f in filas):
        por_modelo = {}
        for f in filas:
            clave = f"{f['proveedor']}/{f['modelo']}" + (" (fallback)" if f["uso_fallback"] else "")
            conteo = por_modelo.setdefault(clave, {"activos": 0, "con_alertas": 0})
            conteo["activos"] += 1
            conteo["con_alertas"] += bool(f["alertas"])
        datos["por_modelo"] = dict(sorted(por_modelo.items()))
    con_esperado = [f for f in filas if "esperado" in f]
    if con_esperado:
        datos["coinciden_con_lo_esperado"] = sum(
            1 for f in con_esperado
            if (f["esperado"] == "revisar") == (f["decision_sugerida"] == "revisar")
        )
        datos["con_decision_esperada"] = len(con_esperado)
    return datos


def a_markdown(reporte):
    meta, filas = reporte["metadatos"], reporte["filas"]
    lineas = [
        "# Auditoría de coherencia semántica",
        "",
        f"Proveedor: {meta['proveedor']} · Código: {meta['version_codigo']} · Modo: {meta['modo']}",
        "",
        "Las alertas son señales para revisión humana; la similitud es informativa.",
        "",
        "| ID | Ruta | Modelo | Similitud | Alertas | Sugerida | Esperada | Decisión humana |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for f in filas:
        alertas = "; ".join(f"{a['tipo']}: {a['detalle']}" for a in f["alertas"]) or "—"
        modelo = f"{f['proveedor']}/{f['modelo']}" + (" (fallback)" if f["uso_fallback"] else "") if "modelo" in f else "—"
        lineas.append(
            f"| {f['id_interaccion']} | {f['ruta']} | {modelo} "
            f"| {f['similitud_secuencia']} / {f['similitud_palabras']} "
            f"| {alertas.replace('|', '/')} | {f['decision_sugerida']} | {f.get('esperado', '—')} | |"
        )
    lineas += ["", "Resumen: `" + json.dumps(reporte["resumen"], ensure_ascii=False) + "`", ""]
    return "\n".join(lineas)


def cargar_json(ruta):
    with Path(ruta).open(encoding="utf-8-sig") as archivo:
        return json.load(archivo)


def principal(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    modo = parser.add_mutually_exclusive_group(required=True)
    modo.add_argument("--casos", help="fixture de casos de consistencia (validación)")
    modo.add_argument("--entrega", help="JSON del contrato de salida de DS")
    parser.add_argument("--informe-datos", help="informe de ingesta, para detectar activos de mensajes excluidos")
    parser.add_argument("--palabras-excluidas", help="JSON con una lista de palabras acordadas por el equipo")
    parser.add_argument("--fuentes-aprobadas", help="JSON con una lista de nombres o textos de respaldo")
    parser.add_argument("--proveedor", default="no_indicado")
    parser.add_argument("--version-codigo", default="no_indicada")
    parser.add_argument("--salida-json")
    parser.add_argument("--salida-md")
    args = parser.parse_args(argv)

    opciones = {
        "excluidas": cargar_json(args.palabras_excluidas) if args.palabras_excluidas else [],
        "fuentes": cargar_json(args.fuentes_aprobadas) if args.fuentes_aprobadas else [],
    }
    if args.casos:
        filas = auditar_casos(cargar_json(args.casos), opciones)
    else:
        informe = cargar_json(args.informe_datos) if args.informe_datos else None
        filas = auditar_entrega(cargar_json(args.entrega), informe, opciones)

    reporte = {
        "metadatos": {"modo": "casos" if args.casos else "entrega",
                      "proveedor": args.proveedor, "version_codigo": args.version_codigo},
        "resumen": resumen(filas),
        "filas": filas,
    }
    if args.salida_json:
        Path(args.salida_json).write_text(json.dumps(reporte, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.salida_md:
        Path(args.salida_md).write_text(a_markdown(reporte), encoding="utf-8")
    print(json.dumps(reporte["resumen"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
