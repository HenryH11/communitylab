"""Presentación local de fechas; los procesos y comparaciones siguen en UTC."""

from datetime import datetime
import logging
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import streamlit as st


def zona_usuario() -> ZoneInfo:
    nombre = st.context.timezone
    if nombre:
        try:
            return ZoneInfo(nombre)
        except ZoneInfoNotFoundError:
            logging.getLogger(__name__).warning("Zona del navegador no reconocida: %s", nombre)
            st.warning("No se reconoce tu zona horaria; se muestran las horas en UTC.")
    return ZoneInfo("UTC")


def fecha_local(fecha: datetime, zona: ZoneInfo) -> str:
    if fecha.tzinfo is None:
        raise ValueError("La fecha requiere zona horaria.")
    local = fecha.astimezone(zona)
    desfase = local.strftime("%z")
    return f"{local:%d/%m/%Y %H:%M} · {zona.key} (UTC{desfase[:3]}:{desfase[3:]})"
