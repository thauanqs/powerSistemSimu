from typing import *
from PySide6.QtWidgets import (
    QGraphicsRectItem,
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsSimpleTextItem,
)
from PySide6.QtCore import Qt

from controllers.simulator_controller import ElementEvent, SimulatorController
from models.bus import Bus
from models.network_element import NetworkElement
from view.draggable_link_square import DraggableLinkSquare


class BusWidget(QGraphicsRectItem):
    def __init__(self, x: float, y: float, bus: Bus):
        super().__init__(x, y, 50, 10)
        self.bus: Bus = bus
        self.setBrush(Qt.GlobalColor.gray)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable, True)

        self.link = DraggableLinkSquare(x + 50 / 2, y, self)

        self.label = QGraphicsSimpleTextItem(self.__label, parent=self)
        self.label.setPos(x, y + 10)
        SimulatorController.instance().listen(self.circuitListener)

    def circuitListener(self, node: NetworkElement, event: ElementEvent):
        if event == ElementEvent.UPDATED and node.id == self.bus.id and isinstance(node, Bus):
            self.bus = node
            self.label.setText(self.__label)

    def mouseDoubleClickEvent(self, event):
        # Duplo clique na barra -> estudo de falta trifásica nesta barra
        SimulatorController.instance().runThreePhaseFaultOnBus(self.bus.id)
        super().mouseDoubleClickEvent(event)


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
