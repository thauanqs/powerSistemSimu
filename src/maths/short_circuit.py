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


def safe_inv(Y: np.ndarray, eps: float = 1e-9) -> np.ndarray:
    try:
        return np.linalg.inv(Y)
    except np.linalg.LinAlgError:
        # Regulariza a diagonal (equivale a colocar um shunt absurdamente grande -> quase aberto)
        Yreg = Y.copy().astype(complex)
        idx = np.diag_indices_from(Yreg)
        Yreg[idx] += eps
        try:
            return np.linalg.inv(Yreg)
        except np.linalg.LinAlgError:
            # Último recurso
            return np.linalg.pinv(Yreg)


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

        self.z1 = safe_inv(self.y1)
        self.z2 = safe_inv(self.y2)
        self.z0 = safe_inv(self.y0)

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
        A = self._symm_matrix_A()
        Iabc_fault = tuple((A @ np.array([0+0j, I_fault, 0+0j], dtype=complex)).tolist())

        # resultado por barra
        results: Dict[str, FaultResultBasic] = {}

        for bus_id, i in self.bus_index.items():
            Zik = self.zbus[i, k]
            V_post = self.pre_v[bus_id] - Zik * I_fault

            # por enquanto, corrente não nula só na barra em falta
            I_bus = I_fault if bus_id == fault_bus_id else 0+0j
            Vabc = tuple((A @ np.array([0+0j, V_post, 0+0j], dtype=complex)).tolist())
            Iabc = Iabc_fault if bus_id == fault_bus_id else (0+0j, 0+0j, 0+0j)

            results[bus_id] = FaultResultBasic(
                bus_id=bus_id,
                v_pu=V_post,
                i_pu=I_bus,
                v_abc=Vabc,
                i_abc=Iabc,
            )

        return FaultStudyResult(
            spec=spec,
            fault_current_pu=I_fault,
            buses=results,
        )
    

    # Componentes simétricas

    @staticmethod
    def _symm_matrix_A() -> np.ndarray:
        """Matriz A tal que [Va,Vb,Vc]^T = A [V0,V1,V2]^T e [Ia,Ib,Ic]^T = A [I0,I1,I2]^T."""
        a = np.exp(1j * 2 * np.pi / 3)
        return np.array(
            [
                [1, 1, 1],
                [1, a**2, a],
                [1, a, a**2],
            ],
            dtype=complex,
        )

    @staticmethod
    def _phase_to_index(phase: str) -> int:
        phase = phase.upper().strip()
        if phase == "A":
            return 0
        if phase == "B":
            return 1
        if phase == "C":
            return 2
        raise ValueError(f"Fase inválida: {phase!r}. Use 'A', 'B' ou 'C'.")

    @staticmethod
    def _parse_fault_phases(spec: FaultSpec) -> tuple[int, int | None, int]:
        """
        Retorna (p, q, r):
        - p = fase principal (A/B/C) (sempre existe)
        - q = segunda fase (LL/DLG) ou None (SLG)
        - r = fase restante (a que NÃO participa em LL/DLG) ou uma das não-faltosas em SLG
        """
        ft = spec.fault_type

        if ft == FaultType.SINGLE_LINE_TO_GROUND:
            p = ShortCircuitSolver._phase_to_index(spec.phase)
            others = [0, 1, 2]
            others.remove(p)
            r = others[0]
            return p, None, r

        if ft == FaultType.LINE_TO_LINE:
            ph = spec.phase.upper().strip()
            if ph not in ("AB", "BC", "CA"):
                raise ValueError(f"Fases inválidas para LL: {spec.phase!r}. Use 'AB', 'BC' ou 'CA'.")
            p = ShortCircuitSolver._phase_to_index(ph[0])
            q = ShortCircuitSolver._phase_to_index(ph[1])
            r = ({0, 1, 2} - {p, q}).pop()
            return p, q, r

        if ft == FaultType.DOUBLE_LINE_TO_GROUND:
            ph = spec.phase.upper().strip()
            if ph not in ("ABG", "BCG", "CAG"):
                raise ValueError(f"Fases inválidas para DLG: {spec.phase!r}. Use 'ABG', 'BCG' ou 'CAG'.")
            p = ShortCircuitSolver._phase_to_index(ph[0])
            q = ShortCircuitSolver._phase_to_index(ph[1])
            r = ({0, 1, 2} - {p, q}).pop()
            return p, q, r

        raise ValueError(f"Tipo de falta não suportado aqui: {ft}")

    def _solve_sequence_currents_at_fault_bus(self, spec: FaultSpec) -> tuple[complex, complex, complex]:
        """
        Resolve I0, I1, I2 na barra da falta (Thevenin por sequência) impondo
        condições de contorno em abc. Isso permite escolher A/B/C (ou AB/BC/CA, ABG/BCG/CAG)
        sem "gambiarras" e corrige LL sólida.

        Retorna: (I0, I1, I2)
        """
        fault_bus_id = spec.bus_id
        k = self.bus_index[fault_bus_id]

        Zf = spec.z_fault_pu
        V1_pref = self.pre_v[fault_bus_id]

        Z0kk = self.z0[k, k]
        Z1kk = self.z1[k, k]
        Z2kk = self.z2[k, k]

        A = self._symm_matrix_A()

        # Iabc = A @ [I0,I1,I2]
        Irow = A

        # V012 = [ -Z0 I0, V1_pref - Z1 I1, -Z2 I2 ] = c + D x
        D = np.diag([-Z0kk, -Z1kk, -Z2kk]).astype(complex)
        c = np.array([0 + 0j, V1_pref, 0 + 0j], dtype=complex)

        # Vabc = A @ (c + D x) = Vconst + Vrow x
        Vconst = A @ c
        Vrow = A @ D

        ft = spec.fault_type
        p, q, r = self._parse_fault_phases(spec)

        rows = []
        rhs = []

        if ft == FaultType.SINGLE_LINE_TO_GROUND:
            others = [0, 1, 2]
            others.remove(p)

            rows.append(Irow[others[0]])
            rhs.append(0 + 0j)

            rows.append(Irow[others[1]])
            rhs.append(0 + 0j)

            rows.append(Vrow[p] - Zf * Irow[p])
            rhs.append(-(Vconst[p]))

        elif ft == FaultType.LINE_TO_LINE:
            assert q is not None
            rows.append(Irow[r])
            rhs.append(0 + 0j)

            rows.append(Irow[p] + Irow[q])
            rhs.append(0 + 0j)

            rows.append((Vrow[p] - Vrow[q]) - Zf * Irow[p])
            rhs.append(-(Vconst[p] - Vconst[q]))

        elif ft == FaultType.DOUBLE_LINE_TO_GROUND:
            assert q is not None
            rows.append(Irow[r])
            rhs.append(0 + 0j)

            sum_I = Irow[p] + Irow[q]
            rows.append(Vrow[p] - Zf * sum_I)
            rhs.append(-(Vconst[p]))

            rows.append(Vrow[q] - Zf * sum_I)
            rhs.append(-(Vconst[q]))

        else:
            raise ValueError(f"Tipo de falta não suportado: {ft}")

        M = np.vstack(rows).astype(complex)
        b = np.array(rhs, dtype=complex)

        I0, I1, I2 = np.linalg.solve(M, b)
        return I0, I1, I2


    def single_line_to_ground_fault(self, spec: FaultSpec) -> FaultStudyResult:
        """
        Falta monofásica fase–terra (SLG) em uma barra.

        Suporta escolha de fase (A/B/C) via spec.phase e retorna Va,Vb,Vc e Ia,Ib,Ic.
        """
        if spec.fault_type != FaultType.SINGLE_LINE_TO_GROUND:
            raise ValueError("single_line_to_ground_fault só aceita FaultType.SINGLE_LINE_TO_GROUND")

        fault_bus_id = spec.bus_id
        k = self.bus_index[fault_bus_id]

        I0, I1, I2 = self._solve_sequence_currents_at_fault_bus(spec)
        A = self._symm_matrix_A()

        V0_post: Dict[str, complex] = {}
        V1_post: Dict[str, complex] = {}
        V2_post: Dict[str, complex] = {}

        for bus_id, i in self.bus_index.items():
            Z0ik = self.z0[i, k]
            Z1ik = self.z1[i, k]
            Z2ik = self.z2[i, k]

            V0_post[bus_id] = -Z0ik * I0
            V1_post[bus_id] = self.pre_v[bus_id] - Z1ik * I1
            V2_post[bus_id] = -Z2ik * I2

        Iabc_fault = tuple((A @ np.array([I0, I1, I2], dtype=complex)).tolist())
        p = self._phase_to_index(spec.phase)

        results: Dict[str, FaultResultBasic] = {}
        for bus_id in self.bus_index.keys():
            Vabc = tuple((A @ np.array([V0_post[bus_id], V1_post[bus_id], V2_post[bus_id]], dtype=complex)).tolist())
            Iabc = Iabc_fault if bus_id == fault_bus_id else (0 + 0j, 0 + 0j, 0 + 0j)

            results[bus_id] = FaultResultBasic(
                bus_id=bus_id,
                v_pu=Vabc[p],
                i_pu=Iabc[p],
                v_abc=Vabc,
                i_abc=Iabc,
            )

        return FaultStudyResult(spec=spec, fault_current_pu=results[fault_bus_id].i_pu, buses=results)

    def line_to_line_fault(self, spec: FaultSpec) -> FaultStudyResult:
        """
        Falta fase–fase (LL) em uma barra.

        Suporta escolha AB/BC/CA via spec.phase e retorna Va,Vb,Vc e Ia,Ib,Ic.
        """
        if spec.fault_type != FaultType.LINE_TO_LINE:
            raise ValueError("line_to_line_fault só aceita FaultType.LINE_TO_LINE")

        fault_bus_id = spec.bus_id
        k = self.bus_index[fault_bus_id]

        I0, I1, I2 = self._solve_sequence_currents_at_fault_bus(spec)
        A = self._symm_matrix_A()

        V0_post: Dict[str, complex] = {}
        V1_post: Dict[str, complex] = {}
        V2_post: Dict[str, complex] = {}

        for bus_id, i in self.bus_index.items():
            Z0ik = self.z0[i, k]
            Z1ik = self.z1[i, k]
            Z2ik = self.z2[i, k]

            V0_post[bus_id] = -Z0ik * I0
            V1_post[bus_id] = self.pre_v[bus_id] - Z1ik * I1
            V2_post[bus_id] = -Z2ik * I2

        Iabc_fault = tuple((A @ np.array([I0, I1, I2], dtype=complex)).tolist())
        p, _, _ = self._parse_fault_phases(spec)

        results: Dict[str, FaultResultBasic] = {}
        for bus_id in self.bus_index.keys():
            Vabc = tuple((A @ np.array([V0_post[bus_id], V1_post[bus_id], V2_post[bus_id]], dtype=complex)).tolist())
            Iabc = Iabc_fault if bus_id == fault_bus_id else (0 + 0j, 0 + 0j, 0 + 0j)

            results[bus_id] = FaultResultBasic(
                bus_id=bus_id,
                v_pu=Vabc[p],
                i_pu=Iabc[p],
                v_abc=Vabc,
                i_abc=Iabc,
            )

        return FaultStudyResult(spec=spec, fault_current_pu=results[fault_bus_id].i_pu, buses=results)

    def double_line_to_ground_fault(self, spec: FaultSpec) -> FaultStudyResult:
        """
        Falta dupla fase–terra (DLG) em uma barra.

        Suporta escolha ABG/BCG/CAG via spec.phase e retorna Va,Vb,Vc e Ia,Ib,Ic.
        """
        if spec.fault_type != FaultType.DOUBLE_LINE_TO_GROUND:
            raise ValueError("double_line_to_ground_fault só aceita FaultType.DOUBLE_LINE_TO_GROUND")

        fault_bus_id = spec.bus_id
        k = self.bus_index[fault_bus_id]

        I0, I1, I2 = self._solve_sequence_currents_at_fault_bus(spec)
        A = self._symm_matrix_A()

        V0_post: Dict[str, complex] = {}
        V1_post: Dict[str, complex] = {}
        V2_post: Dict[str, complex] = {}

        for bus_id, i in self.bus_index.items():
            Z0ik = self.z0[i, k]
            Z1ik = self.z1[i, k]
            Z2ik = self.z2[i, k]

            V0_post[bus_id] = -Z0ik * I0
            V1_post[bus_id] = self.pre_v[bus_id] - Z1ik * I1
            V2_post[bus_id] = -Z2ik * I2

        Iabc_fault = tuple((A @ np.array([I0, I1, I2], dtype=complex)).tolist())
        p, _, _ = self._parse_fault_phases(spec)

        results: Dict[str, FaultResultBasic] = {}
        for bus_id in self.bus_index.keys():
            Vabc = tuple((A @ np.array([V0_post[bus_id], V1_post[bus_id], V2_post[bus_id]], dtype=complex)).tolist())
            Iabc = Iabc_fault if bus_id == fault_bus_id else (0 + 0j, 0 + 0j, 0 + 0j)

            results[bus_id] = FaultResultBasic(
                bus_id=bus_id,
                v_pu=Vabc[p],
                i_pu=Iabc[p],
                v_abc=Vabc,
                i_abc=Iabc,
            )

        return FaultStudyResult(spec=spec, fault_current_pu=results[fault_bus_id].i_pu, buses=results)



