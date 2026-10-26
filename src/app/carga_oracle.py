"""Cliente del ingestor exclusivo de la aplicacion interna."""

import hashlib
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


def conservar_conjunto(documento: dict, directorio: Path = Path("salida/ingesta")) -> Path:
    contenido = json.dumps(documento, ensure_ascii=False, sort_keys=True, indent=2)
    huella = hashlib.sha256(contenido.encode("utf-8")).hexdigest()
    directorio.mkdir(parents=True, exist_ok=True)
    ruta = directorio / f"{huella}.json"
    if ruta.exists():
        if ruta.read_text(encoding="utf-8") != contenido:
            raise ValueError("El archivo conservado no coincide con el lote")
    else:
        with ruta.open("x", encoding="utf-8") as archivo:
            archivo.write(contenido)
    return ruta


def solicitar(ruta: str, documento: dict | None = None, *, destino: dict | None = None,
              sintetico: bool = False) -> dict:
    url = os.environ.get("INGESTOR_URL", "").strip().rstrip("/")
    partes = urlsplit(url)
    if partes.scheme not in ("http", "https") or not partes.hostname or partes.username or partes.password or partes.query or partes.fragment:
        raise ValueError("Configurar INGESTOR_URL con la URL base privada del ingestor")
    if partes.path not in ("", "/"):
        raise ValueError("INGESTOR_URL debe ser la URL base, sin /sincronizar")
    headers = {"Content-Type": "application/json"}
    if destino is not None:
        headers["X-CommunityLab-Destino"] = destino["identidad"]
        headers["X-CommunityLab-Sintetico"] = str(sintetico).lower()
    datos = None if documento is None else json.dumps(documento, ensure_ascii=False).encode("utf-8")
    try:
        with urlopen(Request(url + ruta, data=datos, headers=headers), timeout=120) as respuesta:
            resultado = json.load(respuesta)
    except HTTPError as error:
        raise RuntimeError(
            f"Ingestor rechazo la operacion (HTTP {error.code}). Revisar sus logs; "
            "si la carga quedo incierta, verificar o reintentar el mismo documento."
        ) from error
    except (URLError, TimeoutError) as error:
        raise RuntimeError(
            "No se pudo completar la comunicacion con el ingestor. "
            "La carga puede haberse confirmado: verificar o reintentar el mismo documento."
        ) from error
    if not isinstance(resultado, dict):
        raise ValueError("Respuesta invalida del ingestor")
    return resultado


def render_carga(documento: dict) -> None:
    import streamlit as st

    st.subheader("Carga acumulativa en Oracle")
    st.caption("No borra registros ni sobrescribe IDs en conflicto. No publica en redes.")
    try:
        conservado = conservar_conjunto(documento)
    except (OSError, ValueError) as error:
        st.error(f"No se pudo conservar el lote para reintentos ({type(error).__name__}).")
        return
    st.caption(f"Copia local para reintentos: {conservado.name}")
    st.json({
        "registros": documento.get("total"),
        "spam_excluido": documento.get("total_spam_excluido"),
        "sin_fecha": sum(r.get("fecha") is None for r in documento.get("registros", [])),
    })
    st.download_button(
        "Descargar Conjunto Consultable", json.dumps(documento, ensure_ascii=False, indent=2),
        file_name="conjunto_consultable.json", mime="application/json",
    )
    sintetico = st.checkbox("El lote contiene datos sinteticos", value=True)
    if st.button("Comprobar destino Oracle"):
        st.session_state.pop("destino_ingesta", None)
        try:
            st.session_state["destino_ingesta"] = solicitar("/destino")
        except (ValueError, RuntimeError) as error:
            st.error(str(error))
    destino = st.session_state.get("destino_ingesta")
    if not destino:
        st.info("Comprueba el destino antes de cargar. El resultado puede descargarse y cargarse despues.")
        return
    st.write(f"Destino: {destino['nombre']} · {destino['entorno']} · {destino['total']} registros actuales")
    if sintetico and destino["entorno"] != "demostracion":
        st.error("Los datos sinteticos solo pueden cargarse en un destino de demostracion.")
        return
    huella = hashlib.sha256(json.dumps(documento, sort_keys=True).encode()).hexdigest()
    confirmado = st.checkbox(
        "Confirmo este lote y este destino para una carga acumulativa",
        key=f"confirmar_{destino['identidad']}_{huella}_{sintetico}",
    )
    cargar, verificar = st.columns(2)
    with cargar:
        enviar = st.button("Cargar y verificar en Oracle", disabled=not confirmado)
    with verificar:
        solo_verificar = st.button("Verificar lote sin escribir")
    if enviar or solo_verificar:
        try:
            if enviar:
                with st.spinner("Cargando lote..."):
                    resultado = solicitar("/sincronizar", documento, destino=destino, sintetico=sintetico)
                st.write("Respuesta de carga", resultado)
            with st.spinner("Comprobando registros por ID y contenido..."):
                evidencia = solicitar("/verificar", documento, destino=destino, sintetico=sintetico)
            st.json(evidencia)
            if evidencia.get("verificado") is not True:
                st.error("El lote no coincide completamente con Oracle. No se declara carga verificada.")
            else:
                st.success("Lote verificado por ID y contenido en Oracle.")
        except (ValueError, RuntimeError) as error:
            st.error(str(error))
