import cmath
from enum import Enum

from models.network_element import NetworkElement


class BusType(Enum):
    SLACK = 3
    PV = 2
    PQ = 0


class Bus(NetworkElement):
    __number: int = 1

    def __init__(
        self,
        name: str | None = None,
        v: float = 1.0,
        o: float = 0.0,
        p_load: float = 0.0,  # real S_load
        q_load: float = 0.0,  # imaginary S_load
        p_gen: float = 0.0,  # real S_load
        q_gen: float = 0.0,  # imaginary S_load
        q_min: float = float("-inf"),
        q_max: float = float("inf"),
        type: BusType = BusType.PQ,
        v_rated: float = 1.0,
        index: int = -1,
        g_shunt: float = 0.0,  # real Y
        b_shunt: float = 0.0,  # imaginary Y
        number: int | None = None,
        id: str | None = None,
    ):

        self.v_sch: float = v
        self.o_sch: float = o
        self.p_sch: float = p_gen - p_load
        self.q_sch: float = q_gen - q_load

        if number is not None:
            self.number: int = number
        else:
            self.number: int = Bus.__number
            Bus.__number += 1

        if name:
            self.name: str = name
        else:
            self.name: str = f"Bus {self.number:03d}"

        self.v: float = v
        self.o: float = o
        self.p: float = self.p_sch
        self.q: float = self.q_sch
        self.p_load: float = p_load
        self.q_load: float = q_load
        self.p_gen: float = p_gen
        self.q_gen: float = q_gen
        self.q_min: float = q_min
        self.q_max: float = q_max
        self.index: int = index
        self.type: BusType = type
        self.v_rated: float = v_rated
        self.g_shunt: float = g_shunt
        self.b_shunt: float = b_shunt
        super().__init__(name=self.name, id=id, type="B")

    def copy_with(
        self,
        name: str | None = None,
        number: int | None = None,
        v: float | None = None,
        o: float | None = None,
        p_load: float | None = None,
        q_load: float | None = None,
        p_gen: float | None = None,
        q_gen: float | None = None,
        q_min: float | None = None,
        q_max: float | None = None,
        type: BusType | None = None,
        v_rated: float | None = None,
        index: int | None = None,
        b_shunt: float | None = None,
        g_shunt: float | None = None,
        id: str | None = None,  
    ) -> "Bus":
        return Bus(
            name=name if name is not None else self.name,
            number=number if number is not None else self.number,
            v=v if v is not None else self.v,
            o=o if o is not None else self.o,
            q_min=q_min if q_min is not None else self.q_min,
            q_max=q_max if q_max is not None else self.q_max,
            type=type if type is not None else self.type,
            v_rated=v_rated if v_rated is not None else self.v_rated,
            index=index if index is not None else self.index,
            b_shunt=b_shunt if b_shunt is not None else self.b_shunt,
            g_shunt=g_shunt if g_shunt is not None else self.g_shunt,
            p_load=p_load if p_load is not None else self.p_load,
            q_load=q_load if q_load is not None else self.q_load,
            p_gen=p_gen if p_gen is not None else self.p_gen,
            q_gen=q_gen if q_gen is not None else self.q_gen,
            id=id if id is not None else self.id,
        )

    def __str__(self) -> str:
        # q_min: str = "        "
        # if self.q_min:
        #     q_min = f"{self.q_min:+8.2f}"
        # q_max: str = "        "
        # if self.q_max:
        #     q_max = f"{self.q_max:+8.2f}"
        return (
            f"{int(self.id):04d} {self.type.name:^7s}, v = {self.v:+4.3f} ∠ {(self.o*180/cmath.pi):+8.3f}° |"
            + f", p = {self.p:+8.2f}, q = {self.q:+8.2f}"
            + f", p_sch: {self.p_sch:+8.2f}, q_sch: {self.q_sch:+8.2f} |"
            # + f" Q_min: {q_min} | Q_max: {q_max} | shunt: {self.g_shunt:+4.2f}  {self.b_shunt:+4.2f}j |"
        
        # A sintaxe geral de formatação em Python é :[[preenchimento]alinhamento][sinal][largura][.precisão][tipo].
        )
