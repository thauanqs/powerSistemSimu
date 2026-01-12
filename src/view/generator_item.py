from __future__ import annotations
from PySide6.QtWidgets import QGraphicsItem
from PySide6.QtCore import QRectF, QPointF, Qt
from PySide6.QtGui import QPainter, QPen, QPainterPath


class GeneratorItem(QGraphicsItem):
    """
    Ícone de gerador: fica como FILHO (parent) da barra.
    Assim ele acompanha automaticamente a barra e não precisa ser adicionado na scene.
    """

    def __init__(self, parent_item: QGraphicsItem):
        super().__init__(parent_item)  # <-- agora é filho da barra

        self._size = 26.0
        self._offset = QPointF(-4, -30)  # ajuste fino: acima da barra

        self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.setZValue(20)

        # posição relativa ao pai
        self.setPos(self._offset)

    def boundingRect(self) -> QRectF:
        s = self._size
        return QRectF(0, 0, s, s + 25)

    def paint(self, painter: QPainter, option, widget=None):
        s = self._size
        parent = self.parentItem()
        parent = self.parentItem()
        if parent is not None and hasattr(parent, "rect"):
            xg = s / 2.0
            yg = s

            pr = parent.rect()
            target_in_parent = pr.topLeft() + QPointF(pr.width() / 2.0, 0.0)
            target_local = self.mapFromParent(target_in_parent)

            pen_old = painter.pen()
            pen = QPen(pen_old)
            pen.setWidth(2)
            pen.setColor(Qt.GlobalColor.black)
            painter.setPen(pen)

            painter.drawLine(xg, yg, target_local.x(), target_local.y())

            painter.setPen(pen_old)


        painter.setPen(QPen())
        painter.drawEllipse(0, 0, s, s)
        painter.drawLine(s/2, s, s/2, s + 6)

        # senoide dentro
        path = QPainterPath()
        margin = 4.0
        x0 = margin
        x1 = s - margin
        ymid = s / 2.0
        amp = (s - 2 * margin) * 0.30

        path.moveTo(x0, ymid)
        xm = (x0 + x1) / 2.0
        path.cubicTo(x0 + (xm - x0) * 0.5, ymid - amp, x0 + (xm - x0) * 0.5, ymid + amp, xm, ymid)
        path.cubicTo(xm + (x1 - xm) * 0.5, ymid - amp, xm + (x1 - xm) * 0.5, ymid + amp, x1, ymid)

        painter.drawPath(path)
