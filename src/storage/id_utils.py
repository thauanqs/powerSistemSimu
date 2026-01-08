from __future__ import annotations
from typing import Any

def norm_bus_id(x: Any) -> str:
    """
    Normaliza IDs de barra.
    - "   1" -> "1"
    - "001"  -> "1"
    - "Bus_1" -> "Bus_1" (não numérico fica como está)
    """
    s = str(x).strip()
    if s == "":
        raise ValueError("ID de barra vazio no arquivo de entrada.")
    try:
        return str(int(s))
    except ValueError:
        return s
