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
    ):
        self.tap_bus_id: str = Line.__unrwap_bus_id(tap_bus_id)
        self.z_bus_id: str = Line.__unrwap_bus_id(z_bus_id)
        self.b: float = b
        self.g: float = g
        self.bc = bc
        self.tap = tap
        self.phase = phase

        if name:
            self.name: str = name
        else:
            self.name: str = f"Line"

        super().__init__(name=self.name, id=id, type="C")

    @property
    def y(self) -> complex:
        return complex(self.g, self.b)

    def __str__(self) -> str:
        return f"{int(self.tap_bus_id):04d} -> {int(self.z_bus_id):04d}, y = {complex(self.g,self.b):.4f}, bc = {self.bc:.4f} tap = {self.tap:.4f}"

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
        )
