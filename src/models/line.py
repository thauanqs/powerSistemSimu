from models.bus import Bus
from models.network_element import NetworkElement


class Line(NetworkElement):
    @staticmethod
    def from_z(
        tap_bus_id: str | Bus,
        z_bus_id: str | Bus,
        z: complex,
        bc: float = 0.0,
        tap: float = 1.0,
        phase: float = 0.0,
        name: str | None = None,
        id: str | None = None,
    ) -> "Line":
        y = 1 / complex(z.real, z.imag)
        return Line(
            tap_bus_id=tap_bus_id,
            z_bus_id=z_bus_id,
            g=y.real,
            b=y.imag,
            bc=bc,
            tap=tap,
            phase=phase,
            name=name,
            id=id,
            z1=z,
            z2=None,
            z0=None,
        )

    def __init__(
        self,
        tap_bus_id: str | Bus,
        z_bus_id: str | Bus,
        b: float = 0.0,
        g: float = 0.0,
        bc: float = 0.0,
        tap: float = 1.0,
        phase: float = 0.0,
        name: str | None = None,
        id: str | None = None,

        z1: complex | None = None,
        z2: complex | None = None,
        z0: complex | None = None,
        bc1: float | None = None,
        bc0: float | None = None,
    ):
        self.tap_bus_id: str = Line.__unrwap_bus_id(tap_bus_id)
        self.z_bus_id: str = Line.__unrwap_bus_id(z_bus_id)
        self.b: float = b
        self.g: float = g
        self.bc = bc
        self.tap = tap
        self.phase = phase

        self.z1: complex | None = z1
        self.z2: complex | None = z2
        self.z0: complex | None = z0
        self.bc1: float | None = bc1
        self.bc0: float | None = bc0

        if name:
            self.name: str = name
        else:
            self.name: str = f"Line"

        super().__init__(name=self.name, id=id, type="C")

    @property
    def y(self) -> complex:
        return complex(self.g, self.b)
    
    @property
    def y1(self) -> complex:
        """
        Admitância de sequência positiva.
        Se z1 não for informado, usa a admitância 'y' padrão.
        """
        if self.z1 is not None:
            return 1 / self.z1 if self.z1 != 0 else 0 + 0j
        return self.y

    @property
    def y2(self) -> complex:
        """
        Admitância de sequência negativa.
        Se z2 não for informado, assume igual à positiva (aproximação comum).
        """
        if self.z2 is not None:
            return 1 / self.z2 if self.z2 != 0 else 0 + 0j
        return self.y1

    @property
    def y0(self) -> complex:
        """
        Admitância de sequência zero.
        Se z0 não for informado, por enquanto usamos a mesma da positiva.
        (mais pra frente dá pra ajustar com dados reais de z0).
        """
        if self.z0 is not None:
            return 1 / self.z0 if self.z0 != 0 else 0 + 0j
        return self.y1

    @property
    def b1(self) -> float:
        """
        Susceptância shunt de sequência positiva.
        Se não informada, usa bc padrão.
        """
        return self.bc1 if self.bc1 is not None else self.bc

    @property
    def b0(self) -> float:
        """
        Susceptância shunt de sequência zero.
        Se não informada, assume igual à positiva.
        """
        return self.bc0 if self.bc0 is not None else self.b1

    def __str__(self) -> str:
        return (
            f"{self.tap_bus_id:4} -> {self.z_bus_id:4}, "
            f"y={complex(self.g, self.b):.4f}, "
            f"bc = {self.bc:.4f} tap = {self.tap:.4f}"
        )

    @staticmethod
    def __unrwap_bus_id(bus_id: str | Bus) -> str:
        if isinstance(bus_id, Bus):
            return bus_id.id
        return bus_id

    def copyWith(
        self,
        b: float | None = None,
        g: float | None = None,
        bc: float | None = None,
        tap: float | None = None,
        phase: float | None = None,
        name: str | None = None,
        z1: complex | None = None,
        z2: complex | None = None,
        z0: complex | None = None,
        bc1: float | None = None,
        bc0: float | None = None,
    ) -> "Line":
        return Line(
            tap_bus_id=self.tap_bus_id,
            z_bus_id=self.z_bus_id,
            b=b if b is not None else self.b,
            g=g if g is not None else self.g,
            bc=bc if bc is not None else self.bc,
            tap=tap if tap is not None else self.tap,
            phase=phase if phase is not None else self.phase,
            name=name if name is not None else self.name,
            id=self.id,
            z1=z1 if z1 is not None else self.z1,
            z2=z2 if z2 is not None else self.z2,
            z0=z0 if z0 is not None else self.z0,
            bc1=bc1 if bc1 is not None else self.bc1,
            bc0=bc0 if bc0 is not None else self.bc0,
        )
