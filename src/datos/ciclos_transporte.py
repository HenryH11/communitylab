"""Gestión de fragmentos y transporte de ciclos de datos para entrega."""

import json
from pathlib import Path
import re
from typing import Any, Callable

if __package__:
    from .relevancia import TIPOS, leer_fecha
else:
    from relevancia import TIPOS, leer_fecha

RAIZ = Path(__file__).resolve().parents[2]

_CARACTERES_NO_SEGUROS_ARCHIVO = re.compile(r"[^A-Za-z0-9_-]+")
_CAMPOS_CONTRATO_NELSON = ("id", "autor", "canal", "tipo", "texto", "fecha", "idioma")


def _nombre_seguro(texto: str) -> str:
    """Reduce un campo de datos (origen_comunidad, periodo_referencia) a algo
    seguro para usar en un nombre de archivo: solo letras/números/guiones. Evita
    que un valor con `/` o `..` escriba fuera del directorio de ciclos."""
    limpio = _CARACTERES_NO_SEGUROS_ARCHIVO.sub("_", texto).strip("_")
    return limpio or "sin_nombre"


def validar_tamano_ciclo(tamano: Any) -> None:
    """Valida que el tamaño de ciclo esté acotado entre 10 y 30."""
    if type(tamano) is not int or not 10 <= tamano <= 30:
        raise ValueError("tamano_ciclo debe ser un entero entre 10 y 30")


def _validar_cadena(objeto: dict, campo: str, ruta: str, vacia: bool = False) -> None:
    """Valida que un campo sea cadena no vacía y representable en UTF-8."""
    valor = objeto.get(campo)
    if not isinstance(valor, str) or (not vacia and not valor.strip()):
        raise ValueError(
            f"{ruta}.{campo}: se esperaba texto" + (" no vacío" if not vacia else "")
        )
    try:
        valor.encode("utf-8", errors="strict")
    except UnicodeEncodeError as error:
        raise ValueError(f"{ruta}.{campo}: texto no representable en UTF-8") from error


def _interaccion_para_entrega(interaccion: dict, *, permitir_texto_vacio: bool = False) -> dict:
    """Proyecta una interacción ya depurada al contrato oficial de Nelson
    (`docs/arquitectura-solucion/contrato-intermedio-ingesta.schema.json`):
    exactamente `id`/`autor`/`canal`/`tipo`/`texto`/`fecha`/`idioma`, los siete
    obligatorios y sin campos adicionales (`additionalProperties: false`)."""
    faltantes = [campo for campo in _CAMPOS_CONTRATO_NELSON if campo not in interaccion]
    if faltantes:
        raise ValueError(
            "Interacción sin los campos obligatorios del contrato de entrega "
            f"({', '.join(_CAMPOS_CONTRATO_NELSON)}): faltan {', '.join(faltantes)}"
        )
    for campo in _CAMPOS_CONTRATO_NELSON:
        _validar_cadena(
            interaccion, campo, "interaccion", vacia=campo == "texto" and permitir_texto_vacio
        )
    if interaccion["tipo"] not in TIPOS:
        raise ValueError("Tipo no admitido en la entrega")
    if interaccion["id"] != interaccion["id"].strip():
        raise ValueError("ID con espacios exteriores")
    fecha = interaccion["fecha"]
    if not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)",
        fecha,
    ):
        raise ValueError("fecha debe ser ISO 8601 completa con zona horaria")
    try:
        leer_fecha(fecha)
    except ValueError as error:
        raise ValueError("fecha inválida en la entrega") from error
    return {campo: interaccion[campo] for campo in _CAMPOS_CONTRATO_NELSON}


def construir_ciclos(salida: dict, tamano_ciclo: int, validador_limpiador: Callable[[dict], dict] | None = None) -> list[dict]:
    """Exporta fragmentos planos por origen, conservando el orden recibido.

    N debe estar entre 10 y 30; un fragmento final puede tener menos de 10.
    Estos archivos son transporte, no los ciclos operativos: esos se definen
    en construir_plan_procesamiento. Cada interacción tiene siete campos válidos
    e ID único en la entrega. Un lote vacío no genera archivos.
    """
    validar_tamano_ciclo(tamano_ciclo)
    if validador_limpiador is not None:
        datos = validador_limpiador(salida)
    else:
        try:
            from .ingesta import validar_y_limpiar
        except (ImportError, ValueError):
            from ingesta import validar_y_limpiar
        datos = validar_y_limpiar(salida)

    lotes = datos["lotes"] if "lotes" in datos else [datos]
    ciclos = []
    vistos = set()
    for lote_indice, lote in enumerate(lotes):
        interacciones = lote["interacciones"]
        origen = _nombre_seguro(lote["origen_comunidad"])
        periodo = _nombre_seguro(lote["periodo_referencia"])
        for ciclo_indice, inicio in enumerate(range(0, len(interacciones), tamano_ciclo)):
            fragmento = [_interaccion_para_entrega(i) for i in interacciones[inicio:inicio + tamano_ciclo]]
            for mensaje in fragmento:
                if mensaje["id"] in vistos:
                    raise ValueError("IDs repetidos en la entrega")
                vistos.add(mensaje["id"])
            ciclos.append({
                "archivo": f"{origen}_{periodo}_lote{lote_indice}_ciclo{ciclo_indice}.json",
                "contenido": {
                    "origen_comunidad": lote["origen_comunidad"],
                    "periodo_referencia": lote["periodo_referencia"],
                    "interacciones": fragmento,
                },
                "lote_indice": lote_indice,
                "ciclo_indice": ciclo_indice,
                "cantidad": len(fragmento),
            })
    return ciclos