def _build_solver_from_powerflow(
    pf: PowerFlow,
    source_bus_id: str | None = None,
    z1_source_pu: complex | None = None,
    z2_source_pu: complex | None = None,
    z0_source_pu: complex | None = None,
    generators=None,  # <- NOVO: lista de Generator
) -> ShortCircuitSolver:
    y1, y2, y0 = pf.get_ybus_numpy_sequences()
    pre_v = pf.get_bus_voltages_complex_pu()
    bus_index = pf.get_bus_index_dict()

    # Fonte Thevenin (se você ainda estiver usando)
    if source_bus_id is not None:
        k = bus_index[source_bus_id]

        def add_shunt(Y: np.ndarray, z: complex | None) -> None:
            if z is None:
                return
            if abs(z) < 1e-12:
                raise ValueError("Impedância da fonte muito pequena (próxima de 0).")
            Y[k, k] += 1 / z

        add_shunt(y1, z1_source_pu)
        add_shunt(y2, z2_source_pu)
        add_shunt(y0, z0_source_pu)

    # NOVO: contribuição dos geradores como shunt (sem importar controller)
    if generators:
        for gen in generators:
            if gen.bus_id not in bus_index:
                continue
            k = bus_index[gen.bus_id]

            Z1 = 1j * gen.sc.x1_pu
            Z2 = 1j * gen.sc.x2_pu

            if gen.sc.grounded:
                Z0 = 1j * (gen.sc.x0_pu + 3.0 * gen.sc.xn_pu)
            else:
                Z0 = None

            def add_shunt_Z(Y, Z):
                if Z is None:
                    return
                if abs(Z) < 1e-12:
                    return
                Y[k, k] += 1 / Z

            add_shunt_Z(y1, Z1)
            add_shunt_Z(y2, Z2)
            add_shunt_Z(y0, Z0)

    return ShortCircuitSolver(
        ybus=y1,
        pre_fault_voltages=pre_v,
        bus_index=bus_index,
        ybus_negative=y2,
        ybus_zero=y0,
    )

