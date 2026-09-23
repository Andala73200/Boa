from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QGraphicsScene


class GridScene(QGraphicsScene):
    GRID_SIZE = 20
    CLASS_COLUMN_WIDTH = 320
    GRAPH_BACKGROUND = QColor("#15171a")
    GRAPH_GRID = QColor("#262a30")
    FUNCTION_BACKGROUND = QColor("#141b24")
    FUNCTION_GRID = QColor("#26384d")
    CLASS_BACKGROUND = QColor("#201723")
    CLASS_GRID = QColor("#432b49")
    CLASS_SEPARATOR = QColor("#8e5a9b")

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._mode = "graph"
        self._class_columns = 1

    def set_grid_size(self, size: int) -> None:
        self.GRID_SIZE = max(10, int(size))
        self.update()

    def set_function_mode(self, enabled: bool) -> None:
        self.set_document_mode("function" if enabled else "graph")

    def set_document_mode(self, mode: str) -> None:
        self._mode = mode if mode in {"graph", "function", "class"} else "graph"
        self.update()

    def set_class_columns(self, count: int) -> None:
        self._class_columns = max(1, int(count))
        self.update()

    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:
        super().drawBackground(painter, rect)
        background, grid = self._colors()
        painter.fillRect(rect, background)
        painter.setPen(QPen(grid, 1))
        left = int(rect.left()) - int(rect.left()) % self.GRID_SIZE
        top = int(rect.top()) - int(rect.top()) % self.GRID_SIZE
        for x in range(left, int(rect.right()), self.GRID_SIZE):
            painter.drawLine(x, rect.top(), x, rect.bottom())
        for y in range(top, int(rect.bottom()), self.GRID_SIZE):
            painter.drawLine(rect.left(), y, rect.right(), y)
        if self._mode == "class":
            self._draw_class_columns(painter, rect)

    def _colors(self) -> tuple[QColor, QColor]:
        if self._mode == "function":
            return self.FUNCTION_BACKGROUND, self.FUNCTION_GRID
        if self._mode == "class":
            return self.CLASS_BACKGROUND, self.CLASS_GRID
        return self.GRAPH_BACKGROUND, self.GRAPH_GRID

    def _draw_class_columns(self, painter: QPainter, rect: QRectF) -> None:
        painter.save()
        painter.setPen(QPen(self.CLASS_SEPARATOR, 2, Qt.PenStyle.DashLine))
        painter.setFont(QFont("", 9, QFont.Weight.Bold))
        origin = 0
        for index in range(self._class_columns + 1):
            x = origin + index * self.CLASS_COLUMN_WIDTH
            painter.drawLine(x, rect.top(), x, rect.bottom())
            if index < self._class_columns:
                painter.drawText(QRectF(x + 8, rect.top() + 8, 110, 20), Qt.AlignmentFlag.AlignLeft, f"Ordre {index + 1}")
        painter.restore()
