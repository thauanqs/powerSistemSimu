from typing import Callable

from maths.power_flow import PowerFlow
from models.bus import Bus
from models.line import Line
from models.network_element import ElementEvent, NetworkElement
from typing import cast
from PySide6.QtWidgets import QMessageBox
from maths.short_circuit import run_three_phase_fault_from_powerflow
import numpy as np


class SimulatorController:
    __instance = None

    @staticmethod
    def instance():
        if SimulatorController.__instance is None:
            SimulatorController.__instance = SimulatorController()
        return SimulatorController.__instance

    def clear_state(self):
        for bus in self.__buses.values():
            for listener in self.__listeners:
                listener(bus, ElementEvent.DELETED)
        for connection in self.__connections.values():
            for listener in self.__listeners:
                listener(connection, ElementEvent.DELETED)
        self.__buses.clear()
        self.__connections.clear()

    @property
    def buses(self) -> list[Bus]:
        return list(self.__buses.values())

    @property
    def connections(self) -> list[Line]:
        return list(self.__connections.values())

    def __init__(self):
        self.__buses = dict[str, Bus]()
        self.__connections = dict[str, Line]()
        self.__listeners: list[Callable[[NetworkElement, ElementEvent], None]] = []
        self.power_base_mva: float = 100.0
        self.__power_flow: PowerFlow | None = None

    def listen(self, callback: Callable[[NetworkElement, ElementEvent], None]) -> None:
        self.__listeners.append(callback)

    def addBus(self, bus: Bus | None = None) -> Bus:
        return cast(Bus, self.__add_element(bus if bus else Bus()))

    def addConnection(self, line: Line) -> Line:
        return cast(Line, self.__add_element(line))

    def __add_element(self, element: NetworkElement) -> NetworkElement:
        if isinstance(element, Bus):
            self.__buses[element.id] = element
        elif isinstance(element, Line):
            self.__connections[element.id] = element

        for callback in self.__listeners:
            callback(element, ElementEvent.CREATED)

        return element

    def updateElement(self, element: NetworkElement) -> None:
        if element.id in self.__buses and isinstance(element, Bus):
            self.__buses[element.id] = element
        elif element.id in self.__connections and isinstance(element, Line):
            self.__connections[element.id] = element
        else:
            return

        for callback in self.__listeners:
            callback(element, ElementEvent.UPDATED)

    def get_bus_by_id(self, id: str) -> Bus:
        if id in self.__buses:
            return self.__buses[id]
        raise ValueError(f"Bus with id {id} not found")

    def get_connection_by_id(self, id: str) -> Line:
        if id in self.__connections:
            return self.__connections[id]
        raise ValueError(f"Connection with id {id} not found")

    def runPowerFlow(self):
        power_flow = PowerFlow(base=self.power_base_mva)
        for bus in self.__buses.values():
            power_flow.add_bus(bus)
        for connection in self.__connections.values():
            power_flow.add_connection(connection)

        power_flow.solve()
        self.__power_flow = power_flow

        for bus in self.__buses.values():
            for callback in self.__listeners:
                callback(bus, ElementEvent.UPDATED)

    def printNetwork(self):
        pf = PowerFlow()
        for bus in self.__buses.values():
            bus = bus.copy_with()
            pf.add_bus(bus)
        for line in self.__connections.values():
            line = line.copyWith()
            pf.add_connection(line)
        pf.print_data()

    def getElementNames(self, ids: list[str]) -> str:
        return " "  # TODO
    
    def runThreePhaseFaultOnBus(self, bus_id: str) -> None:
        """
        Executa falta trifásica na barra indicada e mostra a corrente de falta.

        Para funcionar, é preciso ter rodado runPowerFlow() antes
        (para preencher self.__power_flow).
        """
        if self.__power_flow is None:
            QMessageBox.warning(
                None,  # ideal: janela principal como parent
                "Curto-circuito",
                "Execute o fluxo de potência antes de calcular a falta."
            )
            return

        try:
            result = run_three_phase_fault_from_powerflow(self.__power_flow, bus_id)
        except Exception as e:
            QMessageBox.critical(
                None,
                "Curto-circuito",
                f"Erro ao calcular falta 3φ na barra {bus_id}:\n{e}"
            )
            return

        If = result.fault_current_pu
        If_mag = np.abs(If)
        If_ang = np.rad2deg(np.angle(If))

        msg = (
            f"Falta 3φ na barra {bus_id}\n\n"
            f"|If| = {If_mag:.4f} pu\n"
            f"∠If = {If_ang:.2f}°"
        )

        QMessageBox.information(
            None,  # ideal: janela principal como parent
            "Resultado de falta trifásica",
            msg,
        )

