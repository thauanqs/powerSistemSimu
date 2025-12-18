from typing import Optional
import numpy as np

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QHeaderView,
)

from models.faults import FaultStudyResult


class FaultResultDialog(QDialog):
    def __init__(self, result: FaultStudyResult, parent: Optional[QDialog] = None):
        super().__init__(parent)

        self.result = result

        layout = QVBoxLayout(self)

        # Descrição da falta
        desc_label = QLabel(self.result.spec.description, self)
        layout.addWidget(desc_label)

        # Tabela com resultados por barra
        table = QTableWidget(self)
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(
            ["Barra", "|V| (pu)", "∠ V (°)", "|I| (pu)", "∠ I (°)"]
        )

        buses = list(self.result.buses.values())
        table.setRowCount(len(buses))

        for row, bus_result in enumerate(buses):
            v = bus_result.v_pu
            i = bus_result.i_pu

            v_mag = np.abs(v)
            v_ang = np.rad2deg(np.angle(v))

            i_mag = np.abs(i)
            i_ang = np.rad2deg(np.angle(i))

            table.setItem(row, 0, QTableWidgetItem(str(bus_result.bus_id)))
            table.setItem(row, 1, QTableWidgetItem(f"{v_mag:.4f}"))
            table.setItem(row, 2, QTableWidgetItem(f"{v_ang:.2f}"))
            table.setItem(row, 3, QTableWidgetItem(f"{i_mag:.4f}"))
            table.setItem(row, 4, QTableWidgetItem(f"{i_ang:.2f}"))

        table.resizeColumnsToContents()

        # Colunas se ajustam quando a janela for redimensionada
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)

        layout.addWidget(table)

        # Botão fechar
        close_btn = QPushButton("Fechar", self)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        # Tamanho inicial + permitir redimensionar
        self.resize(500, 400)
        self.setSizeGripEnabled(True)
