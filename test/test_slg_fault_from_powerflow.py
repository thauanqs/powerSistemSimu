import numpy as np
from pathlib import Path

import sys
from pathlib import Path

# adiciona a pasta src/ no sys.path
project_root = Path(__file__).resolve().parent.parent  # pasta raiz do projeto
src_path = project_root / "src"
sys.path.append(str(src_path))

from storage.storage import StorageFacade
from maths.short_circuit import ShortCircuitSolver
from models.faults import FaultSpec, FaultType, FaultStudyResult
from models.bus import BusType


def main():
    project_root = Path(__file__).resolve().parent.parent
    ieee_path = project_root / "assets" / "ieee_examples" / "ieee14cdf.txt"

    print(f"Carregando caso IEEE de: {ieee_path}")

    pf = StorageFacade.read_ieee_file(str(ieee_path))
    pf.solve()

    # monta dados de entrada pro ShortCircuitSolver
    ybus = pf.get_ybus_numpy()
    pre_v = pf.get_bus_voltages_complex_pu()
    bus_index = pf.get_bus_index_dict()

    solver = ShortCircuitSolver(ybus, pre_v, bus_index)  # por enquanto y0=y1=y2

    # escolhe uma barra PQ qualquer, por ex. a primeira não-SLACK
    candidate_buses = [b.id for b in pf.buses.values() if b.type != BusType.SLACK]
    fault_bus_id = candidate_buses[0]

    spec = FaultSpec(
        bus_id=fault_bus_id,
        fault_type=FaultType.SINGLE_LINE_TO_GROUND,
        z_fault_pu=0+0j,
        description=f"Falta SLG sólida na barra {fault_bus_id}",
    )

    result: FaultStudyResult = solver.single_line_to_ground_fault(spec)

    print()
    print(result.spec.description)
    If = result.fault_current_pu
    If_mag = np.abs(If)
    If_ang = np.rad2deg(np.angle(If))
    print(f"Corrente de falta fase A na barra {fault_bus_id}:")
    print(f"  |If| = {If_mag:.4f} pu, ∠If = {If_ang:.2f}°")

    print("\nTensões de fase A pós-falta por barra:")
    for bus_id, r in result.buses.items():
        v_mag = np.abs(r.v_pu)
        v_ang = np.rad2deg(np.angle(r.v_pu))
        print(f"  {bus_id}: |Va|={v_mag:.4f} pu, ∠Va={v_ang:7.2f}°")


if __name__ == "__main__":
    main()