def run_three_phase_fault_from_powerflow(
    pf: PowerFlow,
    bus_id: str,
    z_fault_pu: complex = 0+0j,
    description: str | None = None,
    source_bus_id: str | None = None,
    z1_source_pu: complex | None = None,
    z2_source_pu: complex | None = None,
    z0_source_pu: complex | None = None,
    generators=None,
) -> FaultStudyResult:
    """
        Executa um estudo de falta trifásica (3φ) em qualquer sistema
        representado por um PowerFlow JÁ RESOLVIDO (pf.solve()).
        """
    if description is None:
        description = f"Falta 3φ na barra {bus_id}"

    solver = _build_solver_from_powerflow(
        pf,
        source_bus_id=source_bus_id,
        z1_source_pu=z1_source_pu,
        z2_source_pu=z2_source_pu,
        z0_source_pu=z0_source_pu,
        generators=generators,
    )

    spec = FaultSpec(
        bus_id=bus_id,
        fault_type=FaultType.THREE_PHASE,
        z_fault_pu=z_fault_pu,
        description=description,
        phase="A",
    )
    return solver.three_phase_fault(spec)


def run_slg_fault_from_powerflow(
    pf: PowerFlow,
    bus_id: str,
    z_fault_pu: complex = 0 + 0j,
    phase: str = "A",
    description: str | None = None,
    source_bus_id: str | None = None,
    z1_source_pu: complex | None = None,
    z2_source_pu: complex | None = None,
    z0_source_pu: complex | None = None,
    generators=None,
) -> FaultStudyResult:
    if description is None:
        description = f"Falta SLG sólida na barra {bus_id}"

    solver = _build_solver_from_powerflow(
        pf,
        source_bus_id=source_bus_id,
        z1_source_pu=z1_source_pu,
        z2_source_pu=z2_source_pu,
        z0_source_pu=z0_source_pu,
        generators=generators,
    )

    spec = FaultSpec(
        bus_id=bus_id,
        fault_type=FaultType.SINGLE_LINE_TO_GROUND,
        z_fault_pu=z_fault_pu,
        description=description,
        phase=phase,
    )

    return solver.single_line_to_ground_fault(spec)


