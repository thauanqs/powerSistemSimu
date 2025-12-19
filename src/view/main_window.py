from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QKeySequence, QFont
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QHBoxLayout,
    QSizePolicy,
)

from controllers.simulator_controller import SimulatorController
from view.board_view import BoardView
from view.bus_table import BusTable


from view.line_table import LineTable
from view.text_field import TextField
from PySide6.QtWidgets import QFileDialog
import os


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        centralWidget = QWidget()
        simulatorInstance = SimulatorController.instance()
        self.setWindowTitle("Power Systems Simulator - Board")
        # Layout creation
        top_row = QHBoxLayout()
        bottom_row = QHBoxLayout()

        toolbar = self.menuBar()
        toolbar.setNativeMenuBar(False)

        project = toolbar.addMenu("Project")
        projectNew = QAction("New", project)

        projectNew.triggered.connect(self.new_project)
        project.addAction(projectNew)

        projectOpen = QAction("Open", project)
        projectOpen.setShortcut(QKeySequence.StandardKey.Open)
        projectOpen.triggered.connect(self.import_project_from_json)
        project.addAction(projectOpen)

        projectSave = QAction("Save", project)
        projectSave.setShortcut(QKeySequence.StandardKey.Save)
        projectSave.triggered.connect(self.save_project_to_json)
        project.addAction(projectSave)

        projectExportPDF = QAction("Export PDF", project)
        projectExportPDF.setShortcut(QKeySequence("Ctrl+E"))
        projectExportPDF.triggered.connect(self.export_pdf)
        project.addAction(projectExportPDF)

        projectImportIeee = QAction("Open IEEE ", project)
        projectImportIeee.setShortcut(QKeySequence("Ctrl+I"))
        projectImportIeee.triggered.connect(self.import_project_from_ieee)
        project.addAction(projectImportIeee)

        view = toolbar.addMenu("View")
        viewBars = QAction("Bars", view)
        viewBars.triggered.connect(self.show_bus_window)
        view.addAction(viewBars)

        viewLine = QAction("Lines", view)
        viewLine.triggered.connect(self.show_line_window)
        view.addAction(viewLine)

        show = toolbar.addMenu("Show")
        showYMatrix = QAction("Y Matrix", show)

        # 1. Conecte o MENU (showYMatrix) ao seu método
        showYMatrix.triggered.connect(self.show_y_matrix_window)

       

        
        show.addAction(showYMatrix)

        run = toolbar.addMenu("Run")
        runLoadFlow = QAction("Load Flow", run)
        runLoadFlow.setShortcut(QKeySequence("Ctrl+R"))
        runLoadFlow.triggered.connect(SimulatorController.instance().runPowerFlow)
        run.addAction(runLoadFlow)

        # Layout Alignment configuration
        top_row.setAlignment(Qt.AlignmentFlag.AlignLeft)
        bottom_row.setAlignment(Qt.AlignmentFlag.AlignLeft)

        addBusButton = QPushButton("Add Bus")
        addBusButton.setShortcut(QKeySequence("Ctrl+B"))
        addBusButton.setToolTip("Add a new bus to the network. Shortcut: Ctrl+B or Command+B")
        addBusButton.setFixedSize(70, 30)
        addBusButton.setIconSize(QSize(70, 30))

        show_y_bar_matrix_button = QPushButton("Print Network") #importante
        show_y_bar_matrix_button.setFixedSize(110, 30)

        self.powerBaseField = TextField[int](
            type=int,
            title="base",
            trailing="MVA",
            on_focus_out=self.on_power_base_changed,
            value=int(SimulatorController.instance().power_base_mva),
        )

        self.board = BoardView()

        # Screen montage
        column = QVBoxLayout(centralWidget)
        column.addLayout(top_row)
        column.addWidget(self.board)
        column.addLayout(bottom_row)

        simulatorInstance = SimulatorController.instance()

        # Connect button signal to the board's addSquare method.
        addBusButton.clicked.connect(lambda: simulatorInstance.addBus())
        show_y_bar_matrix_button.clicked.connect(self.show_network_data_window)  #importante

        # Add widgets to the layout.
        top_row.addWidget(self.powerBaseField)

        # Create a horizontal layout to place the board view on the left and a new widget on the right.

        bottom_row.addWidget(addBusButton)
        bottom_row.addWidget(show_y_bar_matrix_button)

        self.setCentralWidget(centralWidget)

    def show_bus_window(self):
        networkWindow = QMainWindow(parent=self)
        networkWindow.setWindowTitle("Bus Table")
        centralWidget = QWidget()
        layout = QVBoxLayout(centralWidget)
        layout.setContentsMargins(0, 0, 0, 0)

        busTable = BusTable()
        busTable.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        layout.addWidget(busTable)

        networkWindow.setCentralWidget(centralWidget)
        networkWindow.resize(1530, 600)
        networkWindow.show()

    def show_line_window(self):
        lineWindow = QMainWindow(parent=self)
        lineWindow.setWindowTitle("Line Table")
        centralWidget = QWidget()
        layout = QVBoxLayout(centralWidget)
        layout.setContentsMargins(0, 0, 0, 0)

        rightWidget = LineTable()
        rightWidget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        layout.addWidget(rightWidget)

        lineWindow.setCentralWidget(centralWidget)
        lineWindow.resize(930, 600)
        lineWindow.show()

    def print_network(self): #importante
        SimulatorController.instance().printNetwork()

    def show_y_matrix_window(self):
        # Usaremos o mesmo método para ambos, apenas para fins de demonstração
        self.show_network_data_window()

    def show_network_data_window(self):
        from PySide6.QtWidgets import QMainWindow, QPlainTextEdit, QWidget, QVBoxLayout
        
        # 1. Obter a string de dados do Controller
        data_string = SimulatorController.instance().printNetwork() 
        
        # 2. Configurar a nova janela
        dataWindow = QMainWindow(parent=self)
        dataWindow.setWindowTitle("Network Data and Y Matrix")
        
        centralWidget = QWidget()
        layout = QVBoxLayout(centralWidget)
        
        # 3. Widget de texto para exibir os dados
        text_widget = QPlainTextEdit(data_string)
        text_widget.setReadOnly(True)

        # Define uma fonte monoespaçada (Consolas, Courier New, etc.)
        text_widget.setFont(QFont("Courier New", 10))
        
        layout.addWidget(text_widget)
        dataWindow.setCentralWidget(centralWidget)
        
        dataWindow.resize(800, 600)
        dataWindow.show()

    def on_power_base_changed(self):
        controller = SimulatorController.instance()
        powerBase = self.powerBaseField.getValue()
        if powerBase == None or powerBase <= 0:
            controller = SimulatorController.instance()
            self.powerBaseField.setValue(int(controller.power_base_mva))
            return
        controller.power_base_mva = float(powerBase)

    def new_project(self):
        SimulatorController.instance().clear_state()

    def import_project_from_json(self):
        self.board.import_json()

    def save_project_to_json(self):
        self.board.export_json()

    def import_project_from_ieee(self):
        self.board.import_ieee()

    def export_pdf(self):
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar Relatório PDF",
            "relatorio_fluxo_potencia.pdf",
            "PDF Files (*.pdf)"
        )

        if not filename:
            return

        if not filename.lower().endswith(".pdf"):
            filename += ".pdf"

        SimulatorController.instance().export_pdf_report(filename)
