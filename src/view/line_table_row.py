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
        bc = self.bc.getValue()
        tap = self.tap.getValue()

        # Vamos calcular SEMPRE y (g+jb) e z (r+jx) e manter coerentes
        if self.choiceField.currentIndex() == 0:  # Z
            r = self.r.getValue()
            x = self.x.getValue()
            if r is None or x is None:
                SimulatorController.instance().updateElement(self.line.copyWith())
                return

            z = complex(r, x)
            y = 0j if abs(z) < 1e-12 else (1 / z)

            g = y.real
            b = y.imag

        else:  # Y
            g = self.g.getValue()
            b = self.b.getValue()
            if g is None or b is None:
                SimulatorController.instance().updateElement(self.line.copyWith())
                return

            y = complex(g, b)
            z = 0j if abs(y) < 1e-12 else (1 / y)

        # Atualiza z1 SEMPRE (porque é isso que o solver usa em y1)
        new_z1 = z

        # Se z2/z0 não foram definidos (None), mantém iguais ao positivo (didático)
        new_z2 = self.line.z2 if self.line.z2 is not None else z
        new_z0 = self.line.z0 if self.line.z0 is not None else (3 * z)  # <-- AQUI

        SimulatorController.instance().updateElement(
            self.line.copyWith(
                g=g, b=b,
                bc=bc, tap=tap,
                z1=new_z1, z2=new_z2, z0=new_z0
            )
        )

    def update_values(self) -> None:
        tap_bus: Bus = SimulatorController.instance().get_bus_by_id(self.line.tap_bus_id)
        z_bus: Bus = SimulatorController.instance().get_bus_by_id(self.line.z_bus_id)
        # Mostra o que o cálculo realmente usa:
        z = self.line.z1 if self.line.z1 is not None else (0j if abs(self.line.y) < 1e-12 else 1 / self.line.y)
        y = self.line.y1  # adm. usada na sequência positiva
        self.tapBus.setValue(tap_bus.name)
        self.zBus.setValue(z_bus.name)
        self.r.setValue(z.real)
        self.x.setValue(z.imag)
        self.g.setValue(y.real)
        self.b.setValue(y.imag)
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
