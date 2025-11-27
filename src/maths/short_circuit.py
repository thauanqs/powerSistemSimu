from dataclasses import dataclass
from typing import Dict
import numpy as np
from models.faults import FaultSpec, FaultType, FaultResultBasic, FaultStudyResult

@dataclass
class ThreePhaseFaultResult:
    """Resultado básico de uma falta trifásica em uma barra."""
    fault_bus_id: str
    I_fault: complex                   # corrente de falta na barra em pu
    V_post: Dict[str, complex]         # tensões pós-falta em cada barra (pu)


class ShortCircuitSolver:
    """
    Resolve falta trifásica (simétrica) usando apenas a rede de sequência positiva.
    """

    def __init__(self, ybus: np.ndarray, pre_fault_voltages: Dict[str, complex], bus_index: Dict[str, int]):
        """
        :param ybus: matriz Ybus (sequência positiva), NxN, como numpy.array de complexos
        :param pre_fault_voltages: tensões pré-falta em pu, ex: {"B1": 1+0j, "B2": 0.98-0.02j, ...}
        :param bus_index: mapeia id da barra -> índice da matriz, ex: {"B1": 0, "B2": 1, ...}
        """
        self.ybus = ybus
        self.pre_v = pre_fault_voltages
        self.bus_index = bus_index

        # Calcula Zbus = Ybus^(-1)
        self.zbus = np.linalg.inv(self.ybus)

    def three_phase_fault(self, spec: FaultSpec) -> FaultStudyResult:
        """
        Calcula falta trifásica (simétrica) em uma barra.

        Usa apenas a rede de sequência positiva.
        """
        if spec.fault_type != FaultType.THREE_PHASE:
            raise ValueError("three_phase_fault só aceita FaultType.THREE_PHASE")

        fault_bus_id = spec.bus_id
        z_fault_pu = spec.z_fault_pu

        # índice da barra de falta na matriz
        k = self.bus_index[fault_bus_id]

        # tensão pré-falta na barra de falta (seq. positiva)
        V_pref = self.pre_v[fault_bus_id]

        # impedância de Thevenin vista da barra de falta
        Z_th = self.zbus[k, k]

        # corrente de falta na barra em falta (seq. positiva)
        I_fault = V_pref / (Z_th + z_fault_pu)

        # resultado por barra
        results: Dict[str, FaultResultBasic] = {}

        for bus_id, i in self.bus_index.items():
            Zik = self.zbus[i, k]
            V_post = self.pre_v[bus_id] - Zik * I_fault

            # por enquanto, corrente não nula só na barra em falta
            I_bus = I_fault if bus_id == fault_bus_id else 0+0j

            results[bus_id] = FaultResultBasic(
                bus_id=bus_id,
                v_pu=V_post,
                i_pu=I_bus,
            )

        return FaultStudyResult(
            spec=spec,
            fault_current_pu=I_fault,
            buses=results,
        )

from maths.power_flow import PowerFlow  # ajusta o caminho caso esteja diferente



def run_three_phase_fault_from_powerflow(
    pf: PowerFlow,
    bus_id: str,
    z_fault_pu: complex = 0+0j,
    description: str | None = None,
) -> FaultStudyResult:
    """
    Executa um estudo de falta trifásica (3φ) em qualquer sistema
    representado por um PowerFlow JÁ RESOLVIDO (pf.solve()).

    - pf: objeto PowerFlow com o sistema atual (o que o usuário montou)
    - bus_id: id da barra onde ocorre a falta (string)
    - z_fault_pu: impedância da falta em pu (0 -> falta sólida)
    - description: texto opcional descritivo
    """
    if description is None:
        description = f"Falta 3φ na barra {bus_id}"

    # Extrai dados de pré-falta e Ybus do PowerFlow
    ybus = pf.get_ybus_numpy()
    pre_v = pf.get_bus_voltages_complex_pu()
    bus_index = pf.get_bus_index_dict()

    solver = ShortCircuitSolver(ybus, pre_v, bus_index)

    spec = FaultSpec(
        bus_id=bus_id,
        fault_type=FaultType.THREE_PHASE,
        z_fault_pu=z_fault_pu,
        description=description,
    )

    return solver.three_phase_fault(spec)


#teste

if __name__ == "__main__":
    # - B1: barra slack, 1∠0 pu
    # - B2: barra de carga, 0.98∠-2° (pré-falta)
    #
    # Ybus fictícia só pra testar (2x2):
    Y = np.array([
        [10 - 30j, -10 + 30j],
        [-10 + 30j, 10 - 30j],
    ], dtype=complex)

    # Tensões pré-falta (em pu)
    pre_v = {
        "B1": 1.0 + 0.0j,
        "B2": 0.98 * np.exp(-1j * np.deg2rad(2.0)),  # módulo 0.98, ângulo -2°
    }

    bus_index = {
        "B1": 0,
        "B2": 1,
    }

    solver = ShortCircuitSolver(Y, pre_v, bus_index)

    # falta trifásica na barra B2, Zf = 0
    result = solver.three_phase_fault("B2", z_fault_pu=0 + 0j)

    print("Barra em falta:", result.fault_bus_id)
    print("Corrente de falta I_f (pu):", result.I_fault)
    print("Tensões pós-falta:")
    for bus_id, v in result.V_post.items():
        mag = np.abs(v)
        ang = np.rad2deg(np.angle(v))
        print(f"  {bus_id}: {mag:.4f} pu ∠ {ang:.2f}°")
