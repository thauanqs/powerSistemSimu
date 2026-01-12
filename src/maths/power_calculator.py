import cmath
from math import cos, sin

from models.bus import Bus
from models.y_bus_square_matrix import YBusSquareMatrix

def _bii_total(bus_i: Bus, buses: dict[str, Bus], Y: YBusSquareMatrix) -> float:
    """
    Retorna B_ii efetivo = imag(Y_ii) + soma(line_charging/2) de todas as conexões incidentes.
    No teu YBusSquareMatrix, o bc não entra na matriz, então precisamos somar aqui.
    """
    bc_half_sum = 0.0
    for b in buses.values():
        if b.index == bus_i.index:
            continue
        bc_half_sum += Y.getBc(bus_i.index, b.index) / 2.0
    return float(Y.y_matrix[bus_i.index][bus_i.index].imag) + bc_half_sum


# P_i = ∑ |Vi| |Vj| |Yij| cos(θij - δi + δj)
#       j
def calcP(
    self: Bus,
    buses: dict[str, "Bus"],
    Y: YBusSquareMatrix,
) -> float:
    sum: float = 0.0
    for bus in buses.values():
        y = abs(Y.y_matrix[self.index][bus.index])
        theta = cmath.phase(Y.y_matrix[self.index][bus.index])
        sum += self.v * bus.v * y * cos(theta - self.o + bus.o)
    return sum


# Q_i = - ∑ |Vi| |Vj| |Yij| sin(θij - δi + δj)
#         j
def calcQ(
    self: Bus,
    buses: dict[str, "Bus"],
    Y: YBusSquareMatrix,
) -> float:
    s = 0.0
    for bus in buses.values():
        y = abs(Y.y_matrix[self.index][bus.index])
        theta = cmath.phase(Y.y_matrix[self.index][bus.index])
        s += self.v * bus.v * y * sin(theta - self.o + bus.o)
    return -s


@staticmethod
def dPdO(  # dPi/dOj
    i_id: str,
    j_id: str,
    buses: dict[str, "Bus"],
    Y: YBusSquareMatrix,
) -> float:
    if i_id != j_id:
        bus_i = buses[i_id]
        bus_j = buses[j_id]
        y_ij = abs(Y.y_matrix[bus_i.index][bus_j.index])
        theta_ij = cmath.phase(Y.y_matrix[bus_i.index][bus_j.index])
        return -bus_i.v * bus_j.v * y_ij * sin(theta_ij - bus_i.o + bus_j.o)

    bus = buses[i_id]
    b = Y.y_matrix[bus.index][bus.index].imag
    return -bus.v * bus.v * b - calcQ(bus, buses, Y)



def dPdV(  # dPi/dOj
    i_id: str,
    j_id: str,
    buses: dict[str, "Bus"],
    Y: YBusSquareMatrix,
) -> float:
    if i_id != j_id:
        bus_i = buses[i_id]
        bus_j = buses[j_id]
        y_ij = abs(Y.y_matrix[bus_i.index][bus_j.index])
        theta_ij = cmath.phase(Y.y_matrix[bus_i.index][bus_j.index])
        return bus_i.v * y_ij * cos(theta_ij - bus_i.o + bus_j.o)

    bus = buses[i_id]
    g = Y.y_matrix[bus.index][bus.index].real
    return bus.v * g + calcP(bus, buses, Y) / bus.v


def dQdO(  # dPi/dOj
    i_id: str,
    j_id: str,
    buses: dict[str, "Bus"],
    Y: YBusSquareMatrix,
) -> float:
    if i_id != j_id:
        bus_i = buses[i_id]
        bus_j = buses[j_id]
        y_ij = abs(Y.y_matrix[bus_i.index][bus_j.index])
        theta_ij = cmath.phase(Y.y_matrix[bus_i.index][bus_j.index])
        return -bus_i.v * bus_j.v * y_ij * cos(theta_ij - bus_i.o + bus_j.o)

    bus = buses[i_id]
    g = Y.y_matrix[bus.index][bus.index].real
    return -bus.v * bus.v * g + calcP(bus, buses, Y)


def dQdV(  # dPi/dOj
    i_id: str,
    j_id: str,
    buses: dict[str, "Bus"],
    Y: YBusSquareMatrix,
) -> float:
    if i_id != j_id:
        bus_i = buses[i_id]
        bus_j = buses[j_id]
        y_ij = abs(Y.y_matrix[bus_i.index][bus_j.index])
        theta_ij = cmath.phase(Y.y_matrix[bus_i.index][bus_j.index])
        return -bus_i.v * y_ij * sin(theta_ij - bus_i.o + bus_j.o)

    bus = buses[i_id]
    b = Y.y_matrix[bus.index][bus.index].imag
    return -bus.v * b + calcQ(bus, buses, Y) / bus.v
