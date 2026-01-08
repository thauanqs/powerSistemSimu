from __future__ import annotations

from typing import Optional
from math import sqrt

import numpy as np
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QHeaderView,
    QInputDialog,
)

from models.bus import Bus
from models.faults import FaultStudyResult


class FaultResultDialog(QDialog):
    def __init__(
        self,
        result: FaultStudyResult,
        buses: dict[str, Bus],
        s_base_mva: float,
        parent=None,
    ):
        super().__init__(parent)

        self.result = result
        self._buses = buses
        self._s_base_mva = float(s_base_mva)

        # Pergunta Vbase (kV LL) UMA vez (como era antes).
        # Se digitar 0, tenta usar v_rated de cada barra (se definido).
        default_vbase = 13.8

        vbase_kv, ok = QInputDialog.getDouble(
            self,
            "Base de tensão",
            "Informe Vbase (kV, linha-linha) para converter pu -> kA\n"
            "(dica: use 0 para pegar a base de cada barra, se definida):",
            float(default_vbase),
            0.0,
            1000.0,
            3,
        )
        if not ok:
            vbase_kv = float(default_vbase)

        self._vbase_override_kv: float = float(vbase_kv)

        layout = QVBoxLayout(self)

        desc_label = QLabel(self.result.spec.description, self)
        layout.addWidget(desc_label)

        table = QTableWidget(self)
        table.setColumnCount(10)
        table.setHorizontalHeaderLabels(
            [
                "Barra",
                "Va (pu)",
                "Vb (pu)",
                "Vc (pu)",
                "Ia (pu)",
                "Ib (pu)",
                "Ic (pu)",
                "Ia (kA)",
                "Ib (kA)",
                "Ic (kA)",
            ]
        )

        def fmt_polar(z: complex) -> str:
            mag = float(np.abs(z))
            ang = float(np.rad2deg(np.angle(z)))
            return f"{mag:.4f} ∠ {ang:.2f}°"

        def ibase_ka_for_bus(bus_id: str) -> Optional[float]:
            # override > 0: usa o valor digitado pelo usuário para todas as barras
            if self._vbase_override_kv > 0.0:
                return self._s_base_mva / (sqrt(3) * self._vbase_override_kv)

            # override == 0: tenta pegar a base da própria barra
            b = self._buses.get(bus_id)
            if b is None:
                return None

            # teu Bus usa v_rated (kV)
            v_kv = float(getattr(b, "v_rated", 0.0) or 0.0)

            # fallback (se um dia renomear)
            if v_kv <= 0.0:
                v_kv = float(getattr(b, "base_kv", 0.0) or 0.0)

            if v_kv <= 0.0:
                return None

            return self._s_base_mva / (sqrt(3) * v_kv)

        buses_res = list(self.result.buses.values())
        table.setRowCount(len(buses_res))

        for row, bus_result in enumerate(buses_res):
            if bus_result.v_abc is not None:
                Va, Vb, Vc = bus_result.v_abc
            else:
                Va, Vb, Vc = (bus_result.v_pu, 0 + 0j, 0 + 0j)

            if bus_result.i_abc is not None:
                Ia, Ib, Ic = bus_result.i_abc
            else:
                Ia, Ib, Ic = (bus_result.i_pu, 0 + 0j, 0 + 0j)

            table.setItem(row, 0, QTableWidgetItem(str(bus_result.bus_id)))
            table.setItem(row, 1, QTableWidgetItem(fmt_polar(Va)))
            table.setItem(row, 2, QTableWidgetItem(fmt_polar(Vb)))
            table.setItem(row, 3, QTableWidgetItem(fmt_polar(Vc)))
            table.setItem(row, 4, QTableWidgetItem(fmt_polar(Ia)))
            table.setItem(row, 5, QTableWidgetItem(fmt_polar(Ib)))
            table.setItem(row, 6, QTableWidgetItem(fmt_polar(Ic)))

            ibase = ibase_ka_for_bus(bus_result.bus_id)
            if ibase is None:
                table.setItem(row, 7, QTableWidgetItem("—"))
                table.setItem(row, 8, QTableWidgetItem("—"))
                table.setItem(row, 9, QTableWidgetItem("—"))
            else:
                table.setItem(row, 7, QTableWidgetItem(fmt_polar(Ia * ibase)))
                table.setItem(row, 8, QTableWidgetItem(fmt_polar(Ib * ibase)))
                table.setItem(row, 9, QTableWidgetItem(fmt_polar(Ic * ibase)))

        table.resizeColumnsToContents()
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(table)

        close_btn = QPushButton("Fechar", self)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        self.resize(800, 420)
        self.setSizeGripEnabled(True)
