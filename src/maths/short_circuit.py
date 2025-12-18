from dataclasses import dataclass
from typing import Dict
import numpy as np
from models.faults import FaultSpec, FaultType, FaultResultBasic, FaultStudyResult
from maths.power_flow import PowerFlow  

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

    def __init__(self, ybus: np.ndarray, pre_fault_voltages: Dict[str, complex], bus_index: Dict[str, int], ybus_negative: np.ndarray | None = None, ybus_zero: np.ndarray | None = None):
        """
        :param ybus: matriz Ybus (sequência positiva), NxN, como numpy.array de complexos
        :param pre_fault_voltages: tensões pré-falta em pu, ex: {"B1": 1+0j, "B2": 0.98-0.02j, ...}
        :param bus_index: mapeia id da barra -> índice da matriz, ex: {"B1": 0, "B2": 1, ...}
        """
        self.y1 = ybus
        self.y2 = ybus_negative if ybus_negative is not None else ybus
        self.y0 = ybus_zero if ybus_zero is not None else ybus
        
        self.pre_v = pre_fault_voltages
        self.bus_index = bus_index

        self.z1 = np.linalg.inv(self.y1)
        self.z2 = np.linalg.inv(self.y2)
        self.z0 = np.linalg.inv(self.y0)

        self.ybus = self.y1
        self.zbus = self.z1

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

    def single_line_to_ground_fault(self, spec: FaultSpec) -> FaultStudyResult:
        """
        Falta monofásica fase-terra (SLG) em uma barra, assumindo pré-falta equilibrado.

        Por enquanto:
        - falta na fase A
        - redes 0, 1, 2 fornecidas via z0, z1, z2 (aqui estão iguais se não tiver dados separados)
        """
        if spec.fault_type != FaultType.SINGLE_LINE_TO_GROUND:
            raise ValueError("single_line_to_ground_fault só aceita FaultType.SINGLE_LINE_TO_GROUND")

        fault_bus_id = spec.bus_id
        k = self.bus_index[fault_bus_id]
        Zf = spec.z_fault_pu

        # tensão pré-falta de sequência positiva na barra de falta
        V1_pref = self.pre_v[fault_bus_id]

        # impedâncias de Thevenin na barra k para cada sequência
        Z1kk = self.z1[k, k]
        Z2kk = self.z2[k, k]
        Z0kk = self.z0[k, k]

        # correntes de sequência na barra de falta
        I1 = V1_pref / (Z1kk + Z2kk + Z0kk + 3 * Zf)
        I2 = I1
        I0 = I1

        # tensões de sequência pós-falta em todas as barras
        V1_post: Dict[str, complex] = {}
        V2_post: Dict[str, complex] = {}
        V0_post: Dict[str, complex] = {}

        for bus_id, i in self.bus_index.items():
            Z1ik = self.z1[i, k]
            Z2ik = self.z2[i, k]
            Z0ik = self.z0[i, k]

            V1_post[bus_id] = self.pre_v[bus_id] - Z1ik * I1
            V2_post[bus_id] = - Z2ik * I2
            V0_post[bus_id] = - Z0ik * I0

        # Transformação de componentes simétricas para fases
        # a = e^(j*120°)
        a = np.exp(1j * 2 * np.pi / 3)

        results: Dict[str, FaultResultBasic] = {}
        for bus_id in self.bus_index.keys():
            V0 = V0_post[bus_id]
            V1 = V1_post[bus_id]
            V2 = V2_post[bus_id]

            # tensão de fase A
            Va = V0 + V1 + V2

            # corrente: por enquanto só fase A na barra de falta
            if bus_id == fault_bus_id:
                I_phase_a = 3 * I1  # Ia = 3*I1 em falta SLG na fase A
            else:
                I_phase_a = 0 + 0j

            results[bus_id] = FaultResultBasic(
                bus_id=bus_id,
                v_pu=Va,         # interpretando como tensão de fase A
                i_pu=I_phase_a,  # corrente de fase A
            )

        # corrente de falta que vamos expor: Ia na barra de falta
        I_fault_phase_a = 3 * I1

        return FaultStudyResult(
            spec=spec,
            fault_current_pu=I_fault_phase_a,
            buses=results,
        )

    def line_to_line_fault(self, spec: FaultSpec) -> FaultStudyResult:
        """
        Falta fase–fase (LL), por exemplo entre fases B–C, em uma barra.

        Assumindo:
        - pré-falta equilibrado (só seq. positiva)
        - Z2 = Z1 (sequência negativa igual à positiva)
        - rede de sequência zero não participa da LL
        """
     
        if spec.fault_type != FaultType.LINE_TO_LINE:
            raise ValueError("line_to_line_fault só aceita FaultType.LINE_TO_LINE")

        fault_bus_id = spec.bus_id
        k = self.bus_index[fault_bus_id]
        Zf = spec.z_fault_pu

        V1_pref = self.pre_v[fault_bus_id]
        Z1kk = self.z1[k, k]
        Z2kk = self.z2[k, k]

        # Para falta LL (entre, por exemplo, B–C):
        # I1 =  V1 /(Z1 + Z2 + Zf)
        # I2 = -I1   (seq. negativa oposta à positiva)
        I1 = V1_pref / (Z1kk + Z2kk + Zf)
        I2 = -I1

        V1_post: Dict[str, complex] = {}
        V2_post: Dict[str, complex] = {}

        for bus_id, i in self.bus_index.items():
            Z1ik = self.z1[i, k]
            Z2ik = self.z2[i, k]

            V1_post[bus_id] = self.pre_v[bus_id] - Z1ik * I1
            V2_post[bus_id] = - Z2ik * I2

        # componente de sequência zero é zero: V0 = 0
        results: Dict[str, FaultResultBasic] = {}
        for bus_id in self.bus_index.keys():
            V1 = V1_post[bus_id]
            V2 = V2_post[bus_id]
            V0 = 0+0j

            # se a falta for, por ex., entre fases B–C:
            # Va = V0 + V1 + V2
            # Vb = V0 + a² V1 + a V2
            # Vc = V0 + a V1 + a² V2
            a = np.exp(1j * 2 * np.pi / 3)

            # vamos guardar, por enquanto, a tensão da fase em falta.
            # por simplicidade, podemos considerar que estamos olhando fase B.
            Vb = V0 + (a**2) * V1 + a * V2

            if bus_id == fault_bus_id:
                # corrente na fase em falta (ex.: B)
                I_phase = (V1 - V2) / Zf if Zf != 0 else 3 * I1  # forma simplificada
            else:
                I_phase = 0+0j

            results[bus_id] = FaultResultBasic(
                bus_id=bus_id,
                v_pu=Vb,
                i_pu=I_phase,
            )

        I_fault_phase = results[fault_bus_id].i_pu

        return FaultStudyResult(
            spec=spec,
            fault_current_pu=I_fault_phase,
            buses=results,
        )

    def double_line_to_ground_fault(self, spec: FaultSpec) -> FaultStudyResult:
        """
        Falta dupla linha-terra (DLG) nas fases B e C em uma barra.

        Assumimos condição de pré-falta equilibrada (apenas seq. positiva).
        Usa as impedâncias de Thevenin Z0, Z1 e Z2 vistas da barra de falta.
        """
        if spec.fault_type != FaultType.DOUBLE_LINE_TO_GROUND:
            raise ValueError(
                "double_line_to_ground_fault só aceita FaultType.DOUBLE_LINE_TO_GROUND"
            )

        fault_bus_id = spec.bus_id
        k = self.bus_index[fault_bus_id]
        Zf = spec.z_fault_pu

        # Tensão pré-falta de sequência positiva na barra em falta
        V1_pref = self.pre_v[fault_bus_id]

        # Impedâncias de Thevenin em cada sequência
        Z1 = self.z1[k, k]
        Z2 = self.z2[k, k]
        Z0 = self.z0[k, k]

        # Fórmulas clássicas para falta DLG: I1, I2, I0 :contentReference[oaicite:0]{index=0}
        Z0eq = Z0 + 3 * Zf
        denom = Z2 + Z0eq

        # Z2 || (Z0 + 3Zf)
        Z_par = (Z2 * Z0eq) / denom

        I1 = V1_pref / (Z1 + Z_par)
        I2 = (-I1) * (Z0eq / denom)
        I0 = (-I1) * (Z2 / denom)

        # Tensões de sequência pós-falta em todas as barras
        V0_post: dict[str, complex] = {}
        V1_post: dict[str, complex] = {}
        V2_post: dict[str, complex] = {}

        for bus_id, i in self.bus_index.items():
            Z1ik = self.z1[i, k]
            Z2ik = self.z2[i, k]
            Z0ik = self.z0[i, k]

            V1_post[bus_id] = self.pre_v[bus_id] - Z1ik * I1
            V2_post[bus_id] = -Z2ik * I2
            V0_post[bus_id] = -Z0ik * I0

        # Transformação para fase: vamos mostrar a fase B (uma das fases em falta)
        a = np.exp(1j * 2 * np.pi / 3)

        results: dict[str, FaultResultBasic] = {}
        for bus_id in self.bus_index.keys():
            V0 = V0_post[bus_id]
            V1b = V1_post[bus_id]
            V2b = V2_post[bus_id]

            # Tensão de fase B: Vb = V0 + a² V1 + a V2
            Vb = V0 + (a**2) * V1b + a * V2b

            # Corrente: só consideramos a corrente da fase B na barra em falta
            if bus_id == fault_bus_id:
                Ib = I0 + (a**2) * I1 + a * I2
            else:
                Ib = 0.0 + 0.0j

            results[bus_id] = FaultResultBasic(
                bus_id=bus_id,
                v_pu=Vb,   # tensão da fase B (uma das fases em falta)
                i_pu=Ib,   # corrente da fase B
            )

        I_fault = results[fault_bus_id].i_pu

        return FaultStudyResult(
            spec=spec,
            fault_current_pu=I_fault,
            buses=results,
        )

