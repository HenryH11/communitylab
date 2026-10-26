"""Entrada de Marketing: nunca habilita el flujo interno de Datos."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.app.interfaz import render

render(modo_interno=False)
