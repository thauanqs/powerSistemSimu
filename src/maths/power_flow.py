import cmath
from math import sqrt
from typing import Any, Callable
import numpy
import numpy as np 

from maths.power_calculator import calcP, calcQ, dPdO, dPdV, dQdO, dQdV
from models.line import Line
from models.bus import Bus, BusType
from models.y_bus_square_matrix import YBusSquareMatrix
from models.transformer import Transformer


class VariableIndex:
    def __init__(self, variable: str, power: str, busIndex: int, busId: str):
        self.variable = variable
        self.power = power
        self.index = busIndex
        self.busId = busId

    def __str__(self) -> str:
        return f"{self.variable}[{self.index + 1}]"


class PowerFlow:
    def __init__(self, base: float = 1):
        self.buses = dict[str, Bus]()
        self.connections = dict[str, Line]()
        self.__yMatrix: YBusSquareMatrix = YBusSquareMatrix()
        self.indexes = list[VariableIndex]()
        self.base = base

    def add_bus(self, bus: Bus) -> Bus:
        self.buses[bus.id] = bus
        bus.index = len(self.buses) - 1
        return bus

    def add_connection(self, connection: Line) -> None:
        self.connections[connection.id] = connection

    def build_bus_matrix(self, sequence: str = "positive") -> YBusSquareMatrix:
        def c0(x):
            return 0+0j if x is None else complex(x)

        def f0(x):
            return 0.0 if x is None else float(x)

        
        """
        Monta a Ybus para a sequência indicada:

        - "positive"  -> usa y1, b1
        - "negative"  -> usa y2, b1
        - "zero"      -> usa y0, b0

        Regra didática extra:
        - Se o ramo for Transformer e sequence=="zero",
        usa ligação (D/Y/Yg) e aterramento para decidir passagem de seq. zero.
        """
        from models.transformer import Transformer  # import local evita ciclo

        bus_matrix: YBusSquareMatrix = YBusSquareMatrix()

        # barras (shunt da barra)
        for index, bus in enumerate(self.buses.values()):
            bus_matrix.add_bus(bus.id)  # id correto
            bus.index = index
            # shunt da barra entra na diagonal
            bus_matrix.y_matrix[index][index] += complex(bus.g_shunt, bus.b_shunt)


        # conexões entre barras
        for connection in self.connections.values():

            # ---------------------------------------------------------
            # Transformador na sequência zero
            # ---------------------------------------------------------

            if sequence == "zero" and isinstance(connection, Transformer):
                hv_idx = self.buses[connection.tap_bus_id].index
                lv_idx = self.buses[connection.z_bus_id].index

                def norm_conn(s: str) -> str:
                    return s.upper().strip()

                hv_c = norm_conn(connection.meta.conn_hv)
                lv_c = norm_conn(connection.meta.conn_lv)

                hv_delta = hv_c == "D"
                lv_delta = lv_c == "D"

                hv_star = hv_c in ("Y", "YG")
                lv_star = lv_c in ("Y", "YG")

                # "Yg" OU ("Y" + checkbox aterrado)
                hv_star_g = (hv_c == "YG") or (hv_c == "Y" and connection.meta.grounded_hv)
                lv_star_g = (lv_c == "YG") or (lv_c == "Y" and connection.meta.grounded_lv)

                # Usa Z0 diretamente (não 1/y0), porque é o que o dialog edita.
                z0 = c0(getattr(connection, "z0", None))

                if abs(z0) < 1e-12:
                    y0 = c0(getattr(connection, "y0", None))
                    if abs(y0) > 1e-12:
                        z0 = 1 / y0
                    else:
                        z0 = c0(getattr(connection, "z1", None))


                def add_zero_shunt(bus_i: int, xn_pu: float):
                    # Zeq = Z0 + 3*Zn, Zn = j*Xn
                    zn = 1j * float(xn_pu)
                    zeq = z0 + 3 * zn
                    if abs(zeq) < 1e-12:
                        return
                    bus_matrix.y_matrix[bus_i][bus_i] += 1 / zeq

                # Caso 1: Yg-Yg (sem delta) -> conecta barras na seq. zero
                if hv_star_g and lv_star_g and hv_star and lv_star and (not hv_delta) and (not lv_delta):
                    y_series = 0 if abs(z0) < 1e-12 else 1 / z0
                    tap_complex = connection.tap * cmath.exp(1j * getattr(connection, "phase", 0.0))
                    bus_matrix.connect_bus_to_bus(
                        y=y_series,
                        source=hv_idx,
                        target=lv_idx,
                        bc=f0(connection.b0),
                        tap=tap_complex,
                    )
                    continue

                # Caso 2: existe delta em um lado (ex.: Yg-Δ)
                # -> NÃO conecta as barras, só cria shunt no(s) lado(s) Yg aterrado(s)
                if hv_star_g and hv_star and not hv_delta:
                    add_zero_shunt(hv_idx, connection.meta.xn_hv_pu)

                if lv_star_g and lv_star and not lv_delta:
                    add_zero_shunt(lv_idx, connection.meta.xn_lv_pu)

                continue


                # Caso contrário: seq. zero NÃO atravessa entre as barras
                # Se houver lado aterrado (Yg), adiciona shunt para terra nesse lado:
                # Y_shunt = 1 / (Z0_trafo + 3*Zn), Zn = j*Xn
                def add_zero_shunt(bus_i: int, xn_pu: float):
                    if y_series == 0:
                        return
                    z0 = 1 / y_series
                    zn = 1j * float(xn_pu)
                    zeq = z0 + 3 * zn
                    if abs(zeq) < 1e-12:
                        return
                    ysh = 1 / zeq
                    bus_matrix.y_matrix[bus_i][bus_i] += ysh

                if hv_star_g and not hv_delta:
                    add_zero_shunt(hv_idx, connection.meta.xn_hv_pu)

                if lv_star_g and not lv_delta:
                    add_zero_shunt(lv_idx, connection.meta.xn_lv_pu)

                continue

            # ---------------------------------------------------------
            # Linha normal (ou trafo em seq. positiva/negativa)
            # ---------------------------------------------------------
            y1 = c0(getattr(connection, "y1", None))
            y2 = c0(getattr(connection, "y2", None)) or y1
            y0 = c0(getattr(connection, "y0", None)) or y1  # pra demo; se quiser mais “conservador”, usa 0+0j

            b1 = f0(getattr(connection, "b1", 0.0))
            b0 = f0(getattr(connection, "b0", 0.0))

            if sequence == "positive":
                y_series = y1
                bc = b1
            elif sequence == "negative":
                y_series = y2
                bc = b1
            elif sequence == "zero":
                y_series = y0
                bc = b0

            else:
                raise ValueError(f"Sequência inválida: {sequence}")

            bus_matrix.connect_bus_to_bus(
                y=y_series,
                source=self.buses[connection.tap_bus_id].index,
                target=self.buses[connection.z_bus_id].index,
                bc=bc,
                tap=connection.tap,
            )

        return bus_matrix

    def get_ybus_numpy_sequences(self):
        """
        Retorna (Y1, Y2, Y0) como np.ndarray para estudos de curto-circuito.

        Y1: sequência positiva
        Y2: sequência negativa
        Y0: sequência zero
        """
        Y1 = self.build_bus_matrix("positive").y_matrix
        Y2 = self.build_bus_matrix("negative").y_matrix
        Y0 = self.build_bus_matrix("zero").y_matrix

        return np.array(Y1, dtype=complex), np.array(Y2, dtype=complex), np.array(Y0, dtype=complex)


    def solve(
            self,
            max_iterations: int = 30,
            max_error: float = 10000.0,
            decoupled: bool = False,
            tol: float = 1e-6, 
        ) -> None:
        print("Solving power flow...")
        self.__yMatrix = self.build_bus_matrix()
        self.__update_indexes()

        # --- Padroniza potências especificadas como injeção líquida
        # Psch = Pgen - Pload
        # Qsch = Qgen - Qload
        for bus in self.buses.values():
            bus.p_sch = (getattr(bus, "p_gen", 0.0) - getattr(bus, "p_load", 0.0))
            bus.q_sch = (getattr(bus, "q_gen", 0.0) - getattr(bus, "q_load", 0.0))


        original_types = {bus.id: bus.type for bus in self.buses.values()}
        pv_to_pq_events: list[str] = []


        # guarda estado inicial por barra (não depende de self.indexes mudar no meio)
        initial_v = {bus.id: bus.v for bus in self.buses.values()}
        initial_o = {bus.id: bus.o for bus in self.buses.values()}  # rad

        if len(self.indexes) == 0:
            print("Nenhuma variável de estado para resolver (provável rede só SLACK).")
            print("Pulando Newton-Raphson e calculando P/Q com o estado atual.")
            for bus in self.buses.values():
                bus.p = calcP(bus, self.buses, self.__yMatrix) * self.base
                bus.q = calcQ(bus, self.buses, self.__yMatrix) * self.base
                print(bus)
            return
    
        n: int = len(self.buses)
        j: list[list[float]] = [[0 for _ in range(n)] for _ in range(n)]
        s_sch: list[float] = list[float]()
        for namedIndex in self.indexes:
            bus = self.buses[namedIndex.busId]
            if namedIndex.variable == "o" and (bus.type == BusType.PV or bus.type == BusType.PQ):
                s_sch.append(bus.p_sch)
            elif namedIndex.variable == "v" and (bus.type == BusType.PV or bus.type == BusType.PQ):
                s_sch.append(bus.q_sch)
        self.split_index: int = 0

        converged = False

        for iteration in range(1, max_iterations + 1):
            print(f"\nIteration {iteration}:")

            def getPowerResidues(bus_id: str, variable: str, power: str) -> float:
                bus = self.buses[bus_id]
                if power == "p" and (
                    bus.type.value == BusType.PV.value or bus.type.value == BusType.PQ.value
                ):
                    p_cal = calcP(bus, self.buses, self.__yMatrix)
                    p_sch = bus.p_sch / self.base  # TODO where more to update?
                    return p_sch - p_cal
                elif power == "q" and (bus.type == BusType.PV or bus.type == BusType.PQ):
                    q_cal = calcQ(bus, self.buses, self.__yMatrix)
                    q_sch = bus.q_sch / self.base  # TODO where more to update?
                    return q_sch - q_cal
                return 0

            def getJacobianElement(r_id: str, c_id: str, _: str, __: str, diff: str) -> float:
                dSdX: Callable[[str, str, dict[str, Bus], YBusSquareMatrix], float] = dPdO
                if diff == "∂p/∂o":
                    dSdX = dPdO
                    self.split_index += 1
                elif diff == "∂p/∂v":
                    dSdX = dPdV
                elif diff == "∂q/∂o":
                    dSdX = dQdO
                else:
                    dSdX = dQdV
                return dSdX(i_id=r_id, j_id=c_id, buses=self.buses, Y=self.__yMatrix)

            ds = self.__map_indexes_list(getPowerResidues)
            j = self.__map_indexes_matrix(getJacobianElement)

            mismatch = float(np.max(np.abs(np.array(ds, dtype=float))))
            print(f"mismatch={mismatch:.3e}")


            # decouple split index on jacobian matrix
            self.split_index = int(sqrt(self.split_index))
            if decoupled:
                j_dpdo = [row[: self.split_index] for row in j[: self.split_index]]
                j_dqdv = [row[self.split_index :] for row in j[self.split_index :]]

                dp = ds[: self.split_index]
                dq = ds[self.split_index :]

                Jp = np.array(j_dpdo, dtype=float)
                Jq = np.array(j_dqdv, dtype=float)
                dpv = np.array(dp, dtype=float)
                dqv = np.array(dq, dtype=float)

                do = np.linalg.solve(Jp, dpv)
                dv = np.linalg.solve(Jq, dqv)
                dX = np.concatenate((do, dv))

            else:
                J = np.array(j, dtype=float)
                b = np.array(ds, dtype=float)
                dX = np.linalg.solve(J, b)

            # ------------------------------
            # DAMPING: tenta reduzir passo se piorar mismatch
            # ------------------------------
            alpha = 1.0

            # salva estado atual para poder "voltar" se piorar
            state_backup = {b.id: (b.v, b.o) for b in self.buses.values()}

            def apply_step(a: float):
                for i, namedIndex in enumerate(self.indexes):
                    bus = self.buses[namedIndex.busId]
                    if namedIndex.variable == "o":
                        bus.o = bus.o + a * float(dX[i])
                    elif namedIndex.variable == "v":
                        bus.v = bus.v + a * float(dX[i])
                        bus.v = max(bus.v, 0.05)

            def restore():
                for bid, (v0, o0) in state_backup.items():
                    self.buses[bid].v = v0
                    self.buses[bid].o = o0

            # mismatch atual (antes de aplicar passo)
            mismatch0 = mismatch

            accepted = False
            for _ in range(8):  # tenta até 8 reduções (1, 0.5, 0.25, ...)
                restore()
                apply_step(alpha)

                # recalcula mismatch com o estado "tentado"
                ds_try = self.__map_indexes_list(getPowerResidues)
                mismatch_try = float(np.max(np.abs(np.array(ds_try, dtype=float))))

                if mismatch_try <= mismatch0:
                    mismatch = mismatch_try
                    accepted = True
                    break

                alpha *= 0.5

            if not accepted:
                # não conseguiu melhorar nem com alpha pequeno -> divergiu
                raise ValueError(f"NR divergiu: mismatch não melhora nem com damping (mismatch={mismatch0:.3e}).")

            print(f"alpha={alpha:.3f} mismatch-> {mismatch:.3e}")


            # for i, namedIndex in enumerate(self.indexes):
            #     bus_id = namedIndex.busId
            #     bus = self.buses[bus_id]
            #     if namedIndex.variable == "o":
            #         newO = bus.o + dX[i]
            #         # if newO > cmath.pi:
            #         #     newO = newO % (cmath.pi)
            #         # elif newO < -cmath.pi:
            #         #     newO = newO % (-cmath.pi)
            #         bus.o = newO

            #     elif namedIndex.variable == "v":
            #         bus.v = bus.v + float(dX[i])
            #         bus.v = max(bus.v, 0.05)  # evita V<=0 dar ruim

            err = sum([abs(x) for x in dX])
            # if err > max_error:
            #     print(f"|E| = {err}.  Diverged at {iteration}.")
            #     raise ValueError(f"Power flow diverged. {iteration} iterations.")

            has_to_update_indexes: bool = False
            for i, bus in enumerate(self.buses.values()):
                if bus.type == BusType.PV:
                    # Q calculado pelo fluxo é INJEÇÃO LÍQUIDA na barra: Qnet = Qg - Qload
                    q_net = calcQ(bus, self.buses, self.__yMatrix) * self.base

                    # Limites do JSON (q_min/q_max) são do GERADOR: Qg
                    q_gen = q_net + bus.q_load

                    if q_gen > bus.q_max or q_gen < bus.q_min:
                        print(
                            f"Bus {bus.name} (PV) has generator reactive power out of limits: "
                            f"Qg={q_gen:.2f} ({bus.q_min:.2f} - {bus.q_max:.2f}). "
                            f"(Qnet={q_net:.2f}, Qload={bus.q_load:.2f})"
                        )

                        # vira PQ e fixa o Q LÍQUIDO correspondente ao gerador no limite:
                        self.buses[bus.id].type = BusType.PQ
                        qg_lim = bus.q_max if q_gen > bus.q_max else bus.q_min
                        self.buses[bus.id].q_sch = qg_lim - bus.q_load  # <-- chave do conserto
                        has_to_update_indexes = True


                # if bus.type == BusType.PQ:
                #     if bus.v > 1.1 or bus.v < 0.9:
                #         print(
                #             f"Bus {bus.name} (PQ) has voltage out of limits: {bus.v:.2f} "
                #             f"(0.9 - 1.1)."
                #         )
                #         self.buses[bus.id].type = BusType.PV
                #         self.buses[bus.id].v_sch = 0.95 if bus.v < 0.95 else 1.05
                #         has_to_update_indexes = True


            if has_to_update_indexes:
                self.__update_indexes()
                ds = self.__map_indexes_list(getPowerResidues)
                mismatch = float(np.max(np.abs(np.array(ds, dtype=float))))
                print(f"mismatch(after PV->PQ)={mismatch:.3e}")


            if mismatch < tol:
                print(f"Converged at {iteration} (mismatch={mismatch:.3e}).")
                converged = True
                break
            else:
                print(f"|E| = {err}. End.")

        if not converged:
            raise ValueError("Power flow NÃO convergiu (atingiu max_iterations).")

        print("\nPower flow solved.")
        for bus in self.buses.values():
            bus.p = calcP(bus, self.buses, self.__yMatrix) * self.base
            bus.q = calcQ(bus, self.buses, self.__yMatrix) * self.base
            print(bus)

            print("\n================ DIAGNÓSTICO PF ================")
            # 1) Slack count
            slacks = [b for b in self.buses.values() if b.type == BusType.SLACK]
            print(f"Slack buses: {len(slacks)} -> {[b.id for b in slacks]}")

            # 2) PV -> PQ events
            if pv_to_pq_events:
                print("\nPV -> PQ (limites de Q estourados):")
                for s in pv_to_pq_events:
                    print("  -", s)
            else:
                print("\nPV -> PQ: nenhum (nenhum PV estourou Qmin/Qmax)")

            # 3) Tipos finais vs originais (útil pra casos grandes)
            changed = []
            for b in self.buses.values():
                if original_types.get(b.id) != b.type:
                    changed.append((b.id, original_types[b.id].name, b.type.name))
            if changed:
                print("\nMudanças de tipo (orig -> final):")
                for bid, t0, t1 in changed:
                    print(f"  - {bid}: {t0} -> {t1}")

            # 4) Checagem de base/unidade (heurística simples)
            # Se p_load/p_gen forem pequenos (<5) em casos IEEE grandes, pode estar em pu e você está dividindo por base de novo.
            small_p = []
            for b in self.buses.values():
                if abs(getattr(b, "p_load", 0.0)) > 0 and abs(getattr(b, "p_load", 0.0)) < 5:
                    small_p.append(b.id)
            if small_p:
                print("\nALERTA: p_load pequeno em algumas barras (<5).")
                print("Isso pode indicar que o JSON está em pu, mas o código está tratando como MW e dividindo por base.")
                print("Barras com p_load pequeno:", small_p[:10], ("..." if len(small_p) > 10 else ""))

            print("================================================\n")


        for index in self.indexes:
            bus = self.buses[index.busId]

            if index.variable == "v":
                start = initial_v.get(bus.id, bus.v)
                final = bus.v
            else:
                start = initial_o.get(bus.id, bus.o) * 180.0 / cmath.pi
                final = bus.o * 180.0 / cmath.pi

            rpd = 0.0
            if final + start != 0.0:
                rpd = 100.0 * abs(final - start) / ((final + start) / 2)

            print(
                f"{index.variable}{bus.index:3d} {start:+8.4f} -> {final:+8.4f} (RPD {rpd:+4.4f}%)"
            )


    def print_state(self):
        for bus in self.buses.values():
            print(f"Bus: {bus.name}, V: {bus.v}, O: {bus.o}, P: {bus.p}, Q: {bus.q}")
            

    # --------------------------------------------------------------------
    # Adição do código para cálculo de faltas

    def get_ybus_numpy(self) -> numpy.ndarray:
        """
        Devolve a matriz Ybus interna como um numpy.ndarray de complexos.
        Deve ser chamada DEPOIS de solve(), pois usa self.__yMatrix.
        """
        # self.__yMatrix.y_matrix é uma lista de listas de complexos
        return numpy.array(self.__yMatrix.y_matrix, dtype=complex)

    def get_bus_index_dict(self) -> dict[str, int]:
        """
        Devolve um dicionário {bus_id: indice_na_matriz}.
        """
        return {bus.id: bus.index for bus in self.buses.values()}

    def get_bus_voltages_complex_pu(self) -> dict[str, complex]:
        """
        Devolve um dicionário {bus_id: V_complex_pu} com a tensão pré-falta.

        Usa V = |V| * e^{j·theta}, onde:
          - bus.v é o módulo em pu
          - bus.o é o ângulo em radianos
        """
        return {
            bus.id: bus.v * cmath.exp(1j * bus.o)
            for bus in self.buses.values()
        }

    # --------------------------------------------------------------------


    def transposeList(self, list: list[float]) -> list[list[float]]:
        return [[list[j]] for j in range(len(list))]

    def __update_indexes(self):
        o_indexes: list[VariableIndex] = list[VariableIndex]()
        v_indexes: list[VariableIndex] = list[VariableIndex]()

        for source in self.buses.values():
            if source.type is BusType.PQ:
                o_indexes.append(
                    VariableIndex(variable="o", power="p", busIndex=source.index, busId=source.id)
                )
                v_indexes.append(
                    VariableIndex(variable="v", power="q", busIndex=source.index, busId=source.id)
                )
            if source.type is BusType.PV:
                o_indexes.append(
                    VariableIndex(variable="o", power="p", busIndex=source.index, busId=source.id)
                )

        self.indexes = o_indexes + v_indexes

    def print_indexes(self) -> None:
        for v in self.variable_indexes:
            print(str(v))

    def __map_indexes_matrix(
        self, x: Callable[[str, str, str, str, str], Any]  # row, column, variable, power, diff]
    ) -> list[list[Any]]:
        return [
            [
                x(
                    row_index.busId,
                    column_index.busId,
                    column_index.variable,
                    row_index.power,
                    f"∂{row_index.power}/∂{column_index.variable}",
                )
                for _, column_index in enumerate(self.indexes)
            ]
            for _, row_index in enumerate(self.indexes)
        ]

    def __map_indexes_list(
        self, x: Callable[[str, str, str], Any]  # row, variable, power
    ) -> list[Any]:
        return [x(index.busId, index.variable, index.power) for _, index in enumerate(self.indexes)]

    def print_data(self):
        y = self.build_bus_matrix()
        output = ["Data:", "\nBuses:"]


        # 1. Cabeçalho das Barras
        # Usamos larguras parecidas com as do Bus.__str__ para alinhar
        # ID(4) Type(7) ... P(8) Q(8) ...
        header_bus = (
            f"{'ID':^4} {'Type':^7}"            # ID(4) e Type(7)
            f"{' ':6}{'V (pu)':<6}{' ':3}{'Angle':<9} |"   # Espaço(", v = "), V(6), Espaço(" ∠ "), Angle(9), " |"
            f"{' ':6}{'P (MW)':>8}{' ':6}{'Q (MVAr)':>8}"   # Espaço(", p = "), P(8), Espaço(", q = "), Q(8)
            f"{' ':9}{'P_sch':>8}{' ':9}{'Q_sch':>8} |"     # Espaço(", p_sch: "), P_sch(8), Espaço(", q_sch: "), Q_sch(8)
        )

        output.append(header_bus)
        output.append("-" * len(header_bus)) # Linha divisória


        
        # ... Adicione informações de Buses e Connections à lista 'output' ...
        for index, bus in enumerate(self.buses.values()):
            bus.index = index
            output.append(str(bus))


# --- SEÇÃO DE CONEXÕES (LINES) ---
        output.append("\nConnections:")
        
        # 2. Cabeçalho das Conexões
        # Baseado no formato: "   1 ->    2, y=..."
        header_line = (
            f"{'From':>4} -> {'To':>4}  "
            f"{'Admittance (Y)':<18} {'B (sh)':<10} {'Tap':<8}"
        )
        output.append(header_line)
        output.append("-" * len(header_line)) # Linha divisória


        #output.append("\nConnections:")
        for connection in self.connections.values():
            output.append(str(connection))

        output.append("\nY matrix:")


        for row in y.y_matrix:
            # 1. Crie uma lista de strings, onde cada número
            #    é formatado para ter 18 caracteres de largura, 
            #    alinhado à direita.
            padded_row = [f"{f'{complex(x.real, x.imag):.2f}': >18}" for x in row]
            
            # 2. Junte as colunas (agora alinhadas) com um único espaço.
            output.append(" ".join(padded_row))
        
        # Retorne a string formatada em vez de imprimir
        return "\n".join(output)