def _build_solver_from_powerflow(pf: PowerFlow) -> ShortCircuitSolver:
    """
    Monta o ShortCircuitSolver usando as três matrizes de sequência
    calculadas no fluxo de potência.
    Pressupõe que pf.solve() já foi chamado.
    """
    y1, y2, y0 = pf.get_ybus_numpy_sequences()
    pre_v = pf.get_bus_voltages_complex_pu()
    bus_index = pf.get_bus_index_dict()

    solver = ShortCircuitSolver(
        ybus=y1,                    # sequência positiva
        pre_fault_voltages=pre_v,
        bus_index=bus_index,
        ybus_negative=y2,           # sequência negativa
        ybus_zero=y0,               # sequência zero
    )
    return solver


def run_three_phase_fault_from_powerflow(
    pf: PowerFlow,
    bus_id: str,
    z_fault_pu: complex = 0+0j,
    description: str | None = None,
) -> FaultStudyResult:
    """
        Executa um estudo de falta trifásica (3φ) em qualquer sistema
        representado por um PowerFlow JÁ RESOLVIDO (pf.solve()).
        """
    if description is None:
        description = f"Falta 3φ na barra {bus_id}"

    solver = _build_solver_from_powerflow(pf)

    spec = FaultSpec(
        bus_id=bus_id,
        fault_type=FaultType.THREE_PHASE,
        z_fault_pu=z_fault_pu,
        description=description,
    )

    return solver.three_phase_fault(spec)


