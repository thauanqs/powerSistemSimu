from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QLineEdit,
    QComboBox,
    QCheckBox,
    QDialogButtonBox,
    QMessageBox,
)

from controllers.simulator_controller import SimulatorController
from models.bus import Bus, BusType
from models.generator import Generator, GeneratorSC

class GeneratorDialog(QDialog):
    def __init__(self, bus: Bus):
        super().__init__()
        self.bus = bus
        self.setWindowTitle(f"Gerador na barra {bus.name}")

        layout = QFormLayout(self)

        ctrl = SimulatorController.instance()
        existing = ctrl.getGeneratorByBusId(bus.id)

        self.kind = QComboBox()
        self.kind.addItems(["SLACK", "PV"])
        self.kind.setCurrentText("SLACK" if bus.type == BusType.SLACK else "PV")

        # --------------------
        # Parâmetros de PF
        # --------------------
        self.p_gen = QLineEdit(str(existing.p_gen if existing else bus.p_gen))
        self.v_set = QLineEdit(str(existing.v_set if existing else bus.v))

        self.q_min = QLineEdit(str((existing.q_min if existing else bus.q_min)))
        self.q_max = QLineEdit(str((existing.q_max if existing else bus.q_max)))

        # --------------------
        # Parâmetros de curto-circuito (pu)
        # --------------------
        sc = existing.sc if existing else GeneratorSC()

        self.x1 = QLineEdit(str(sc.x1_pu))
        self.x2 = QLineEdit(str(sc.x2_pu))
        self.x0 = QLineEdit(str(sc.x0_pu))

        self.grounded = QCheckBox("Neutro aterrado")
        self.grounded.setChecked(bool(sc.grounded))
        self.xn = QLineEdit(str(sc.xn_pu))

        layout.addRow("Tipo", self.kind)
        layout.addRow("Pgen (MW na base do sistema)", self.p_gen)
        layout.addRow("Vset (pu)", self.v_set)
        layout.addRow("Qmin (MVAr)", self.q_min)
        layout.addRow("Qmax (MVAr)", self.q_max)

        layout.addRow("X1'' (pu)", self.x1)
        layout.addRow("X2 (pu)", self.x2)
        layout.addRow("X0 (pu)", self.x0)
        layout.addRow(self.grounded)
        layout.addRow("Xn (pu)  [0 = sólido]", self.xn)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._apply)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _apply(self):
        try:
            bus_type = BusType[self.kind.currentText()]

            pgen = float(self.p_gen.text())
            vset = float(self.v_set.text())
            qmin = float(self.q_min.text())
            qmax = float(self.q_max.text())

            x1 = float(self.x1.text())
            x2 = float(self.x2.text())
            x0 = float(self.x0.text())
            xn = float(self.xn.text())

            sc = GeneratorSC(
                x1_pu=x1,
                x2_pu=x2,
                x0_pu=x0,
                grounded=bool(self.grounded.isChecked()),
                xn_pu=xn,
            )

            # Atualiza a barra (PF)
            new_bus = self.bus.copy_with(
                type=bus_type,
                p_gen=pgen,
                q_gen=self.bus.q_gen,
                v=vset,
                q_min=qmin,
                q_max=qmax,
            )

            ctrl = SimulatorController.instance()
            ctrl.updateElement(new_bus)

            # Cria/atualiza o gerador explícito (curto-circuito)
            existing = ctrl.getGeneratorByBusId(self.bus.id)
            gen_id = existing.id if existing else None

            gen = Generator(
                bus_id=self.bus.id,
                name=f"G@{self.bus.name}",
                p_gen=pgen,
                v_set=vset,
                q_min=qmin,
                q_max=qmax,
                sc=sc,
                id=gen_id,
            )
            ctrl.upsertGenerator(gen)

            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Erro", str(e))

    def on_ok(self):
        ctrl = SimulatorController.instance()

        gen = Generator(
            id=f"GEN_{self.bus.id}",      # ou id vazio se teu Generator cria sozinho
            bus_id=self.bus.id,
            name=f"Gen {self.bus.name}",
            p_gen=self.pgen_mw.value(),   # exemplo
            v_set=self.vset.value(),
            q_min=self.qmin.value(),
            q_max=self.qmax.value(),
            enabled=True,
            sc=GeneratorSCData(
                x1_pu=self.x1.value(),
                x2_pu=self.x2.value(),
                x0_pu=self.x0.value(),
                neutral_grounded=self.chk_neutro.isChecked(),
                xn_pu=self.xn.value(),
            ),
        )

        ctrl.upsertGenerator(gen)

        # se quiser: garante que a barra vira PV/SLACK conforme o combo
        # bus2 = self.bus.copy_with(type=BusType.PV, v=self.vset.value(), ...)
        # ctrl.updateElement(bus2)

        self.accept()
