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

from PySide6.QtWidgets import QMessageBox, QInputDialog
from models.transformer import Transformer
from view.transformer_dialog import TransformerDialog

from models.bus import Bus, BusType
from view.generator_dialog import GeneratorDialog
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

        addTrafoButton = QPushButton("Add Trafo")
        addTrafoButton.setShortcut(QKeySequence("Ctrl+T"))
        addTrafoButton.setToolTip("Add a transformer between two buses. Shortcut: Ctrl+T")
        addTrafoButton.setFixedSize(90, 30)

        addGenButton = QPushButton("Add Gen")
        addGenButton.setShortcut(QKeySequence("Ctrl+G"))
        addGenButton.setToolTip("Add/configure a generator at a bus. Shortcut: Ctrl+G")
        addGenButton.setFixedSize(80, 30)
        addGenButton.clicked.connect(self.add_generator)
        bottom_row.addWidget(addGenButton)

        show_y_bar_matrix_button = QPushButton("Print Network")
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

        def _create_default_bus() -> Bus:
            return Bus(
                id="",        
                name="",
                type=BusType.PQ,
                v=1.0,
                o=0.0,
                p_load=0.0,
                q_load=0.0,
                p_gen=0.0,
                q_gen=0.0,
                g_shunt=0.0,
                b_shunt=0.0,
                q_min=-9999.0,
                q_max=9999.0,
            )

        # Connect button signal to the board's addSquare method.
        addBusButton.clicked.connect(lambda: simulatorInstance.addBus(Bus(type=BusType.PQ)))
        addTrafoButton.clicked.connect(self.add_transformer)
        show_y_bar_matrix_button.clicked.connect(self.print_network)

        # Add widgets to the layout.
        top_row.addWidget(self.powerBaseField)

        # Create a horizontal layout to place the board view on the left and a new widget on the right.

        bottom_row.addWidget(addBusButton)
        bottom_row.addWidget(addTrafoButton)
        bottom_row.addWidget(addGenButton)
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

    def add_transformer(self):
        ctrl = SimulatorController.instance()
        buses = ctrl.buses

        if len(buses) < 2:
            QMessageBox.warning(self, "Transformador", "Crie pelo menos 2 barras antes.")
            return

        # Labels amigáveis e mapa label -> id
        labels = [f"{b.number} - {b.name} ({b.type.name})" for b in buses]
        label_to_id = {labels[i]: buses[i].id for i in range(len(buses))}

        src_label, ok = QInputDialog.getItem(
            self, "Adicionar Transformador", "Escolha a barra HV (de):", labels, 0, False
        )
        if not ok:
            return
        src_id = label_to_id[src_label]

        dst_labels = [lb for lb in labels if label_to_id[lb] != src_id]
        dst_label, ok = QInputDialog.getItem(
            self, "Adicionar Transformador", "Escolha a barra LV (para):", dst_labels, 0, False
        )
        if not ok:
            return
        dst_id = label_to_id[dst_label]

        # Cria trafo com valores default (você edita no popup)
        trafo = Transformer.from_z(
            tap_bus_id=src_id,
            z_bus_id=dst_id,
            z=complex(0.0, 0.1),   # X=0.1 pu (didático)
            tap=1.0,
            name=f"TR {src_id}-{dst_id}",
        )

        ctrl.addConnection(trafo)

        # Abre popup de propriedades pra você já configurar ligação/aterramento/bases
        TransformerDialog(trafo).exec()

    def add_generator(self):
        ctrl = SimulatorController.instance()
        buses = ctrl.buses
        if len(buses) < 1:
            return

        labels = [f"{b.number} - {b.name} ({b.type.name})" for b in buses]
        label_to_bus = {labels[i]: buses[i] for i in range(len(buses))}

        chosen, ok = QInputDialog.getItem(
            self, "Adicionar Gerador", "Escolha a barra:", labels, 0, False
        )
        if not ok:
            return

        bus = label_to_bus[chosen]
        GeneratorDialog(bus).exec()
