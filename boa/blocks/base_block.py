from dataclasses import dataclass

from textwrap import fill

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QGraphicsObject, QStyleOptionGraphicsItem, QToolTip, QWidget

from boa.i18n import tr
from boa.ui.block_comment_dialog import tooltip_comment


@dataclass(slots=True)
class PortDefinition:
    key: str
    label: str
    kind: str
    value_type: str
    side: str
    y: float
    group: str = ""


class BlockItem(QGraphicsObject):
    changed = Signal()
    GRID_SIZE = 20
    SNAP_ENABLED = True
    WIDTH = 170
    HEIGHT = 76
    PORT_DRAW_RADIUS = 5
    PORT_HIT_RADIUS = 18

    def __init__(
        self,
        title: str,
        subtitle: str = "",
        color: QColor | None = None,
        ports: list[PortDefinition] | None = None,
        width: int = 170,
        height: int = 76,
    ) -> None:
        super().__init__()
        self.title = title
        self.subtitle = subtitle
        self.color = color or QColor("#3d5afe")
        self.uid = ""
        self.block_key = title
        self.connections = set()
        self.modifiable = False
        self.comment = ""
        self._body_tooltip = ""
        self._hovered_port_key = ""
        self.WIDTH = width
        self.HEIGHT = height
        self.ports = ports if ports is not None else [
            PortDefinition("in", "", "input", "flow", "left", self.HEIGHT / 2),
            PortDefinition("out", "", "output", "flow", "right", self.HEIGHT / 2),
        ]
        self.setFlags(
            QGraphicsObject.GraphicsItemFlag.ItemIsMovable
            | QGraphicsObject.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsObject.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)

    def boundingRect(self) -> QRectF:
        hit = self.PORT_HIT_RADIUS
        return QRectF(-hit, -hit, self.WIDTH + hit * 2, self.HEIGHT + hit * 2)

    def shape(self) -> QPainterPath:
        path = QPainterPath()
        path.addRoundedRect(self._body_rect(), 9, 9)
        for port in self.ports:
            path.addEllipse(self._port_rect(port, self.PORT_HIT_RADIUS))
        return path

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget | None = None) -> None:
        rect = self._body_rect()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#ffffff" if self.isSelected() else "#d7d7d7"), 2 if self.isSelected() else 1))
        painter.setBrush(self.color)
        painter.drawRoundedRect(rect, 9, 9)
        self._paint_title(painter, rect)
        self._paint_ports(painter)
        self._paint_port_groups(painter)
        self._paint_loop_number(painter, rect)
        self._paint_modifiable_icon(painter, rect)

    def input_port_pos(self) -> QPointF:
        return self.port_pos(self.default_input_port_key())

    def output_port_pos(self) -> QPointF:
        return self.port_pos(self.default_output_port_key())

    def input_port_scene_pos(self) -> QPointF:
        return self.port_scene_pos(self.default_input_port_key())

    def output_port_scene_pos(self) -> QPointF:
        return self.port_scene_pos(self.default_output_port_key())

    def port_pos(self, port_key: str) -> QPointF:
        port = self.port_definition(port_key)
        if port is None:
            if not self.ports:
                return QPointF(self.WIDTH / 2, self.HEIGHT / 2)
            port = self.ports[0]
        if port.side == "top":
            return QPointF(port.y if port.y else self.WIDTH / 2, 0)
        if port.side == "bottom":
            return QPointF(port.y if port.y else self.WIDTH / 2, self.HEIGHT)
        x = 0 if port.side == "left" else self.WIDTH
        return QPointF(x, port.y)

    def port_scene_pos(self, port_key: str) -> QPointF:
        return self.mapToScene(self.port_pos(port_key))

    def port_definition(self, port_key: str) -> PortDefinition | None:
        return next((port for port in self.ports if port.key == port_key), None)

    def default_input_port_key(self) -> str:
        return self._default_port_key("input")

    def default_output_port_key(self) -> str:
        return self._default_port_key("output")

    def port_at_scene_pos(self, scene_pos: QPointF, kind: str | None = None) -> str | None:
        local_pos = self.mapFromScene(scene_pos)
        for port in self.ports:
            if kind and port.kind != kind:
                continue
            if _distance(local_pos, self.port_pos(port.key)) <= self.PORT_HIT_RADIUS:
                return port.key
        return None

    def add_connection(self, connection) -> None:
        self.connections.add(connection)

    def remove_connection(self, connection) -> None:
        self.connections.discard(connection)

    def set_modifiable(self, modifiable: bool) -> None:
        self.modifiable = bool(modifiable)
        self.refresh_tooltip()
        self.update()

    def refresh_tooltip(self) -> None:
        key = f"block.{self.block_key}.description"
        description = tr(key)
        if description == key:
            description = tr("tooltip.block.generic", name=self.title)
        lines = [description]
        if self.block_key == "print":
            text = str(getattr(self, "print_text", "") or tr("tooltip.value.empty"))
            wrapped = "\n".join(fill(line, width=68) if line else "" for line in text.splitlines() or [text])
            lines.append(tr("tooltip.print.text", text=wrapped))
            if bool(getattr(self, "print_dynamic", False)):
                lines.append(tr("tooltip.print.dynamic"))
        if self.comment:
            lines.append(tooltip_comment(self.comment))
        if self.modifiable:
            lines.append(tr("tooltip.block.modifiable"))
        self._body_tooltip = "\n".join(line for line in lines if line)
        if not self._hovered_port_key:
            self.setToolTip(self._body_tooltip)

    def hoverEnterEvent(self, event) -> None:
        self._update_hover_tooltip(event)
        super().hoverEnterEvent(event)

    def hoverMoveEvent(self, event) -> None:
        self._update_hover_tooltip(event)
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event) -> None:
        if self._hovered_port_key:
            QToolTip.hideText()
        self._hovered_port_key = ""
        self.setToolTip(self._body_tooltip)
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event) -> None:
        self._drag_start_pos = self.pos()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        old_pos = getattr(self, "_drag_start_pos", self.pos())
        super().mouseReleaseEvent(event)
        self._snap_to_grid()
        self._update_connections()
        if self.pos() != old_pos:
            self.changed.emit()

    def itemChange(self, change, value):
        result = super().itemChange(change, value)
        if change == QGraphicsObject.GraphicsItemChange.ItemPositionHasChanged:
            self._update_connections()
        return result

    def _default_port_key(self, kind: str) -> str:
        for port in self.ports:
            if port.kind == kind:
                return port.key
        return self.ports[0].key if self.ports else ""

    def _body_rect(self) -> QRectF:
        return QRectF(0, 0, self.WIDTH, self.HEIGHT)

    def _port_rect(self, port: PortDefinition, radius: float) -> QRectF:
        center = self.port_pos(port.key)
        return QRectF(center.x() - radius, center.y() - radius, radius * 2, radius * 2)

    def _paint_title(self, painter: QPainter, rect: QRectF) -> None:
        painter.setPen(QColor("#ffffff"))
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(10)
        painter.setFont(title_font)
        right_margin = -32 if self.modifiable else -10
        painter.drawText(
            rect.adjusted(10, 6, right_margin, -8),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            self.title,
        )
        if self.subtitle:
            body_font = QFont()
            body_font.setPointSize(10)
            painter.setFont(body_font)
            painter.drawText(
                rect.adjusted(10, 22, -10, -6),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
                self.subtitle,
            )

    def _paint_modifiable_icon(self, painter: QPainter, rect: QRectF) -> None:
        if not self.modifiable:
            return
        center = QPointF(rect.right() - 16, rect.top() + 14)
        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 75))
        painter.drawEllipse(center, 9, 9)
        painter.translate(center)
        painter.rotate(45)
        painter.setPen(QPen(QColor("#ffffff"), 1))
        painter.setBrush(QColor("#ffffff"))
        painter.drawRoundedRect(QRectF(-2, -6, 4, 10), 1, 1)
        painter.drawLine(QPointF(-2, 5), QPointF(0, 8))
        painter.drawLine(QPointF(2, 5), QPointF(0, 8))
        painter.restore()


    def _paint_loop_number(self, painter: QPainter, rect: QRectF) -> None:
        number = getattr(self, "loop_instance_number", 0)
        if self.block_key not in {"for", "while"} or not number:
            return
        font = QFont()
        font.setPointSize(8)
        painter.setFont(font)
        painter.setPen(QColor("#d7d7d7"))
        painter.drawText(rect.adjusted(0, 0, -8, -4), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom, f"#{number}")

    def _paint_ports(self, painter: QPainter) -> None:
        painter.setFont(QFont("", 8))
        for port in self.ports:
            center = self.port_pos(port.key)
            painter.setBrush(QColor("#15171a"))
            painter.setPen(QPen(QColor("#f1f1f1"), 1))
            painter.drawEllipse(center, self.PORT_DRAW_RADIUS, self.PORT_DRAW_RADIUS)
            if not port.label:
                continue
            painter.setPen(QColor("#ffffff"))
            if port.side == "left":
                label_rect = QRectF(12, center.y() - 9, self.WIDTH / 2, 18)
                align = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            elif port.side == "right":
                label_rect = QRectF(self.WIDTH / 2 - 8, center.y() - 9, self.WIDTH / 2 - 8, 18)
                align = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            else:
                label_rect = QRectF(center.x() - 42, 8 if port.side == "top" else self.HEIGHT - 24, 84, 18)
                align = Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter
            painter.drawText(label_rect, align, port.label)

    def _paint_port_groups(self, painter: QPainter) -> None:
        groups: dict[str, list[PortDefinition]] = {}
        for port in self.ports:
            if port.group and port.side == "left":
                groups.setdefault(port.group, []).append(port)
        painter.save()
        painter.setPen(QPen(QColor("#d7d7d7"), 1))
        for label, items in groups.items():
            ordered = sorted(items, key=lambda item: item.y)
            if not ordered:
                continue
            top = ordered[0].y - 10
            bottom = ordered[-1].y + 10
            x = 8
            path = QPainterPath(QPointF(x + 5, top))
            path.cubicTo(QPointF(x, top), QPointF(x, top + 4), QPointF(x, top + 8))
            path.lineTo(QPointF(x, (top + bottom) / 2 - 4))
            path.cubicTo(QPointF(x, (top + bottom) / 2), QPointF(x + 5, (top + bottom) / 2), QPointF(x + 5, (top + bottom) / 2 + 4))
            path.cubicTo(QPointF(x, (top + bottom) / 2 + 4), QPointF(x, (top + bottom) / 2 + 8), QPointF(x, bottom - 8))
            path.cubicTo(QPointF(x, bottom - 4), QPointF(x, bottom), QPointF(x + 5, bottom))
            painter.drawPath(path)
            painter.drawText(QRectF(12, top - 16, 80, 14), Qt.AlignmentFlag.AlignLeft, label)
        painter.restore()

    def _update_hover_tooltip(self, event) -> None:
        port_key = self.port_at_scene_pos(event.scenePos()) or ""
        if port_key == self._hovered_port_key:
            return
        was_on_port = bool(self._hovered_port_key)
        self._hovered_port_key = port_key
        port = self.port_definition(port_key) if port_key else None
        if port is not None:
            direction = tr("tooltip.port.input" if port.kind == "input" else "tooltip.port.output")
            name = port.label or port.key
            tooltip = tr("tooltip.port.details", direction=direction, name=name, value_type=port.value_type or "any")
            self.setToolTip(tooltip)
            QToolTip.showText(event.screenPos(), tooltip)
        else:
            self.setToolTip(self._body_tooltip)
            if was_on_port:
                QToolTip.hideText()

    def _update_connections(self) -> None:
        for connection in list(self.connections):
            connection.update_path()

    def _snap_to_grid(self) -> None:
        if not self.SNAP_ENABLED:
            return
        pos = self.pos()
        x = round(pos.x() / self.GRID_SIZE) * self.GRID_SIZE
        y = round(pos.y() / self.GRID_SIZE) * self.GRID_SIZE
        self.setPos(x, y)


def _distance(a: QPointF, b: QPointF) -> float:
    dx = a.x() - b.x()
    dy = a.y() - b.y()
    return (dx * dx + dy * dy) ** 0.5
