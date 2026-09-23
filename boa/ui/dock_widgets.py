from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDockWidget,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


class CollapsedHandle(QWidget):
    clicked = Signal()

    def __init__(self, title: str, direction: str, arrow: str) -> None:
        super().__init__()
        self.setObjectName("collapsedDockHandle")
        self.button = QPushButton(arrow)
        self.button.setObjectName("collapsedDockButton")
        self.button.setToolTip(f"Restaurer {title}")
        self.button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.button.clicked.connect(self.clicked.emit)

        if direction == "vertical":
            layout = QHBoxLayout(self)
        else:
            layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.button)


class DockTitleBar(QWidget):
    def __init__(self, title: str, dock: "BoaDock", collapsible: bool = False) -> None:
        super().__init__(dock)
        self.setObjectName("dockTitleBar")
        self.dock = dock
        self.title_label = QLabel(title)
        self.title_label.setObjectName("dockTitleLabel")

        self.collapse_button = QToolButton()
        self.collapse_button.setText("−")
        self.collapse_button.setToolTip("Réduire le volet")
        self.collapse_button.setVisible(collapsible)
        self.collapse_button.clicked.connect(self.dock.toggle_collapsed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 4, 2)
        layout.setSpacing(4)
        layout.addWidget(self.title_label)
        layout.addStretch()
        layout.addWidget(self.collapse_button)

    def set_collapsed(self, collapsed: bool) -> None:
        self.collapse_button.setText("+" if collapsed else "−")


class BoaDock(QDockWidget):
    COLLAPSED_WIDTH = 26
    COLLAPSED_HEIGHT = 28

    def __init__(
        self,
        title: str,
        parent=None,
        collapsible: bool = False,
        collapse_direction: str = "horizontal",
        collapsed_arrow: str = "▶",
    ) -> None:
        super().__init__(title, parent)
        self._content_widget: QWidget | None = None
        self._collapsible = collapsible
        self._collapse_direction = collapse_direction
        self._collapsed = False
        self._saved_width = 260
        self._saved_height = 170
        self._normal_min_width = 120
        self._normal_min_height = 90

        self.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )

        self.title_bar = DockTitleBar(title, self, collapsible)
        self._empty_title_bar = QWidget()
        self._empty_title_bar.setFixedSize(0, 0)
        self.setTitleBarWidget(self.title_bar)

        self._stack = QStackedWidget()
        self._collapsed_handle = CollapsedHandle(title, collapse_direction, collapsed_arrow)
        self._collapsed_handle.clicked.connect(self.toggle_collapsed)
        self._stack.addWidget(self._collapsed_handle)
        super().setWidget(self._stack)

    def setWidget(self, widget: QWidget) -> None:  # noqa: N802 - Qt API name
        if self._content_widget is not None:
            self._stack.removeWidget(self._content_widget)
            self._content_widget.setParent(None)
        self._content_widget = widget
        self._stack.insertWidget(0, widget)
        self._stack.setCurrentWidget(widget)

    def is_collapsed(self) -> bool:
        return self._collapsed

    def toggle_collapsed(self) -> None:
        self.set_collapsed(not self._collapsed)

    def set_collapsed(self, collapsed: bool) -> None:
        if not self._collapsible or self._content_widget is None:
            return
        if collapsed == self._collapsed:
            return

        self._collapsed = collapsed
        self.title_bar.set_collapsed(collapsed)

        if self._collapse_direction == "vertical":
            self._set_vertical_collapsed(collapsed)
            return
        self._set_horizontal_collapsed(collapsed)

    def _set_horizontal_collapsed(self, collapsed: bool) -> None:
        if collapsed:
            self._saved_width = max(self.width(), self._normal_min_width)
            self.setTitleBarWidget(self._empty_title_bar)
            self._stack.setCurrentWidget(self._collapsed_handle)
            self.setMinimumWidth(self.COLLAPSED_WIDTH)
            self.setMaximumWidth(self.COLLAPSED_WIDTH)
            return

        self.setMinimumWidth(self._normal_min_width)
        self.setMaximumWidth(16777215)
        self.setTitleBarWidget(self.title_bar)
        self._stack.setCurrentWidget(self._content_widget)
        self.resize(self._saved_width, self.height())

    def _set_vertical_collapsed(self, collapsed: bool) -> None:
        if collapsed:
            self._saved_height = max(self.height(), self._normal_min_height)
            self.setTitleBarWidget(self._empty_title_bar)
            self._stack.setCurrentWidget(self._collapsed_handle)
            self.setMinimumHeight(self.COLLAPSED_HEIGHT)
            self.setMaximumHeight(self.COLLAPSED_HEIGHT)
            return

        self.setMinimumHeight(self._normal_min_height)
        self.setMaximumHeight(16777215)
        self.setTitleBarWidget(self.title_bar)
        self._stack.setCurrentWidget(self._content_widget)
        self.resize(self.width(), self._saved_height)
