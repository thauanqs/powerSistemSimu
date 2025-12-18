import numpy as np
from pathlib import Path

from storage.storage import StorageFacade
from maths.short_circuit import run_three_phase_fault_from_powerflow
from models.bus import BusType


def main():
    project_root = Path(__file__).resolve().parent.parent
    ieee_path = project_root / "assets" / "ieee_examples" / "ieee14cdf.txt"

    print(f"Carregando caso IEEE de: {ieee_path}")

    pf = StorageFacade.read_ieee_file(str(ieee_path))

    pf.solve()

    # Escolhe uma barra não-SLACK só pra testar
    candidate_buses = [b.id for b in pf.buses.values() if b.type != BusType.SLACK]
    fault_bus_id = candidate_buses[0]

    result = run_three_phase_fault_from_powerflow(
        pf,
        fault_bus_id,
        z_fault_pu=0+0j,
        description=f"Falta 3φ sólida na barra {fault_bus_id}",
    )

    print()
    print(f"Estudo: {result.spec.description}")
    print(f"Corrente de falta na barra {fault_bus_id}:")
    If = result.fault_current_pu
    If_mag = np.abs(If)
    If_ang = np.rad2deg(np.angle(If))
    print(f"  |If| = {If_mag:.4f} pu, ∠If = {If_ang:.2f}°")

    print("\nResultados por barra (pós-falta):")
    for bus_id, r in result.buses.items():
        v_mag = np.abs(r.v_pu)
        v_ang = np.rad2deg(np.angle(r.v_pu))
        i_mag = np.abs(r.i_pu)
        print(f"  {bus_id}: |V|={v_mag:.4f} pu, ∠V={v_ang:6.2f}°, |I|={i_mag:.4f} pu")


if __name__ == "__main__":
    main()
