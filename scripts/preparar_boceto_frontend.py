"""Extrae las vistas del SVG exportado y su geometría de Excalidraw.

Uso: python scripts/preparar_boceto_frontend.py escena.excalidraw escena.svg
Solo lee las fuentes; no las mueve ni modifica. El resultado es un activo local.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", NS)


def extraer(escena, svg):
    elementos = escena["elements"]
    grupos = [c for c in svg if c.tag == f"{{{NS}}}g"]
    if len(elementos) != len(grupos):
        raise ValueError("El SVG no corresponde a los elementos de la escena")
    for nodo in svg.iter():
        if nodo.tag.split("}")[-1] not in {"svg", "metadata", "defs", "style", "rect", "g", "path", "text", "mask"}:
            raise ValueError("El SVG contiene elementos no permitidos")
        if any(k.lower().startswith("on") or "href" in k.lower() for k in nodo.attrib):
            raise ValueError("El SVG contiene referencias o eventos externos")
    vistas = {}
    marcos = {nombre: (78 + (i % 3) * 1540, 258 + (i // 3) * 1050, 1440, 875)
              for i, nombre in enumerate(["inicio", "plantillas", "resultado", "agente", "analiticas", "ayuda", "datos", "mapa", "estados"])}
    marcos.update({"movil_inicio": (3225, 2610, 326, 470), "movil_resultado": (3605, 2610, 326, 470)})
    for nombre, (x, y, ancho, alto) in marcos.items():
        raiz = ET.Element(f"{{{NS}}}svg", {"viewBox": f"0 0 {ancho} {alto}", "aria-hidden": "true"})
        capa = ET.SubElement(raiz, f"{{{NS}}}g", {"transform": f"translate({-x-10} {-y-10})"})
        geometria = {}
        for elemento, grupo in zip(elementos, grupos):
            ex, ey = elemento["x"], elemento["y"]
            ew, eh = elemento["width"], elemento["height"]
            if x <= ex < x + ancho and y <= ey < y + alto and ew < ancho * 1.01:
                copia = deepcopy(grupo)
                copia.set("data-id", elemento["id"])
                capa.append(copia)
                geometria[elemento["id"]] = {"x": ex - x, "y": ey - y, "w": ew, "h": eh,
                    "texto": elemento.get("text", ""), "tipo": elemento["type"], "font": elemento.get("fontSize", 14)}
        vistas[nombre] = {"svg": ET.tostring(raiz, encoding="unicode"), "width": ancho, "height": alto, "elementos": geometria}
    return vistas


if __name__ == "__main__":
    fuente, exportacion = map(Path, sys.argv[1:3])
    vistas = extraer(json.loads(fuente.read_text(encoding="utf-8")), ET.fromstring(exportacion.read_text(encoding="utf-8")))
    destino = Path(__file__).resolve().parents[1] / "src/app/frontend/design.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(vistas, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{len(vistas)} vistas extraídas en {destino}")
