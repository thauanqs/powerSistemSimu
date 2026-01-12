from __future__ import annotations
from models.bus_square_matrix import BusSquareMatrix


class YBusSquareMatrix:
    def __init__(self, log_print: bool = False):
        self.__m: BusSquareMatrix = BusSquareMatrix()
        self.__log_print: bool = log_print
        self.__bc: dict[str, float] = {}

    def __getIndex(self, i: int, j: int) -> str:
        if i > j:
            return f"{i}_{j}"
        else:
            return f"{j}_{i}"

    def getBc(self, i: int, j: int) -> float:
        index = self.__getIndex(i, j)
        return self.__bc[index] if index in self.__bc else 0.0

    # Caso 1 - Adicionar um barramento e conecta a terra. Aumenta a ordem da matriz.
    def add_bus(self, bus_id: str) -> None:
        self.__m.add_bus(bus_id, complex(0, 0))



    # Caso 4 - Conectar um barramento a outro barramento. Não aumenta a ordem da matriz.
    def connect_bus_to_bus(
    self,
    y: complex,
    source: int,
    target: int,
    bc: float = 0.0,
    tap: complex = 1.0,
    ):
        """
        Conecta dois barramentos na Ybus com:
        - admitância série y (complex)
        - susceptância de carregamento bc (total da linha, pu)
        - tap do lado "source" (pode ser real ou complexo: a*exp(j*phi))

        Modelo padrão MATPOWER:
        Yff += (y + j*bc/2)/|tap|^2
        Ytt += (y + j*bc/2)
        Yft += -y/conj(tap)
        Ytf += -y/tap
        """
         
        tap = complex(tap)
        if abs(tap) < 1e-12:
            tap = 1.0 + 0j

        tap_abs2 = tap * tap.conjugate()  # |tap|^2

        # Parte série
        self.y_matrix[source][source] += y / tap_abs2
        self.y_matrix[target][target] += y
        self.y_matrix[source][target] += -y / tap.conjugate()
        self.y_matrix[target][source] += -y / tap

        # Line charging (shunt)
        self.y_matrix[source][source] += 1j * (bc / 2.0) / tap_abs2
        self.y_matrix[target][target] += 1j * (bc / 2.0)

        # Se você usa bc em algum getBc, mantenha a matriz/registro que você já tinha:
        # (ajuste o nome do atributo conforme o teu arquivo)
        self.__bc[self.__getIndex(source, target)] = bc


    def __str__(self) -> str:
        return f"{self.__m}"

    @property
    def y_matrix(self) -> list[list[complex | float]]:
        return self.__m.matrix

    @property
    def z_matrix(self) -> list[list[complex | float]]:
        return self.__m.inverse