def run_ll_fault_from_powerflow(
    pf: PowerFlow,
    bus_id: str,
    z_fault_pu: complex = 0 + 0j,
    phase: str = "BC",
    description: str | None = None,
    source_bus_id: str | None = None,
    z1_source_pu: complex | None = None,
    z2_source_pu: complex | None = None,
    z0_source_pu: complex | None = None,
    generators=None,
) -> FaultStudyResult:
    if description is None:
        description = f"Falta LL sólida na barra {bus_id}"

    solver = _build_solver_from_powerflow(
        pf,
        source_bus_id=source_bus_id,
        z1_source_pu=z1_source_pu,
        z2_source_pu=z2_source_pu,
        z0_source_pu=z0_source_pu,
        generators=generators,
    )

    spec = FaultSpec(
        bus_id=bus_id,
        fault_type=FaultType.LINE_TO_LINE,
        z_fault_pu=z_fault_pu,
        description=description,
        phase=phase,
    )

    return solver.line_to_line_fault(spec)


def run_dlg_fault_from_powerflow(
    pf: PowerFlow,
    bus_id: str,
    z_fault_pu: complex = 0 + 0j,
    phase: str = "BCG",
    description: str | None = None,
    source_bus_id: str | None = None,
    z1_source_pu: complex | None = None,
    z2_source_pu: complex | None = None,
    z0_source_pu: complex | None = None,
    generators=None,
) -> FaultStudyResult:
    if description is None:
        description = f"Falta DLG sólida na barra {bus_id}"

    solver = _build_solver_from_powerflow(
        pf,
        source_bus_id=source_bus_id,
        z1_source_pu=z1_source_pu,
        z2_source_pu=z2_source_pu,
        z0_source_pu=z0_source_pu,
        generators=generators,
    )

    spec = FaultSpec(
        bus_id=bus_id,
        fault_type=FaultType.DOUBLE_LINE_TO_GROUND,
        z_fault_pu=z_fault_pu,
        description=description,
        phase=phase,
    )

    return solver.double_line_to_ground_fault(spec)




