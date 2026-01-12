from typing import *
from PySide6.QtWidgets import (
    QGraphicsLineItem, QGraphicsItem
)
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGraphicsSimpleTextItem, QApplication
from PySide6.QtGui import QPen

from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QDialog
from models.transformer import Transformer
from view.transformer_dialog import TransformerDialog

from controllers.simulator_controller import ElementEvent, SimulatorController
from models.line import Line
from models.network_element import NetworkElement


class LinkLineItem(QGraphicsLineItem):
    def __init__(
        self,
        sourceNodeDraggableLink,
        targetNodeDraggableLink,
        line: Line,
    ):
        super().__init__()
        self.sourceNodeDraggableLink = sourceNodeDraggableLink
        self.targetNodeDraggableLink = targetNodeDraggableLink
        self.setPen(QPen(Qt.blue, 1))
        self.setZValue(0)
        self.__line: Line = line
        self.line_model = line   
        self.element = line       


        self.nameLabel = None
        self.center = None

        self.nameLabel = QGraphicsSimpleTextItem(self.__label)
        self.nameLabel.setBrush(Qt.red)
        self.nameLabel.setParentItem(self)
        SimulatorController.instance().listen(self.circuitListener)

    def updatePosition(self):
        p1 = self.sourceNodeDraggableLink.sceneBoundingRect().center()
        p2 = self.targetNodeDraggableLink.sceneBoundingRect().center()
        self.setLine(p1.x(), p1.y(), p2.x(), p2.y())
        if self.nameLabel:
            self.center = p1 + (p2 - p1) / 2
            self.nameLabel.setPos(self.center.x(), self.center.y())

    def paint(self, painter, option, widget):
        self.updatePosition()
        super().paint(painter, option, widget)

        # Se for transformador: desenha duas "bobinas" no meio
        if isinstance(self.__line, Transformer):
            ln = QGraphicsLineItem.line(self)
            mx = (ln.x1() + ln.x2()) / 2.0
            my = (ln.y1() + ln.y2()) / 2.0

            r = 6  # raio visual
            # duas elipses lado a lado
            painter.drawEllipse(mx - 2*r, my - r, 2*r, 2*r)
            painter.drawEllipse(mx,       my - r, 2*r, 2*r)


    def circuitListener(self, element: NetworkElement, event: ElementEvent):
        if (
            event == ElementEvent.UPDATED
            and self.__line.id == element.id
            and isinstance(element, Line)
        ):
            self.__line = element
            self.line_model = element
            self.element = element
            self.nameLabel.setText(self.__label)

    def mouseDoubleClickEvent(self, event):
        if isinstance(self.__line, Transformer):
            dlg = TransformerDialog(self.__line)
            dlg.exec()
            event.accept()
            return

        # Linha normal: abre a LineTable pela view dona da scene (sem imports)
        views = self.scene().views() if self.scene() is not None else []
        if views:
            view0 = views[0]
            if hasattr(view0, "open_line_table"):
                view0.open_line_table(select_line_id=self.__line.id)  # aqui passa o id
                event.accept()
                return

        event.accept()

    @property
    def __label(self) -> str:
        label: str = f"y={self.__line.y:.2f}"
        if self.__line.bc != 0:
            label += f" \nbc=j{self.__line.bc:.2f}"
        if self.__line.tap != 1:
            label += f" \ntap={self.__line.tap:.2f}:1"
        if isinstance(self.__line, Transformer):
            label = "TR\n" + label
            label += f"\n{self.__line.meta.conn_hv}-{self.__line.meta.conn_lv}"
        return label
