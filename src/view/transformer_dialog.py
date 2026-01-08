from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QComboBox, QCheckBox,
    QDialogButtonBox, QMessageBox
)

from controllers.simulator_controller import SimulatorController
from models.transformer import Transformer


class TransformerDialog(QDialog):
    def __init__(self, trafo: Transformer):
        super().__init__()
        self.trafo = trafo
        self.setWindowTitle(f"Transformador - {trafo.name}")

        layout = QFormLayout(self)

        # ----- Meta -----
        self.sn = QLineEdit(str(trafo.meta.sn_mva))
        self.hv = QLineEdit(str(trafo.meta.hv_kv))
        self.lv = QLineEdit(str(trafo.meta.lv_kv))

        self.conn_hv = QComboBox()
        self.conn_hv.addItems(["D", "Y", "Yg"])
        self.conn_hv.setCurrentText(trafo.meta.conn_hv)

        self.conn_lv = QComboBox()
        self.conn_lv.addItems(["D", "Y", "Yg"])
        self.conn_lv.setCurrentText(trafo.meta.conn_lv)

        self.gnd_hv = QCheckBox("HV aterrado")
        self.gnd_hv.setChecked(trafo.meta.grounded_hv)

        self.gnd_lv = QCheckBox("LV aterrado")
        self.gnd_lv.setChecked(trafo.meta.grounded_lv)

        self.xn_hv = QLineEdit(str(trafo.meta.xn_hv_pu))
        self.xn_lv = QLineEdit(str(trafo.meta.xn_lv_pu))

        # ----- Impedâncias do ramo do trafo (em pu) -----
        # z1 (usa se existir; senão deriva de g+j*b)
        z1 = trafo.z1
        if z1 is None:
            y = complex(trafo.g, trafo.b)
            z1 = 0j if abs(y) < 1e-12 else (1 / y)

        z2 = trafo.z2 if trafo.z2 is not None else z1
        z0 = trafo.z0 if trafo.z0 is not None else (3 * z1)

        self.r1 = QLineEdit(f"{z1.real:.6f}")
        self.x1 = QLineEdit(f"{z1.imag:.6f}")

        self.r0 = QLineEdit(f"{z0.real:.6f}")
        self.x0 = QLineEdit(f"{z0.imag:.6f}")

        # (opcional) se quiser expor z2 também:
        self.r2 = QLineEdit(f"{z2.real:.6f}")
        self.x2 = QLineEdit(f"{z2.imag:.6f}")

        # ----- PF (já existia no Line) -----
        self.tap = QLineEdit(str(trafo.tap))
        self.phase = QLineEdit(str(trafo.phase))

        layout.addRow("Snom (MVA)", self.sn)
        layout.addRow("Vnom HV (kV)", self.hv)
        layout.addRow("Vnom LV (kV)", self.lv)
        layout.addRow("Ligação HV", self.conn_hv)
        layout.addRow("Ligação LV", self.conn_lv)
        layout.addRow("", self.gnd_hv)
        layout.addRow("", self.gnd_lv)
        layout.addRow("Xn HV (pu)", self.xn_hv)
        layout.addRow("Xn LV (pu)", self.xn_lv)

        layout.addRow("R1 (pu)", self.r1)
        layout.addRow("X1 (pu)", self.x1)
        layout.addRow("R2 (pu)", self.r2)
        layout.addRow("X2 (pu)", self.x2)
        layout.addRow("R0 (pu)", self.r0)
        layout.addRow("X0 (pu)", self.x0)

        layout.addRow("Tap", self.tap)
        layout.addRow("Defasagem (rad)", self.phase)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._apply)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _apply(self):
        try:
            # ---- meta ----
            self.trafo.meta.sn_mva = float(self.sn.text())
            self.trafo.meta.hv_kv = float(self.hv.text())
            self.trafo.meta.lv_kv = float(self.lv.text())
            self.trafo.meta.conn_hv = self.conn_hv.currentText()
            self.trafo.meta.conn_lv = self.conn_lv.currentText()
            self.trafo.meta.grounded_hv = self.gnd_hv.isChecked()
            self.trafo.meta.grounded_lv = self.gnd_lv.isChecked()
            self.trafo.meta.xn_hv_pu = float(self.xn_hv.text())
            self.trafo.meta.xn_lv_pu = float(self.xn_lv.text())

            # ---- impedâncias ----
            z1 = complex(float(self.r1.text()), float(self.x1.text()))
            z2 = complex(float(self.r2.text()), float(self.x2.text()))
            z0 = complex(float(self.r0.text()), float(self.x0.text()))

            # coerência: se z muito pequeno, evita infinito
            y1 = 0j if abs(z1) < 1e-12 else (1 / z1)

            # atualiza campos do "Line" interno do trafo
            self.trafo.z1 = z1
            self.trafo.z2 = z2
            self.trafo.z0 = z0
            self.trafo.g = y1.real
            self.trafo.b = y1.imag

            # ---- PF ----
            self.trafo.tap = float(self.tap.text())
            self.trafo.phase = float(self.phase.text())

            SimulatorController.instance().updateElement(self.trafo)
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Erro", str(e))

    @property
    def y1(self) -> complex:
        if self.z1 is not None:
            return 0j if abs(self.z1) < 1e-12 else 1 / self.z1
        return complex(self.g, self.b)

    @property
    def y2(self) -> complex:
        if self.z2 is not None:
            return 0j if abs(self.z2) < 1e-12 else 1 / self.z2
        return self.y1

    @property
    def y0(self) -> complex:
        if self.z0 is not None:
            return 0j if abs(self.z0) < 1e-12 else 1 / self.z0
        return self.y1  # ou 3*self.y1, se quiser teu default didático
