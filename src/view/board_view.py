from typing import Tuple
from PySide6.QtWidgets import (
    QGraphicsView,
    QGraphicsScene,
)
from PySide6.QtGui import QPainter, QMouseEvent, QContextMenuEvent
from PySide6.QtCore import QRectF, Qt, QPoint

from controllers.simulator_controller import ElementEvent, SimulatorController
from models.bus import Bus
from models.line import Line
from models.network_element import NetworkElement
from storage.storage import StorageFacade
from view.bus_widget import BusWidget
from view.link_line_item import LinkLineItem
from view.line_table import LineTable
from PySide6.QtWidgets import QFileDialog, QMenu
import traceback
from PySide6.QtWidgets import QMessageBox

class BoardView(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setBackgroundBrush(Qt.GlobalColor.white)

        # Permite o QGraphicsView receber teclado (Del/Backspace)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Seleção por retângulo (arrastar com botão esquerdo)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)

        # Navegação: Zoom + Pan
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

        # Seleção: deixa o padrão (clicar/selecionar).
        self.setDragMode(QGraphicsView.DragMode.NoDrag)

        self._line_table: LineTable | None = None

        self._is_panning = False
        self._pan_start = QPoint()

        self._zoom = 0
        self._zoom_min = -10
        self._zoom_max = 30

        # self.setSceneRect(0, 0, 600, 400)
        self.simulator_widgets = dict[str, object]()
        simulatorInstance = SimulatorController.instance()
        simulatorInstance.listen(self.circuitListener)

    def drawBackground(self, painter: QPainter, rect: QRectF):
        painter.setPen(Qt.GlobalColor.lightGray)
        super().drawBackground(painter, rect)

        # Define grid spacing
        gridSize = 20

        # Get the visible area of the scene
        left = int(rect.left()) - (int(rect.left()) % gridSize)
        top = int(rect.top()) - (int(rect.top()) % gridSize)

        # Draw vertical lines
        for x in range(left, int(rect.right()), gridSize):
            painter.drawLine(x, rect.top(), x, rect.bottom())

        # Draw horizontal lines
        for y in range(top, int(rect.bottom()), gridSize):
            painter.drawLine(rect.left(), y, rect.right(), y)

    # Listens to the simulator events and updates the board
    def circuitListener(self, element: NetworkElement, event: ElementEvent):
        # Adds node component to the board
        if event is ElementEvent.CREATED and isinstance(element, Bus):
            widget = BusWidget(50, 50, element)
            self.scene().addItem(widget)
            self.simulator_widgets[element.id] = widget
            return

        # Adds line between two components in the board
        # TODO bug: somethimes not creating wire or TL when there is a block selected
        if event is ElementEvent.CREATED and isinstance(element, Line):
            sourceWidget = self.simulator_widgets[element.tap_bus_id].link
            targetWidget = self.simulator_widgets[element.z_bus_id].link
            line = LinkLineItem(sourceWidget, targetWidget, element)
            self.scene().addItem(line)
            self.simulator_widgets[element.id] = line
            return

        if event is ElementEvent.DELETED:
            widget = self.simulator_widgets[element.id]
            self.scene().removeItem(widget)
            del self.simulator_widgets[element.id]
            return

    def import_ieee(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import IEEE File", "", "IEEE Files (*.txt);;All Files (*)"
        )
        if not file_path:
            return
        SimulatorController.instance().clear_state()

        try:
            power_flow = StorageFacade.read_ieee_file(file_path)
            for bus in power_flow.buses.values():
                SimulatorController.instance().addBus(bus)
            for line in power_flow.connections.values():
                SimulatorController.instance().addConnection(line)

        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Erro ao importar JSON", f"{type(e).__name__}: {e}")
            print(f"Error importing JSON file: {e}")
        pass

        SimulatorController.instance().sync_bus_number_pool()


    def import_json(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import JSON File", "", "JSON Files (*.json);;All Files (*)"
        )
        if not file_path:
            return

        SimulatorController.instance().clear_state()
        try:
            buses, lines, positions = StorageFacade.read_json_file(file_path)
            for bus in buses:
                SimulatorController.instance().addBus(bus)
            for line in lines:
                SimulatorController.instance().addConnection(line)

            for index, bus in enumerate(buses):
                bus_widget = self.simulator_widgets[bus.id]
                position = positions[index]
                bus_widget.setPos(position[0], position[1])
        except Exception as e:
            print(f"Error importing JSON file: {e}")
        
        SimulatorController.instance().sync_bus_number_pool()


    def export_json(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export to JSON", "", "JSON Files (*.json);;All Files (*)"
        )
        if not file_path:
            return

        positions = list[Tuple[float, float]]()
        for element in self.simulator_widgets.values():
            if isinstance(element, BusWidget):
                positions.append((element.x(), element.y()))
        StorageFacade.save_json_file(
            file_path,
            buses=SimulatorController.instance().buses,
            lines=SimulatorController.instance().connections,
            positions=positions,
        )

    def wheelEvent(self, event):
        # Zoom suave: roda pra cima => aproxima
        if event.angleDelta().y() == 0:
            return

        zoom_in_factor = 1.25
        zoom_out_factor = 1 / zoom_in_factor

        if event.angleDelta().y() > 0:
            if self._zoom >= self._zoom_max:
                return
            factor = zoom_in_factor
            self._zoom += 1
        else:
            if self._zoom <= self._zoom_min:
                return
            factor = zoom_out_factor
            self._zoom -= 1

        self.scale(factor, factor)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._is_panning = True
            self._pan_start = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._is_panning:
            delta = event.position().toPoint() - self._pan_start
            self._pan_start = event.position().toPoint()

            # move as barras de rolagem (pan real)
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())

            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.MiddleButton and self._is_panning:
            self._is_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def reset_view(self):
        self.resetTransform()
        self._zoom = 0


    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            selected = list(self.scene().selectedItems())
            if not selected:
                return

            ctrl = SimulatorController.instance()

            # 1) Apaga conexões primeiro (evita sobrar linha referenciando barra removida)
            for item in selected:
                if isinstance(item, LinkLineItem):
                    # IMPORTANTe: LinkLineItem precisa expor item.element (Line) ou item.line (Line)
                    line = getattr(item, "element", None) or getattr(item, "line", None)
                    if line is not None:
                        ctrl.deleteConnection(line.id)

            # 2) Depois apaga barras
            for item in selected:
                if isinstance(item, BusWidget):
                    bus = getattr(item, "element", None) or getattr(item, "bus", None)
                    if bus is not None:
                        ctrl.deleteBus(bus.id)

            return

        super().keyPressEvent(event)


    def _pick_element_item(self, item):
        # sobe a hierarquia até achar algo com .element (BusWidget/LinkLineItem)
        cur = item
        while cur is not None and not hasattr(cur, "element"):
            cur = cur.parentItem()
        return cur

    def contextMenuEvent(self, event: QContextMenuEvent):
        item0 = self.itemAt(event.pos())
        if item0 is None:
            return

        item = self._pick_element_item(item0)
        if item is None:
            return

        element = getattr(item, "element", None)

        menu = QMenu(self)
        act_edit = menu.addAction("Editar")
        act_del  = menu.addAction("Excluir")

        act_fault = None
        if isinstance(element, Bus):
            menu.addSeparator()
            act_fault = menu.addAction("Aplicar falta...")

        chosen = menu.exec(event.globalPos())
        if chosen is None:
            return

        ctrl = SimulatorController.instance()

        # APLICAR FALTA
        if chosen == act_fault and isinstance(element, Bus):
            ctrl.chooseAndRunFaultOnBus(element.id)
            return

        # EXCLUIR
        if chosen == act_del:
            if isinstance(item, LinkLineItem):
                line = getattr(item, "element", None) or getattr(item, "line", None)
                if line is not None:
                    ctrl.deleteConnection(line.id)
            elif isinstance(item, BusWidget):
                bus = getattr(item, "element", None) or getattr(item, "bus", None)
                if bus is not None:
                    ctrl.deleteBus(bus.id)
            return

        # EDITAR
        if chosen == act_edit:
            if hasattr(item, "mouseDoubleClickEvent"):
                item.mouseDoubleClickEvent(event)
            return



    def open_line_table(self, select_line_id: str | None = None) -> None:
        if self._line_table is None:
            self._line_table = LineTable()
            self._line_table.setWindowTitle("Line Table")

        self._line_table.show()
        self._line_table.raise_()
        self._line_table.activateWindow()

        if select_line_id and hasattr(self._line_table, "select_line"):
            self._line_table.select_line(select_line_id)


    # TODO handle deletion. must sync with simulator state
    # def keyPressEvent(self, event):
    #     if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
    #         for item in self.scene().selectedItems():
    #             self.scene().removeItem(item)
    #     else:
    #         super().keyPressEvent(event)
