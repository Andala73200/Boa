from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QGraphicsSceneMouseEvent, QStyleOptionGraphicsItem, QWidget

from boa.blocks.base_block import BlockItem, PortDefinition
from boa.blocks.python_native_blocks import create_return_block as _create_native_return_block


MARKER_COLORS = {
    "def_marker": QColor("#1565c0"),
    "class_marker": QColor("#6a1b9a"),
    "return": QColor("#6a1b9a"),
}
SOCKET_COLOR = QColor("#15171a")
SOCKET_OUTLINE = QColor("#e5e5e5")
SOCKET_RADIUS = 7


class DefinitionMarkerBlockItem(BlockItem):
    def __init__(self, key: str, name: str, target_id: str, captures: list[str] | None = None) -> None:
        capture_names = [str(item).strip() for item in (captures or []) if str(item).strip()]
        ports = [
            PortDefinition("start", "start", "input", "flow", "left", 26),
            PortDefinition("done", "done", "output", "flow", "right", 26),
            PortDefinition("decorator", "", "input", "decorator", "top", 95),
        ]
        for index, capture in enumerate(capture_names):
            ports.append(PortDefinition(f"capture_{index + 1}", capture, "input", "any", "left", 56 + index * 24))
        height = max(68, 70 + max(0, len(capture_names) - 1) * 24)
        title = "DEF" if key == "def_marker" else "CLASSE"
        super().__init__(title, name, MARKER_COLORS[key], ports, 190, height)
        self.block_key = key
        self.definition_id = target_id
        self.definition_captures = capture_names
        self.decorator_accepts = True
        self.modifiable = True

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget | None = None) -> None:
        rect = self._body_rect()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#ffffff" if self.isSelected() else "#d7d7d7"), 2 if self.isSelected() else 1))
        painter.setBrush(self.color)
        painter.drawPath(_notched_body_path(self.WIDTH, self.HEIGHT, 9, self.WIDTH / 2, SOCKET_RADIUS))
        self._paint_title(painter, rect)
        self._paint_ports(painter)
        self._paint_port_groups(painter)
        self._paint_modifiable_icon(painter, rect)

    def _paint_ports(self, painter: QPainter) -> None:
        painter.setFont(QFont("", 8))
        for port in self.ports:
            if port.key == "decorator":
                continue
            center = self.port_pos(port.key)
            painter.setBrush(SOCKET_COLOR)
            painter.setPen(QPen(QColor("#f1f1f1"), 1))
            painter.drawEllipse(center, self.PORT_DRAW_RADIUS, self.PORT_DRAW_RADIUS)
            if not port.label:
                continue
            painter.setPen(QColor("#ffffff"))
            if port.side == "left":
                label_rect = QRectF(12, center.y() - 9, self.WIDTH / 2, 18)
                align = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            else:
                label_rect = QRectF(self.WIDTH / 2 - 8, center.y() - 9, self.WIDTH / 2 - 8, 18)
                align = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            painter.drawText(label_rect, align, port.label)


def create_definition_marker(
    key: str,
    name: str = "définition",
    target_id: str = "",
    captures: list[str] | None = None,
) -> BlockItem:
    return DefinitionMarkerBlockItem(key, name, target_id, captures)


def create_return_block(values: list[str] | None = None, key: str = "return", protected: bool = False) -> BlockItem:
    return _create_native_return_block(values, key, protected)


