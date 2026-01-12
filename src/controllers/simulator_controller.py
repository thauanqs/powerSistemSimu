from typing import Callable
import os 

from maths.power_flow import PowerFlow
from models.bus import Bus, BusType
from models.line import Line
from models.network_element import ElementEvent, NetworkElement
from models.faults import FaultType, FaultStudyResult
from models.generator import Generator

from typing import cast
from PySide6.QtWidgets import QMessageBox, QInputDialog
from maths.short_circuit import (run_three_phase_fault_from_powerflow, run_slg_fault_from_powerflow, run_ll_fault_from_powerflow, run_dlg_fault_from_powerflow)
from view.fault_result_dialog import FaultResultDialog
import numpy as np
import re


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
        self.__generators.clear()

    @property
    def buses(self) -> list[Bus]:
        return list(self.__buses.values())

    @property
    def connections(self) -> list[Line]:
        return list(self.__connections.values())
    
    @property
    def generators(self) -> list[Generator]:
        return list(self.__generators.values())


    def __init__(self):
        self.__buses = dict[str, Bus]()
        self.__connections = dict[str, Line]()
        self.__generators = dict[str, Generator]()  # id -> Generator
        self.__listeners: list[Callable[[NetworkElement, ElementEvent], None]] = []
        self.power_base_mva: float = 100.0
        self.__power_flow: PowerFlow | None = None
        self.__next_bus_num = 1
        self.__free_bus_nums: set[int] = set()
        self.__next_bus_number: int = 1
        self.__free_bus_numbers: set[int] = set()


    def listen(self, callback: Callable[[NetworkElement, ElementEvent], None]) -> None:
        self.__listeners.append(callback)

    @staticmethod
    def _extract_int(s: str) -> int | None:
        m = re.search(r"(\d+)$", s.strip())
        return int(m.group(1)) if m else None


    def addBus(self, bus: Bus | None = None) -> Bus:
        # se o botão Add Bus chama sem argumentos
        if bus is None:
            bus = Bus(id="", name="", type=BusType.PQ)

        # -----------------------------
        # CASO 1: barra nova (id vazio) -> gerar B_n
        # -----------------------------
        if (not bus.id) or (bus.id in self.__buses):
            n = self.__alloc_bus_number()
            new_id = f"B_{n}"

            new_name = bus.name.strip() if bus.name else ""
            if new_name == "" or new_name.startswith("Bus"):
                new_name = f"Bus {n:03d}"

            bus = bus.copy_with(id=new_id, number=n, name=new_name)

        # -----------------------------
        # CASO 2: barra importada (id já veio do arquivo) -> NÃO ALTERA id
        # -----------------------------
        else:
            # garante number coerente (pra teu pool de números)
            n = getattr(bus, "number", 0) or 0
            if n <= 0:
                parsed = SimulatorController._extract_int(bus.id)
                if parsed is not None:
                    n = parsed
                else:
                    n = self.__alloc_bus_number()

            # só atualiza number/nome se estiverem vazios
            new_name = bus.name.strip() if bus.name else ""
            if new_name == "" or new_name.startswith("Bus"):
                new_name = f"Bus {n:03d}"

            bus = bus.copy_with(number=n, name=new_name)  # id fica igual

            # marca número como “usado” (não pode reaproveitar)
            self.__free_bus_numbers.discard(n)
            if n >= self.__next_bus_number:
                self.__next_bus_number = n + 1

        self.__power_flow = None

        # guarda e emite evento
        self.__buses[bus.id] = bus
        for cb in self.__listeners:
            cb(bus, ElementEvent.CREATED)
        return bus



    def addConnection(self, line: Line) -> Line:
        return cast(Line, self.__add_element(line))

    def __add_element(self, element: NetworkElement) -> NetworkElement:
        if isinstance(element, Bus):
            self.__buses[element.id] = element
        elif isinstance(element, Line):
            self.__connections[element.id] = element

        self.__power_flow = None

        for callback in self.__listeners:
            callback(element, ElementEvent.CREATED)

        return element
    
    def addGenerator(self, gen: Generator) -> Generator:
        self.__generators[gen.id] = gen
        for cb in self.__listeners:
            cb(gen, ElementEvent.CREATED)
        return gen

    def updateElement(self, element: NetworkElement) -> None:
        if element.id in self.__buses and isinstance(element, Bus):
            self.__buses[element.id] = element
        elif element.id in self.__connections and isinstance(element, Line):
            self.__connections[element.id] = element
        elif element.id in self.__generators and isinstance(element, Generator):
            self.__generators[element.id] = element
        else:
            return

        self.__power_flow = None 

        for callback in self.__listeners:
            callback(element, ElementEvent.UPDATED)
            
    def getGeneratorByBusId(self, bus_id: str) -> Generator | None:
        for g in self.__generators.values():
            if g.bus_id == bus_id:
                return g
        return None

    def upsertGenerator(self, gen: Generator) -> Generator:
        """Cria ou atualiza um gerador ligado a uma barra (1 por barra)."""
        existing = self.getGeneratorByBusId(gen.bus_id)
        if existing is None:
            return self.addGenerator(gen)

        # mantém o mesmo id (NetworkElement não permite mudar id depois)
        if gen.id != existing.id:
            gen = Generator(
                bus_id=gen.bus_id,
                name=gen.name,
                p_gen=gen.p_gen,
                v_set=gen.v_set,
                q_min=gen.q_min,
                q_max=gen.q_max,
                sc=gen.sc,
                id=existing.id,
            )

        self.__generators[gen.id] = gen
        for cb in self.__listeners:
            cb(gen, ElementEvent.UPDATED)
        return gen

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

            # aplica dados de gerador nas barras (modelo didático: 1 gerador por barra, ou soma se tiver mais)
        for gen in self.__generators.values():
            if gen.bus_id not in self.__buses:
                continue
            b = self.__buses[gen.bus_id]

            # Se quiser: se a barra for slack/pv, manter; senão torna PV por padrão
            if b.type not in (BusType.SLACK, BusType.PV):
                b.type = BusType.PV

            b.p_gen = gen.p_gen
            b.v = gen.v_set
            b.q_min = gen.q_min
            b.q_max = gen.q_max

        # aplica dados de gerador nas barras (modelo didático)
        for gen in self.__generators.values():
            if gen.bus_id not in self.__buses:
                continue
            b = self.__buses[gen.bus_id]

            if b.type not in (BusType.SLACK, BusType.PV):
                b.type = BusType.PV

            b.p_gen = gen.p_gen
            b.v = gen.v_set
            b.q_min = gen.q_min
            b.q_max = gen.q_max

        power_flow.solve(decoupled=True, max_iterations=50, tol=1e-5)
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
    
    def _show_fault_result_dialog(self, result: FaultStudyResult, window_title: str) -> None:
        dlg = FaultResultDialog(result, buses=self.__buses, s_base_mva=self.power_base_mva)
        dlg.setWindowTitle(window_title)
        dlg.exec()
    
    def _resolve_bus_id(self, bus_ref: str) -> str:
        """
        Aceita:
          - id real da barra (ex.: 'B_4' ou uuid)
          - número da barra como string (ex.: '4')
          - nome (ex.: 'Bus 4')
        E devolve o id real existente em self.__buses.
        """
        if bus_ref in self.__buses:
            return bus_ref

        # tenta como número
        try:
            n = int(bus_ref)
            for b in self.__buses.values():
                if getattr(b, "number", None) == n:
                    return b.id
        except Exception:
            pass

        # tenta como nome
        for b in self.__buses.values():
            if getattr(b, "name", None) == bus_ref:
                return b.id

        raise ValueError(f"Barra '{bus_ref}' não encontrada (nem por id, nem por number, nem por name).")


    def chooseAndRunFaultOnBus(self, bus_id: str) -> None:
        """
        Abre um diálogo para o usuário escolher o tipo de falta
        e executa o estudo na barra indicada.
        """
        if self.__power_flow is None:
            QMessageBox.warning(
                None,
                "Curto-circuito",
                "Execute o fluxo de potência antes de calcular a falta.",
            )
            return
        
        bus_id = self._resolve_bus_id(bus_id)


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

        if item.startswith("Falta trifásica"):
            self._run_three_phase_fault_on_bus(bus_id)
            return

        if item.startswith("Falta monofásica"):
            phase, ok = QInputDialog.getItem(
                None,
                "Fase da falta",
                "Selecione a fase (SLG):",
                ["A", "B", "C"],
                0,
                False,
            )
            if not ok:
                return
            self._run_slg_fault_on_bus(bus_id, phase)
            return

        if item.startswith("Falta fase-fase"):
            phase, ok = QInputDialog.getItem(
                None,
                "Fases da falta",
                "Selecione o par de fases (LL):",
                ["AB", "BC", "CA"],
                0,
                False,
            )
            if not ok:
                return
            self._run_ll_fault_on_bus(bus_id, phase)
            return

        if item.startswith("Falta dupla"):
            phase, ok = QInputDialog.getItem(
                None,
                "Fases da falta",
                "Selecione o par de fases (DLG):",
                ["ABG", "BCG", "CAG"],
                0,
                False,
            )
            if not ok:
                return
            self._run_dlg_fault_on_bus(bus_id, phase)
            return

    def _ask_thevenin_source_data(self) -> tuple[str | None, complex | None, complex | None, complex | None]:
        """
        Pergunta se o usuário quer adicionar uma fonte Thevenin na SLACK e coleta X1, X2, X0 (pu).
        Retorna: (source_bus_id, Z1, Z2, Z0) em pu (complex).
        """
        if any(getattr(g, "enabled", True) for g in self.__generators.values()):
            return None, None, None, None

        if self.__power_flow is None:
            return None, None, None, None

        # achar slack
        slack_id = None
        for bus_id, bus in self.__power_flow.buses.items():
            if getattr(bus, "type", None) == BusType.SLACK:
                slack_id = bus_id
                break
        if slack_id is None:
            # Se já existem geradores explícitos, não incomoda com popup de Thevenin
            if len(self.__generators) > 0:
                return None, None, None, None

            return None, None, None, None

        reply = QMessageBox.question(
            None,
            "Fonte equivalente",
            "Deseja modelar uma fonte equivalente (Thevenin) na barra SLACK para o curto-circuito?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return None, None, None, None

        x1, ok = QInputDialog.getDouble(None, "X1 (pu)", "Informe X1 (subtransitória, pu):", 0.25, 0.0, 10.0, 4)
        if not ok: return None, None, None, None
        x2, ok = QInputDialog.getDouble(None, "X2 (pu)", "Informe X2 (sequência negativa, pu):", x1, 0.0, 10.0, 4)
        if not ok: return None, None, None, None
        x0, ok = QInputDialog.getDouble(None, "X0 (pu)", "Informe X0 (sequência zero, pu):", 0.10, 0.0, 10.0, 4)
        if not ok: return None, None, None, None

        # neutro (opcional)
        xn, ok = QInputDialog.getDouble(None, "Xn (pu)", "Informe Xn do neutro (pu). Se solidamente aterrado, use 0:", 0.0, 0.0, 10.0, 4)
        if not ok: return None, None, None, None

        Z1 = 1j * x1
        Z2 = 1j * x2
        Z0 = 1j * (x0 + 3.0 * xn)  # sequência zero vê 3*Zn

        return slack_id, Z1, Z2, Z0

    def _run_three_phase_fault_on_bus(self, bus_id: str) -> None:
        try:
            source_bus_id, Z1s, Z2s, Z0s = self._ask_thevenin_source_data()

            result = run_three_phase_fault_from_powerflow(
                self.__power_flow,
                bus_id,
                source_bus_id=source_bus_id,
                z1_source_pu=Z1s,
                z2_source_pu=Z2s,
                z0_source_pu=Z0s,
                generators=self.generators,
            )
            self._show_fault_result_dialog(result, f"Falta 3φ na barra {bus_id}")
        except Exception as e:
            QMessageBox.critical(None, "Erro no curto-circuito", str(e))


    def _run_slg_fault_on_bus(self, bus_id: str, phase: str) -> None:
        try:
            source_bus_id = None
            Z1s = Z2s = Z0s = None

            # Só pergunta Thevenin se NÃO existir gerador explícito
            if len(self.generators) == 0:
                source_bus_id, Z1s, Z2s, Z0s = self._ask_thevenin_source_data()

            result = run_slg_fault_from_powerflow(
                self.__power_flow,
                bus_id,
                phase=phase,
                source_bus_id=source_bus_id,
                z1_source_pu=Z1s,
                z2_source_pu=Z2s,
                z0_source_pu=Z0s,
                generators=self.generators,
            )
            self._show_fault_result_dialog(result, f"Falta SLG ({phase}) na barra {bus_id}")
        except Exception as e:
            QMessageBox.critical(None, "Erro no curto-circuito", str(e))


    def _run_ll_fault_on_bus(self, bus_id: str, phase: str) -> None:
        try:
            source_bus_id = None
            Z1s = Z2s = Z0s = None

            # Só pergunta Thevenin se NÃO existir gerador explícito
            if len(self.generators) == 0:
                source_bus_id, Z1s, Z2s, Z0s = self._ask_thevenin_source_data()


            result = run_ll_fault_from_powerflow(
                self.__power_flow,
                bus_id,
                phase=phase,
                source_bus_id=source_bus_id,
                z1_source_pu=Z1s,
                z2_source_pu=Z2s,
                z0_source_pu=Z0s,
                generators=self.generators,
            )
            self._show_fault_result_dialog(result, f"Falta LL ({phase}) na barra {bus_id}")
        except Exception as e:
            QMessageBox.critical(None, "Erro no curto-circuito", str(e))


    def _run_dlg_fault_on_bus(self, bus_id: str, phase: str) -> None:
        try:
            source_bus_id = None
            Z1s = Z2s = Z0s = None

            # Só pergunta Thevenin se NÃO existir gerador explícito
            if len(self.generators) == 0:
                source_bus_id, Z1s, Z2s, Z0s = self._ask_thevenin_source_data()

            result = run_dlg_fault_from_powerflow(
                self.__power_flow,
                bus_id,
                phase=phase,
                source_bus_id=source_bus_id,
                z1_source_pu=Z1s,
                z2_source_pu=Z2s,
                z0_source_pu=Z0s,
                generators=self.generators,
            )
            self._show_fault_result_dialog(result, f"Falta DLG ({phase}) na barra {bus_id}")
        except Exception as e:
            QMessageBox.critical(None, "Erro no curto-circuito", str(e))

    def deleteConnection(self, line_id: str) -> None:
        line = self.__connections.pop(line_id, None)

        self.__power_flow = None

        if line is None:
            return
        for cb in self.__listeners:
            cb(line, ElementEvent.DELETED)

    def deleteGenerator(self, gen_id: str) -> None:
        gen = self.__generators.pop(gen_id, None)
        if gen is None:
            return
        for cb in self.__listeners:
            cb(gen, ElementEvent.DELETED)

    def deleteBus(self, bus_id: str) -> None:
        bus = self.__buses.pop(bus_id, None)
        if bus is None:
            return
        
        self.__power_flow = None

        # libera o número pra ser reutilizado
        self.__free_bus_numbers.add(bus.number)

        for cb in self.__listeners:
            cb(bus, ElementEvent.DELETED)


        # apaga linhas conectadas
        lines_to_delete = [
            l.id for l in self.__connections.values()
            if l.tap_bus_id == bus_id or l.z_bus_id == bus_id
        ]
        for lid in lines_to_delete:
            self.deleteConnection(lid)

        # apaga geradores ligados na barra
        gens_to_delete = [
            g.id for g in self.__generators.values()
            if getattr(g, "bus_id", None) == bus_id
        ]
        for gid in gens_to_delete:
            self.deleteGenerator(gid)

        # por fim, apaga a barra
        bus = self.__buses.pop(bus_id, None)
        if bus is None:
            return
        for cb in self.__listeners:
            cb(bus, ElementEvent.DELETED)

    def __extract_bus_num(self, bus_id: str) -> int | None:
        # tenta pegar o final numérico: "B_3" -> 3, "3" -> 3
        m = re.search(r"(\d+)$", bus_id.strip())
        return int(m.group(1)) if m else None

    def __new_bus_id(self) -> str:
        if self.__free_bus_nums:
            n = min(self.__free_bus_nums)
            self.__free_bus_nums.remove(n)
            return f"B_{n}"
        n = self.__next_bus_num
        self.__next_bus_num += 1
        return f"B_{n}"

    def __alloc_bus_number(self) -> int:
        if self.__free_bus_numbers:
            n = min(self.__free_bus_numbers)
            self.__free_bus_numbers.remove(n)
            return n
        n = self.__next_bus_number
        self.__next_bus_number += 1
        return n

    def sync_bus_number_pool(self) -> None:
        used = {b.number for b in self.__buses.values() if hasattr(b, "number")}
        if not used:
            self.__next_bus_number = 1
            self.__free_bus_numbers.clear()
            return
        self.__next_bus_number = max(used) + 1
        self.__free_bus_numbers = set(range(1, self.__next_bus_number)) - used

