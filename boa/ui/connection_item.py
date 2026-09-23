from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainterPath, QPainterPathStroker, QPen
from PySide6.QtWidgets import QGraphicsPathItem, QToolTip

from boa.i18n import tr
from boa.ui.connection_rules import STATUS_CONFLICT, STATUS_ERROR, STATUS_FLOW, STATUS_NORMAL, STATUS_WARNING


_STATUS_PENS = {
    STATUS_NORMAL: ("#42a5f5", Qt.PenStyle.SolidLine),
    STATUS_FLOW: ("#26c6da", Qt.PenStyle.SolidLine),
    STATUS_WARNING: ("#fdd835", Qt.PenStyle.SolidLine),
    STATUS_ERROR: ("#ef5350", Qt.PenStyle.SolidLine),
    STATUS_CONFLICT: ("#ef5350", Qt.PenStyle.DashLine),
}


class ConnectionItem(QGraphicsPathItem):
    HIT_WIDTH = 24

    def __init__(self, source_block, target_block, source_port: str = "", target_port: str = "") -> None:
        super().__init__()
        self.source_block = source_block
        self.target_block = target_block
        self.source_port = source_port or source_block.default_output_port_key()
        self.target_port = target_port or target_block.default_input_port_key()
        self.status = STATUS_NORMAL
        self.setFlags(QGraphicsPathItem.GraphicsItemFlag.ItemIsSelectable)
        self.setAcceptHoverEvents(True)
        self.setZValue(-10)
        self.source_block.add_connection(self)
        self.target_block.add_connection(self)
        self.update_path()
        self._apply_pen()

    def update_path(self) -> None:
        start = self.source_block.port_scene_pos(self.source_port)
        end = self.target_block.port_scene_pos(self.target_port)
        self.setPath(_connection_path(start, end))

    def set_status(self, status: str) -> None:
        self.status = status if status in _STATUS_PENS else STATUS_ERROR
        self._apply_pen()

    def refresh_tooltip(self) -> None:
        source = self.source_block.port_definition(self.source_port)
        target = self.target_block.port_definition(self.target_port)
        source_name = (source.label or source.key) if source else self.source_port
        target_name = (target.label or target.key) if target else self.target_port
        source_type = (source.value_type or "any") if source else "?"
        target_type = (target.value_type or "any") if target else "?"
        status_text = tr(f"tooltip.connection.status.{self.status}")
        self.setToolTip(tr(
            "tooltip.connection.details",
            source=f"{self.source_block.title}.{source_name}",
            target=f"{self.target_block.title}.{target_name}",
            source_type=source_type,
            target_type=target_type,
            status=status_text,
        ))

    def detach(self) -> None:
        self.source_block.remove_connection(self)
        self.target_block.remove_connection(self)

    def itemChange(self, change, value):
        if change == QGraphicsPathItem.GraphicsItemChange.ItemSelectedHasChanged:
            self._apply_pen(bool(value))
        return super().itemChange(change, value)

    def shape(self):
        stroker = QPainterPathStroker()
        stroker.setWidth(self.HIT_WIDTH)
        stroker.setCapStyle(Qt.PenCapStyle.RoundCap)
        stroker.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        return stroker.createStroke(self.path())

    def boundingRect(self):
        margin = self.HIT_WIDTH / 2
        return self.path().controlPointRect().adjusted(-margin, -margin, margin, margin)

    def hoverEnterEvent(self, event) -> None:
        QToolTip.showText(event.screenPos(), self.toolTip())
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event) -> None:
        QToolTip.hideText()
        super().hoverLeaveEvent(event)

    def _apply_pen(self, selected: bool | None = None) -> None:
        if selected is None:
            selected = self.isSelected()
        color, style = ("#00c853", Qt.PenStyle.SolidLine) if selected else _STATUS_PENS.get(self.status, _STATUS_PENS[STATUS_ERROR])
        self.setPen(QPen(QColor(color), 3 if selected else 2, style))
        self.refresh_tooltip()


class TemporaryConnectionItem(QGraphicsPathItem):
    def __init__(self, start: QPointF) -> None:
        super().__init__()
        self.start = start
        self.status = STATUS_NORMAL
        self.setZValue(-9)
        self.update_path(start)
        self._apply_pen()

    def update_path(self, end: QPointF) -> None:
        self.setPath(_connection_path(self.start, end))

    def set_status(self, status: str) -> None:
        self.status = status if status in _STATUS_PENS else STATUS_ERROR
        self._apply_pen()

    def _apply_pen(self) -> None:
        color, style = _STATUS_PENS.get(self.status, _STATUS_PENS[STATUS_ERROR])
        self.setPen(QPen(QColor(color), 2, style))


def _connection_path(start: QPointF, end: QPointF) -> QPainterPath:
    path = QPainterPath(start)
    dx = max(abs(end.x() - start.x()) * 0.5, 60)
    path.cubicTo(QPointF(start.x() + dx, start.y()), QPointF(end.x() - dx, end.y()), end)
    return path
