from __future__ import annotations
from dataclasses import dataclass
from models.network_element import NetworkElement


@dataclass
class GeneratorSC:
    # Reatâncias em pu (subtransitória / sequências)
    x1_pu: float = 0.25   # X1 ~ Xd''
    x2_pu: float = 0.25   # X2
    x0_pu: float = 0.10   # X0

    # Neutro
    grounded: bool = True
    xn_pu: float = 0.0    # Xn (pu). Se solidamente aterrado, 0


class Generator(NetworkElement):
    """
    Gerador como componente explícito ligado a uma barra.
    - No PF: alimenta os campos da barra (P, V, limites Q).
    - No curto: fornece X1/X2/X0 e aterramento para as redes de sequência.
    """

    def __init__(
        self,
        bus_id: str,
        name: str = "G",
        p_gen: float = 0.0,
        v_set: float = 1.0,
        q_min: float = -9999.0,
        q_max: float = 9999.0,
        sc: GeneratorSC | None = None,
        id: str | None = None,
    ):
        super().__init__(name=name, type="G", id=id)
        self.bus_id = bus_id
        self.name = name

        # PF (simplificado)
        self.p_gen = p_gen
        self.v_set = v_set
        self.q_min = q_min
        self.q_max = q_max

        # Curto
        self.sc = sc if sc is not None else GeneratorSC()

    @property
    def is_generator(self) -> bool:
        return True
