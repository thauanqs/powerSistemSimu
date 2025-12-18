from typing import Dict
import numpy as np

from models.faults import FaultSpec, FaultType, FaultResultBasic


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

    def three_phase_fault(self, spec: FaultSpec) -> Dict[str, FaultResultBasic]:
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

        # tensão pré-falta na barra de falta
        V_pref = self.pre_v[fault_bus_id]

        # impedância de Thevenin vista da barra de falta
        Z_th = self.zbus[k, k]

        # corrente de falta
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

        return results


# Teste isolado.

if __name__ == "__main__":
    # Exemplo de 2 barras inventado:
    # - B1: barra slack, 1∠0 pu
    # - B2: barra de carga, 0.98∠-2° (pré-falta)

    Y = np.array([
        [10 - 30j, -10 + 30j],
        [-10 + 30j, 10 - 30j],
    ], dtype=complex)

    pre_v = {
        "B1": 1.0 + 0.0j,
        "B2": 0.98 * np.exp(-1j * np.deg2rad(2.0)),  # módulo 0.98, ângulo -2°
    }

    bus_index = {
        "B1": 0,
        "B2": 1,
    }

    solver = ShortCircuitSolver(Y, pre_v, bus_index)

    # Monta o FaultSpec da falta trifásica em B2
    spec = FaultSpec(
        bus_id="B2",
        fault_type=FaultType.THREE_PHASE,
        z_fault_pu=0+0j,
        description="Falta 3φ sólida na barra B2",
    )

    results = solver.three_phase_fault(spec)

    print(f"Estudo: {spec.description}")
    print("Resultados por barra:")
    for bus_id, r in results.items():
        v_mag = np.abs(r.v_pu)
        v_ang = np.rad2deg(np.angle(r.v_pu))
        i_mag = np.abs(r.i_pu)
        print(f"  {bus_id}: |V|={v_mag:.4f} pu, ∠V={v_ang:6.2f}°, |I|={i_mag:.4f} pu")
