from typing import Callable
import os 

from maths.power_flow import PowerFlow
from models.bus import Bus
from models.line import Line
from models.network_element import ElementEvent, NetworkElement
from models.faults import FaultType, FaultStudyResult
from typing import cast

from view.voltage_profile_plot import (
    show_voltage_profile,
    save_voltage_profile_chunks
)

from view.report_generator import generate_pdf_report

from reports.pdf_report import generate_pdf




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
        from view.voltage_profile_plot import show_voltage_profile

        # =============================
        # GERAR DADOS DO RELATÓRIO
        # =============================

        buses = []
        voltages = []

        for bus in self.__buses.values():
            buses.append(bus.number)          # número da barra
            voltages.append(bus.v)      # magnitude da tensão (pu)

        # =============================
        # GERAR GRÁFICO
        # =============================
        image_path = os.path.abspath("perfil_tensao.png")
        show_voltage_profile(
            buses=buses,
            voltages=voltages,
            save_path=image_path
        )

        
    #    bus_data = self.get_bus_report_data()

    #    generate_pdf(
    #       filename="relatorio_fluxo_potencia.pdf",
    #       bus_data=bus_data,
    #       image_path="perfil_tensao.png",
    #       logo_path="reports/assets/logo.png"
    #   )

    

    def printNetwork(self):
        pf = PowerFlow()
        for bus in self.__buses.values():
            bus = bus.copy_with()
            pf.add_bus(bus)
        for line in self.__connections.values():
            line = line.copyWith()
            pf.add_connection(line)
        # Esta linha chama print_data() (que agora deve retornar uma string)
        # e retorna essa string para quem chamou (a MainWindow)
        return pf.print_data()


    def getElementNames(self, ids: list[str]) -> str:
        return " "  # TODO


    def export_pdf_report(self, pdf_path: str):
        if not self.__buses:
            return

        buses = []
        voltages = []

        for bus in self.__buses.values():
            buses.append(bus.number)
            voltages.append(bus.v)

        output_dir = os.path.abspath("temp_graficos")

        image_paths = save_voltage_profile_chunks(
            buses=buses,
            voltages=voltages,
            output_dir=output_dir,
            bars_per_image=20
        )

        # gera PDF
        bus_data = self.get_bus_report_data()
        generate_pdf(
            filename=pdf_path,
            bus_data=bus_data,
            image_paths=image_paths,
            logo_path="reports/assets/logo.png"
        )

        # gera PDF
        
#       generate_pdf_report(
#          filename=pdf_path,
#          buses=buses,
#          voltages=voltages,
#          image_path=image_path,
#      )


    def get_bus_report_data(self):
        data = []
        for bus in self.__buses.values():
            data.append({
                "id": bus.number,
                "type": bus.type,
                "v": bus.v,
                "angle": bus.o * 180 / 3.141592653589793,  # em graus
                "p": bus.p,
                "q": bus.q,
                "p_sch": bus.p_sch,
                "q_sch": bus.q_sch
            })
        return data