class DecoratorBlockItem(BlockItem):
    WIDTH = 190
    HEIGHT = 28

    def __init__(self, expression: str = "decorateur") -> None:
        super().__init__("", "", QColor("#263238"), [], self.WIDTH, self.HEIGHT)
        self.block_key = "decorator"
        self.decorator_expression = expression.lstrip("@").strip() or "decorateur"
        self.decorator_target = ""
        self.decorator_order = 0
        self.decorator_attached = False
        self.stack_collapsed = False
        self.stack_count = 1
        self.toggle_stack_callback = lambda _block: None
        self.modifiable = True
        self.refresh_tooltip()

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget | None = None) -> None:
        rect = self._body_rect()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#ffffff" if self.isSelected() else "#9ea7ad"), 2 if self.isSelected() else 1))
        painter.setBrush(self.color)
        painter.drawPath(_notched_body_path(self.WIDTH, self.HEIGHT, 7, self.WIDTH / 2, SOCKET_RADIUS))
        _paint_male_socket(painter, self.WIDTH / 2, self.HEIGHT, self.color)

        painter.setFont(QFont("", 9, QFont.Weight.Bold))
        painter.setPen(QColor("#43a047" if self.decorator_attached else "#e53935"))
        painter.drawText(QRectF(10, 0, 20, self.HEIGHT), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "@")
        painter.setPen(QColor("#ffffff"))
        text = f"Décorateurs ({self.stack_count})" if self.stack_collapsed and self.stack_count > 1 else self.decorator_expression
        painter.drawText(QRectF(29, 0, self.WIDTH - 58, self.HEIGHT), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)
        if self.stack_count > 1:
            painter.setFont(QFont("", 8))
            painter.drawText(QRectF(self.WIDTH - 26, 0, 18, self.HEIGHT), Qt.AlignmentFlag.AlignCenter, "▶" if self.stack_collapsed else "▼")
        self._paint_modifiable_icon(painter, rect)

    def refresh_tooltip(self) -> None:
        if self.decorator_attached:
            self._body_tooltip = f"Décorateur attaché : @{self.decorator_expression}"
        else:
            self._body_tooltip = "Décorateur non associé — il ne sera pas généré dans le code Python."
        self.setToolTip(self._body_tooltip)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        local = event.pos()
        if self.stack_count > 1 and local.x() >= self.WIDTH - 32:
            self.stack_collapsed = not self.stack_collapsed
            self.toggle_stack_callback(self)
            self.changed.emit()
            self.update()
            event.accept()
            return
        super().mousePressEvent(event)

    def set_attached(self, target: str, order: int) -> None:
        self.decorator_target = str(target)
        self.decorator_order = int(order)
        self.decorator_attached = bool(target)
        self.refresh_tooltip()
        self.update()


def _notched_body_path(width: float, height: float, radius: float, socket_x: float, socket_radius: float) -> QPainterPath:
    path = QPainterPath(QPointF(radius, 0))
    path.lineTo(socket_x - socket_radius, 0)
    path.cubicTo(
        QPointF(socket_x - socket_radius, socket_radius * 0.65),
        QPointF(socket_x - socket_radius * 0.65, socket_radius),
        QPointF(socket_x, socket_radius),
    )
    path.cubicTo(
        QPointF(socket_x + socket_radius * 0.65, socket_radius),
        QPointF(socket_x + socket_radius, socket_radius * 0.65),
        QPointF(socket_x + socket_radius, 0),
    )
    path.lineTo(width - radius, 0)
    path.quadTo(QPointF(width, 0), QPointF(width, radius))
    path.lineTo(width, height - radius)
    path.quadTo(QPointF(width, height), QPointF(width - radius, height))
    path.lineTo(radius, height)
    path.quadTo(QPointF(0, height), QPointF(0, height - radius))
    path.lineTo(0, radius)
    path.quadTo(QPointF(0, 0), QPointF(radius, 0))
    path.closeSubpath()
    return path


def _paint_male_socket(painter: QPainter, x: float, y: float, color: QColor) -> None:
    painter.save()
    painter.setPen(QPen(SOCKET_OUTLINE, 1))
    painter.setBrush(color)
    painter.drawEllipse(QPointF(x, y), SOCKET_RADIUS - 1, SOCKET_RADIUS - 1)
    painter.restore()


def create_decorator_block(expression: str = "decorateur") -> DecoratorBlockItem:
    return DecoratorBlockItem(expression)
