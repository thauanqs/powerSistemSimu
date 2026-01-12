# src/models/bus_square_matrix.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, List, Optional, TypeVar

T = TypeVar("T")


@dataclass
class BusIndex:
    bus_id: str
    index: int


class BusSquareMatrix(Generic[T]):
    def __init__(self, m: Optional[List[List[T]]] = None) -> None:
        # EVITA default mutável compartilhado entre instâncias
        self.__m: List[List[T]] = m if m is not None else []
        self.__indexes: List[BusIndex] = []

    @property
    def matrix(self):
        return self.__m  # ou o nome real da tua matriz interna

    @property
    def size(self) -> int:
        # mais robusto do que manter "size" separado
        return len(self.__m)
    
    @property
    def inverse(self):
        import numpy as np
        return np.linalg.inv(np.array(self.matrix, dtype=complex)).tolist()


    def add_bus(self, bus_id: str, initial_value: T) -> None:
        bus_index = BusIndex(bus_id, self.size)
        self.__indexes.append(bus_index)

        # adiciona coluna nas linhas existentes
        for row in self.__m:
            row.append(initial_value)

        # adiciona nova linha
        self.__m.append([initial_value] * (self.size + 1))

    def remove_bus(self, bus_id: str) -> None:
        idx = self.get_bus_index(bus_id)

        self.__m.pop(idx)
        for row in self.__m:
            row.pop(idx)

        self.__indexes = [b for b in self.__indexes if b.bus_id != bus_id]
        for b in self.__indexes:
            if b.index > idx:
                b.index -= 1

    def set_value(self, i: int, j: int, value: T) -> None:
        self.__m[i][j] = value

    def get_value(self, i: int, j: int) -> T:
        return self.__m[i][j]

    def get_bus_index(self, bus_id: str) -> int:
        for b in self.__indexes:
            if b.bus_id == bus_id:
                return b.index
        raise ValueError(f"Bus id not found: {bus_id}")

    def get_bus_id(self, index: int) -> str:
        for b in self.__indexes:
            if b.index == index:
                return b.bus_id
        raise ValueError(f"Bus index not found: {index}")

    def as_list(self) -> List[List[T]]:
        return self.__m

    def clear(self) -> None:
        self.__m = []
        self.__indexes = []
