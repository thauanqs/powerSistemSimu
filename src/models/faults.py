from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Tuple


class FaultType(Enum):
    """
    Tipos de falta que vamos suportar.

    Por enquanto vamos usar só THREE_PHASE (3φ),
    mas já deixamos as outras preparadas para o futuro.
    """
    THREE_PHASE = "3φ"   # falta trifásica simétrica
    SINGLE_LINE_TO_GROUND = "SLG"          # falta monofásica terra
    LINE_TO_LINE = "LL"            # falta fase-fase
    DOUBLE_LINE_TO_GROUND = "DLG"          # falta dupla-fase terra


@dataclass
class FaultSpec:
    """
    Especificação de uma falta (entrada do estudo).

    Exemplo:
        FaultSpec(bus_id="B5", fault_type=FaultType.THREE_PHASE)
    """
    bus_id: str
    fault_type: FaultType
    z_fault_pu: complex = 0+0j
    description: str = ""
    phase: str = "A"


@dataclass
class FaultResultBasic:
    """
    Resultado básico em uma barra para um estudo de falta.

    v_pu: tensão em pu (seq. positiva / fase equivalente)
    i_pu: corrente em pu (seq. positiva / fase equivalente)
    """
    bus_id: str
    v_pu: complex
    i_pu: complex
    v_abc: Optional[Tuple[complex, complex, complex]] = None
    i_abc: Optional[Tuple[complex, complex, complex]] = None

@dataclass
class FaultStudyResult:
    """
    Resultado de um estudo de falta (por enquanto, 3φ):

    - spec: dados da falta (onde, tipo, Zf)
    - fault_current_pu: corrente de falta na barra em falta (pu)
    - buses: resultados por barra (tensão e corrente “local” simplificada)
    """
    spec: FaultSpec
    fault_current_pu: complex
    buses: Dict[str, FaultResultBasic]
