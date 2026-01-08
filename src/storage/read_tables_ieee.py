from cmath import pi
from enum import Enum

from models.bus import Bus, BusType
from models.line import Line
from maths.power_flow import PowerFlow
from storage.id_utils import norm_bus_id


class __ReadStep(Enum):
    TITLE = 0
    BUS_DATA = 1
    BRANCH_DATA = 2


def read_power_flow_from_ieee(path: str) -> PowerFlow:
    step = __ReadStep.TITLE
    powerFlow = PowerFlow(base=100.0)
    with open(path, "+r") as file:

        while True:
            line = file.readline()

            if step is __ReadStep.TITLE:
                line = file.readline()  # skip bus headers
                step = __ReadStep.BUS_DATA
                continue

            if step is __ReadStep.BUS_DATA and not line.startswith("-999"):
                powerFlow.add_bus(parse_bus(line))
                continue

            if step is __ReadStep.BUS_DATA:
                step = __ReadStep.BRANCH_DATA
                line = file.readline()  # skip branch headers
                continue

            if step is __ReadStep.BRANCH_DATA and not line.startswith("-999"):
                powerFlow.add_connection(parse_line(line))
                continue

            break
        return powerFlow


__degrees_to_radians = pi / 180.0


def parse_bus(line: str) -> Bus:
    # colunas 1-4
    raw = line[0:4]           # ex: "   1" ou "   0"
    num = int(raw)            # int("   0") funciona
    bid = norm_bus_id(raw)    # vira "0" ou "1"

    return Bus(
        id=bid,
        number=num,
        name=str(line[5:17]).strip(),            # colunas 7-17
        type=BusType(int(line[24:26])),          # colunas 25-26
        v=float(line[27:33]),                    # colunas 28-33
        o=float(line[33:40]) * __degrees_to_radians,  # colunas 34-40
        p_load=float(line[41:49]),               # colunas 42-49
        q_load=float(line[49:59]),               # colunas 50-59
        p_gen=float(line[59:67]),                # colunas 60-67
        q_gen=float(line[67:75]),                # colunas 68-75
        v_rated=float(line[76:83]),              # colunas 77-83
        q_max=float(line[90:98]),                # colunas 91-98
        q_min=float(line[98:106]),               # colunas 99-106
        g_shunt=float(line[106:114]),            # colunas 107-114
        b_shunt=float(line[114:122]),            # colunas 115-122
    )



def parse_line(line: str) -> Line:
    tap = float(line[77:82])
    return Line.from_z(
        tap_bus_id=norm_bus_id(line[0:4]),
        z_bus_id=norm_bus_id(line[5:9]),
        z=complex(
            # Columns 20-29   Branch resistance R, per unit (F) *
            float(line[20:29]),
            # Columns 30-40   Branch reactance X, per unit (F) * No zero impedance lines
            float(line[30:40]),
        ),
        # Columns 41-50   Line charging B, per unit (F) * (total line charging, +B)
        bc=float(line[41:50]),
        tap=tap if tap != 0 else 1.0,  # Columns 77-82   Transformer final turns ratio (F)
    )
