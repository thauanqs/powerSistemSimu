from PySide6.QtWidgets import QWidget, QComboBox

from controllers.simulator_controller import ElementEvent, SimulatorController
from models.bus import Bus
from models.line import Line
from models.network_element import NetworkElement
from view.text_field import TextField


class LineTableRow:

    def __init__(self, line: Line):
        SimulatorController.instance().listen(self.circuitListener)
        self.line = line

        # Field 1: "tap bus" (str)
        self.tapBus = TextField[str](type=str, enabled=False)

        # Field 2: "z bus" (str)
        self.zBus = TextField[str](type=str, enabled=False)

        # Field 3: unnamed dropdown (allow user to pick Z or Y)
        self.choiceField = QComboBox()
        self.choiceField.addItems(["Z", "Y"])  # type: ignore
        self.choiceField.currentIndexChanged.connect(self.on_choice_field_updated)

        # Field 4: "r" (float) – using (1/element.y).real if available
        self.r = TextField[float](type=float, on_focus_out=self.save)

        # Field 5: "x" (float) – using (1/element.y).imag if available
        self.x = TextField[float](type=float, on_focus_out=self.save)

        # Field 6: "g" (float)
        self.g = TextField[float](type=float, enabled=False, on_focus_out=self.save)

        # Field 7: "b" (float)
        self.b = TextField[float](type=float, enabled=False, on_focus_out=self.save)

        # Field 8: "bc" (float)
        self.bc = TextField[float](type=float, on_focus_out=self.save)

        # Field 9: "tap" (float)
        self.tap = TextField[float](type=float, on_focus_out=self.save)

        self.update_values()

    def get_widgets(self) -> list[QWidget]:
        return [
            self.tapBus,
            self.zBus,
            self.choiceField,
            self.r,
            self.x,
            self.g,
            self.b,
            self.bc,
            self.tap,
        ]

    def on_choice_field_updated(self, option: int):
        if option == 0:  # Z
            self.r.setEnabled(True)
            self.x.setEnabled(True)
            self.g.setEnabled(False)
            self.b.setEnabled(False)
        elif option == 1:  # Y
            self.r.setEnabled(False)
            self.x.setEnabled(False)
            self.g.setEnabled(True)
            self.b.setEnabled(True)
        pass

    def save(self) -> None:
        b: float | None = None
        g: float | None = None
        if self.choiceField.currentIndex() == 0:
            r = self.r.getValue()
            x = self.x.getValue()
            if r is None or x is None:
                SimulatorController.instance().updateElement(self.line.copyWith())
                return
            y = 1 / complex(r, x)
            g = y.real
            b = y.imag
        else:
            g = self.g.getValue()
            b = self.b.getValue()

        bc = self.bc.getValue()
        tap = self.tap.getValue()

        SimulatorController.instance().updateElement(self.line.copyWith(b=b, g=g, bc=bc, tap=tap))

    def update_values(self) -> None:
        tap_bus: Bus = SimulatorController.instance().get_bus_by_id(self.line.tap_bus_id)
        z_bus: Bus = SimulatorController.instance().get_bus_by_id(self.line.z_bus_id)
        z: complex = 1 / self.line.y
        self.tapBus.setValue(tap_bus.name)
        self.zBus.setValue(z_bus.name)
        self.r.setValue(z.real)
        self.x.setValue(z.imag)
        self.g.setValue(self.line.g)
        self.b.setValue(self.line.b)
        if self.line.bc != 0.0:
            self.bc.setValue(self.line.bc)
        else:
            self.bc.clearValue()
        if self.line.tap != 1.0:
            self.tap.setValue(self.line.tap)
        else:
            self.tap.clearValue()

    def circuitListener(self, element: NetworkElement, event: ElementEvent):
        if (
            event is ElementEvent.UPDATED
            and isinstance(element, Line)
            and element.id == self.line.id
        ):
            self.line = element
            self.update_values()
            return

        if (
            event is ElementEvent.UPDATED
            and isinstance(element, Bus)
            and element.id in (self.line.tap_bus_id, self.line.z_bus_id)
        ):
            self.update_values()
            return
