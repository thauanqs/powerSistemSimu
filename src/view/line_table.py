from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTableWidget,
)

from controllers.simulator_controller import ElementEvent, SimulatorController
from models.line import Line
from models.network_element import NetworkElement
from view.line_table_row import LineTableRow


class LineTable(QWidget):
    def __init__(self):
        super().__init__()
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
        for line in self.simulatorInstance.connections:
            row = self.table.rowCount()
            self.table.insertRow(row)
            line_row = LineTableRow(line)
            widgets = line_row.get_widgets()
            for col, widget in enumerate(widgets):
                self.table.setCellWidget(row, col, widget)
            self.items.append(line.id)

    def circuitListener(self, element: NetworkElement, event: ElementEvent):
        if event is ElementEvent.CREATED and isinstance(element, Line):
            row = self.table.rowCount()
            self.table.insertRow(row)
            bus_row = LineTableRow(element)
            widgets = bus_row.get_widgets()
            for col, widget in enumerate(widgets):
                self.table.setCellWidget(row, col, widget)
            self.items.append(element.id)
            return

        if event is ElementEvent.DELETED and isinstance(element, Line):
            for i, bus_id in enumerate(self.items):
                if bus_id == element.id:
                    self.table.removeRow(i)
                    self.items.pop(i)
                    break