def obtener_raiz() -> Path:
    """Obtiene la raíz del proyecto, respetando parches en src.datos.ingesta.RAIZ."""
    try:
        import sys
        modulo = sys.modules.get("src.datos.ingesta")
        if modulo and hasattr(modulo, "RAIZ"):
            return Path(getattr(modulo, "RAIZ"))
    except Exception:
        pass
    return RAIZ


def validar_destino_ciclos(directorio_ciclos: Path | str, ciclos: list[dict], raiz: Path | None = None) -> tuple[Path, set[Path], set[Path]]:
    """Comprueba rutas y propiedad de archivos antes de escribir o retirar nada."""
    directorio_ciclos = Path(directorio_ciclos).resolve()
    base_raiz = raiz if raiz is not None else obtener_raiz()
    raiz_salida = (base_raiz / "salida").resolve()
    if raiz_salida not in directorio_ciclos.parents:
        raise ValueError("directorio_ciclos debe estar dentro de salida/")
    if directorio_ciclos.exists() and not directorio_ciclos.is_dir():
        raise ValueError("El destino de ciclos no es un directorio")

    def ruta_archivo(nombre: str) -> Path:
        if not isinstance(nombre, str) or not re.fullmatch(r"[A-Za-z0-9_-]+_lote\d+_ciclo\d+\.json", nombre):
            raise ValueError("Nombre de fragmento inválido")
        ruta = directorio_ciclos / nombre
        if ruta.is_symlink() or ruta.resolve().parent != directorio_ciclos or (ruta.exists() and not ruta.is_file()):
            raise ValueError("Ruta de fragmento no segura")
        return ruta

    ruta_manifiesto = directorio_ciclos / "manifiesto.json"
    if ruta_manifiesto.is_symlink() or (ruta_manifiesto.exists() and not ruta_manifiesto.is_file()):
        raise ValueError("La ruta del manifiesto no es segura")
    anteriores = set()
    if ruta_manifiesto.exists():
        with Path(ruta_manifiesto).open(encoding="utf-8-sig") as archivo:
            previo = json.load(archivo)
        if not isinstance(previo, dict) or not isinstance(previo.get("ciclos"), list):
            raise ValueError("El manifiesto anterior no es válido; no se modifica la carpeta")
        for entrada in previo["ciclos"]:
            if not isinstance(entrada, dict) or "archivo" not in entrada:
                raise ValueError("El manifiesto anterior no es válido")
            anteriores.add(ruta_archivo(entrada["archivo"]))
    nuevos = [ruta_archivo(c["archivo"]) for c in ciclos]
    if len(set(nuevos)) != len(nuevos):
        raise ValueError("Nombres de fragmentos repetidos")
    if any(p.exists() and p not in anteriores for p in nuevos):
        raise ValueError("Un fragmento sobrescribiría un archivo ajeno al manifiesto")
    return directorio_ciclos, anteriores, set(nuevos)


def guardar_ciclos(directorio_ciclos: Path | str, ciclos: list[dict]) -> Path:
    """Actualiza fragmentos y solo retira archivos del manifiesto anterior."""
    directorio_ciclos, anteriores, nuevos = validar_destino_ciclos(directorio_ciclos, ciclos)
    directorio_ciclos.mkdir(parents=True, exist_ok=True)
    for ciclo in ciclos:
        ruta = directorio_ciclos / ciclo["archivo"]
        ruta.write_text(json.dumps(ciclo["contenido"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ruta_manifiesto = directorio_ciclos / "manifiesto.json"
    manifiesto_data = {
        "ciclos": [
            {
                "archivo": c["archivo"],
                "lote_indice": c["lote_indice"],
                "ciclo_indice": c["ciclo_indice"],
                "cantidad": c["cantidad"],
            }
            for c in ciclos
        ]
    }
    ruta_manifiesto.write_text(json.dumps(manifiesto_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for anterior in anteriores - nuevos:
        anterior.unlink(missing_ok=True)
    return ruta_manifiesto