def run_slg_fault_from_powerflow(
    pf: PowerFlow,
    bus_id: str,
    z_fault_pu: complex = 0 + 0j,
    description: str | None = None,
) -> FaultStudyResult:
    """
    Falta monofásica fase–terra (SLG) usando as três redes de sequência.
    """
    if description is None:
        description = f"Falta SLG sólida na barra {bus_id}"

    solver = _build_solver_from_powerflow(pf)

    spec = FaultSpec(
        bus_id=bus_id,
        fault_type=FaultType.SINGLE_LINE_TO_GROUND,
        z_fault_pu=z_fault_pu,
        description=description,
    )

    return solver.single_line_to_ground_fault(spec)



def run_ll_fault_from_powerflow(
    pf: PowerFlow,
    bus_id: str,
    z_fault_pu: complex = 0 + 0j,
    description: str | None = None,
) -> FaultStudyResult:
    """
    Falta fase–fase (LL) usando as redes de sequência positiva e negativa.
    """
    if description is None:
        description = f"Falta LL sólida na barra {bus_id}"

    solver = _build_solver_from_powerflow(pf)

    spec = FaultSpec(
        bus_id=bus_id,
        fault_type=FaultType.LINE_TO_LINE,
        z_fault_pu=z_fault_pu,
        description=description,
    )

    return solver.line_to_line_fault(spec)


def run_dlg_fault_from_powerflow(
    pf: PowerFlow,
    bus_id: str,
    z_fault_pu: complex = 0 + 0j,
    description: str | None = None,
) -> FaultStudyResult:
    """
    Falta dupla fase–terra (DLG) usando as três redes de sequência.
    """
    if description is None:
        description = f"Falta DLG sólida na barra {bus_id}"

    solver = _build_solver_from_powerflow(pf)

    spec = FaultSpec(
        bus_id=bus_id,
        fault_type=FaultType.DOUBLE_LINE_TO_GROUND,
        z_fault_pu=z_fault_pu,
        description=description,
    )

    return solver.double_line_to_ground_fault(spec)



