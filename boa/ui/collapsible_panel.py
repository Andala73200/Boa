from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStackedLayout,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from boa.i18n import tr


class CollapsiblePanel(QWidget):
    COLLAPSED_SIZE = 28

    def __init__(self, title: str, content: QWidget, area: str) -> None:
        super().__init__()
        self.title = title
        self.content = content
        self.area = area
        self._collapsed = False
        self._saved_size = 220

        self._expanded = self._build_expanded_view()
        self._collapsed_handle = self._build_collapsed_handle()

        self._stack = QStackedLayout(self)
        self._stack.setContentsMargins(0, 0, 0, 0)
        self._stack.addWidget(self._expanded)
        self._stack.addWidget(self._collapsed_handle)
        self._stack.setCurrentWidget(self._expanded)


    def set_title(self, title: str) -> None:
        self.title = title
        if hasattr(self, "_title_label"):
            self._title_label.setText(title)
        if hasattr(self, "_collapse_button"):
            self._collapse_button.setToolTip(tr("panel.collapse", title=title))
        self._collapsed_handle.setToolTip(tr("panel.restore", title=title))

    def is_collapsed(self) -> bool:
        return self._collapsed

    def toggle_collapsed(self) -> None:
        self.set_collapsed(not self._collapsed)

    def set_collapsed(self, collapsed: bool) -> None:
        if collapsed == self._collapsed:
            return
        if collapsed:
            self._save_current_size()
            self._apply_collapsed_size()
            self._stack.setCurrentWidget(self._collapsed_handle)
        else:
            self._release_size_limits()
            self._stack.setCurrentWidget(self._expanded)
        self._collapsed = collapsed
        self._restore_splitter_size()

    def _build_expanded_view(self) -> QWidget:
        wrapper = QWidget()
        wrapper.setObjectName("collapsiblePanel")
        title_bar = QWidget()
        title_bar.setObjectName("collapsiblePanelTitle")

        title_label = QLabel(self.title)
        self._title_label = title_label
        title_label.setObjectName("collapsiblePanelTitleLabel")
        collapse_button = QToolButton()
        self._collapse_button = collapse_button
        collapse_button.setText(self._collapse_arrow())
        collapse_button.setToolTip(tr("panel.collapse", title=self.title))
        collapse_button.clicked.connect(self.toggle_collapsed)

        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(6, 2, 6, 2)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        title_layout.addWidget(collapse_button)

        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(title_bar)
        layout.addWidget(self.content)
        return wrapper

    def _build_collapsed_handle(self) -> QPushButton:
        button = QPushButton(self._restore_arrow())
        button.setObjectName(self._collapsed_object_name())
        button.setToolTip(tr("panel.restore", title=self.title))
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        button.clicked.connect(self.toggle_collapsed)
        return button

    def _collapse_arrow(self) -> str:
        if self.area == "left":
            return "◀"
        if self.area == "right":
            return "▶"
        return "▲"

    def _restore_arrow(self) -> str:
        if self.area == "left":
            return "▶"
        if self.area == "right":
            return "◀"
        return "▼"

    def _collapsed_object_name(self) -> str:
        if self.area == "top":
            return "collapsedTopHandle"
        return "collapsedSideHandle"

    def _save_current_size(self) -> None:
        self._saved_size = self.height() if self.area == "top" else self.width()
        self._saved_size = max(self._saved_size, 160)

    def _apply_collapsed_size(self) -> None:
        if self.area == "top":
            self.setMinimumHeight(self.COLLAPSED_SIZE)
            self.setMaximumHeight(self.COLLAPSED_SIZE)
            return
        self.setMinimumWidth(self.COLLAPSED_SIZE)
        self.setMaximumWidth(self.COLLAPSED_SIZE)

    def _release_size_limits(self) -> None:
        if self.area == "top":
            self.setMinimumHeight(120)
            self.setMaximumHeight(16777215)
            return
        self.setMinimumWidth(150)
        self.setMaximumWidth(16777215)

    def _restore_splitter_size(self) -> None:
        splitter = self.parent()
        if not isinstance(splitter, QSplitter):
            return

        index = splitter.indexOf(self)
        if index < 0:
            return

        sizes = splitter.sizes()
        if not sizes:
            return

        target = self.COLLAPSED_SIZE if self._collapsed else self._saved_size
        target = min(target, max(sum(sizes) - self.COLLAPSED_SIZE, self.COLLAPSED_SIZE))
        delta = target - sizes[index]
        sizes[index] = target

        if len(sizes) > 1 and delta != 0:
            other_index = 1 if index != 1 and len(sizes) > 1 else 0
            sizes[other_index] = max(self.COLLAPSED_SIZE, sizes[other_index] - delta)

        splitter.setSizes(sizes)
