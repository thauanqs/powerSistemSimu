from typing import *
from PySide6.QtWidgets import (
    QGraphicsRectItem,
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsSimpleTextItem,
)
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMenu
from PySide6.QtGui import QContextMenuEvent
from models.bus import Bus
from models.line import Line
from models.transformer import Transformer

from controllers.simulator_controller import ElementEvent, SimulatorController
from models.bus import Bus, BusType
from models.network_element import NetworkElement
from view.draggable_link_square import DraggableLinkSquare
from view.generator_item import GeneratorItem
from PySide6.QtWidgets import QMessageBox



class BusWidget(QGraphicsRectItem):
    def __init__(self, x: float, y: float, bus: Bus):
        super().__init__(x, y, 50, 10)
        self.bus: Bus = bus
        self.element = bus 
        self._gen_icon = None
        self.setBrush(Qt.GlobalColor.gray)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable, True)

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)

        self.link = DraggableLinkSquare(x + 50 / 2, y, self)

        self.label = QGraphicsSimpleTextItem(self.__label, parent=self)
        self.label.setPos(x, y + 10)
        SimulatorController.instance().listen(self.circuitListener)

        self.label.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

        # garante que o BusWidget recebe clique direito
        self.setAcceptedMouseButtons(Qt.LeftButton | Qt.RightButton)

        # o texto NÃO deve capturar mouse/context menu
        self.label.setAcceptedMouseButtons(Qt.NoButton)

        # o "ponto de conexão" (link) pode ficar só com clique esquerdo (arrastar/conectar)
        self.link.setAcceptedMouseButtons(Qt.LeftButton)

        self.set_has_generator(self.bus.type in (BusType.PV, BusType.SLACK))

    def circuitListener(self, node: NetworkElement, event: ElementEvent):
        if event == ElementEvent.UPDATED and node.id == self.bus.id and isinstance(node, Bus):
            self.bus = node
            self.label.setText(self.__label)
            self.set_has_generator(self.bus.type in (BusType.PV, BusType.SLACK))


    def mouseDoubleClickEvent(self, event):
        from view.generator_dialog import GeneratorDialog
        from PySide6.QtWidgets import QMessageBox

        # Se a barra é PV ou SLACK, tratamos como tendo gerador (teu app já faz isso)
        if self.bus.type in (BusType.PV, BusType.SLACK):
            dlg = GeneratorDialog(self.bus)
            dlg.exec()
            event.accept()
            return

        QMessageBox.information(None, "Barra", "Sem gerador nesta barra (edição da barra ainda não implementada).")
        event.accept()


    def set_has_generator(self, has: bool):
        if has and self._gen_icon is None:
            self._gen_icon = GeneratorItem(self)
            self._gen_icon.setAcceptedMouseButtons(Qt.LeftButton)  # não rouba clique direito
            return

        if (not has) and self._gen_icon is not None:
            # como é filho, basta destruir/remover referência
            self._gen_icon.setParentItem(None)
            self._gen_icon = None


    def itemChange(self, change, value):
        return super().itemChange(change, value)

    def _pick_element_item(self, item):
        """
        Sobe na hierarquia (parentItem) até achar um item que tenha .element.
        Isso resolve clique no label/ícone/link etc.
        """
        cur = item
        while cur is not None and not hasattr(cur, "element"):
            cur = cur.parentItem()
        return cur



    @property
    def __label(self) -> str:
        bus: Bus = self.bus
        label: str = (
            f"{bus.name}"
            + f"\n{bus.type.name}"
            + f"\nv={bus.v:.2f}"
            + f"\no={bus.o:.2f}"
            + f"\np={bus.p:.2f}"
            + f"\nq={bus.q:.2f}"
        )
        return label
