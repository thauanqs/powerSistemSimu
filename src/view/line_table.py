from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTableWidget,
)

from controllers.simulator_controller import ElementEvent, SimulatorController
from models.line import Line
from models.network_element import NetworkElement
from view.line_table_row import LineTableRow
from models.line import Line
from models.transformer import Transformer

class LineTable(QWidget):
    def __init__(self):
        super().__init__()
        self.rows: list[LineTableRow] = []
        self.simulatorInstance = SimulatorController.instance()
        self.simulatorInstance.listen(self.circuitListener)
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        self.fields = [
            "from",
            "to",
            "",
            "r",
            "x",
            "g",
            "b",
            "bc",
            "tap",
        ]

        self.table = QTableWidget()
        self.table.setColumnCount(len(self.fields))
        self.table.setHorizontalHeaderLabels(self.fields)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        self.items: list[str] = []

        for conn in self.simulatorInstance.connections:
            if type(conn) is not Line:
                continue

            row = LineTableRow(conn)
            self.rows.append(row)

            i = self.table.rowCount()
            self.table.insertRow(i)

            for col, w in enumerate(row.get_widgets()):
                self.table.setCellWidget(i, col, w)

            self.items.append(conn.id)  # <-- ERA line.id


    def circuitListener(self, element: NetworkElement, event: ElementEvent):
        if event is ElementEvent.CREATED and type(element) is Line:
            row = self.table.rowCount()
            self.table.insertRow(row)
            new_row = LineTableRow(element)
            self.rows.append(new_row)
            widgets = new_row.get_widgets()
            for col, widget in enumerate(widgets):
                self.table.setCellWidget(row, col, widget)
            self.items.append(element.id)
            return

        if event is ElementEvent.CREATED and type(element) is Line:
            for i, line_id in enumerate(self.items):
                if line_id == element.id:
                    self.table.removeRow(i)
                    self.items.pop(i)
                    self.rows.pop(i)  # <-- add
                    break

    def select_line(self, line_id: str) -> None:
        try:
            row = self.items.index(line_id)
        except ValueError:
            return
        self.table.setCurrentCell(row, 0)
        self.table.selectRow(row)

