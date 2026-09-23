import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from boa.ui.main_window import MainWindow
from boa.ui.python_index_notice import show_python_index_notice
from boa.ui.help_dialogs import show_welcome_if_needed


DARK_STYLE = """
QMainWindow, QWidget {
    background-color: #202124;
    color: #f1f1f1;
    font-size: 12px;
}
#collapsiblePanel {
    background-color: #202124;
}
#collapsiblePanelTitle {
    background-color: #202124;
}
#collapsiblePanelTitleLabel {
    color: #f1f1f1;
    font-weight: bold;
}
#collapsedSideHandle, #collapsedTopHandle {
    background-color: #2b2d31;
    color: #f1f1f1;
    border: 1px solid #4b4f57;
    font-size: 15px;
    font-weight: bold;
    padding: 0;
}
#collapsedSideHandle:hover, #collapsedTopHandle:hover {
    background-color: #383c42;
}
QSplitter::handle {
    background-color: #303236;
}
QSplitter::handle:horizontal {
    width: 4px;
}
QSplitter::handle:vertical {
    height: 4px;
}
QLineEdit, QTextEdit, QTableWidget, QTreeWidget, QComboBox, QTabWidget::pane {
    background-color: #15171a;
    color: #f1f1f1;
    border: 1px solid #3a3d42;
    selection-background-color: #3d5afe;
}
QHeaderView::section {
    background-color: #2b2d31;
    color: #f1f1f1;
    padding: 4px;
    border: 1px solid #3a3d42;
}
QPushButton, QToolButton {
    background-color: #2b2d31;
    color: #f1f1f1;
    border: 1px solid #4b4f57;
    padding: 5px 8px;
    border-radius: 4px;
}
QPushButton:hover, QToolButton:hover {
    background-color: #383c42;
}
QMenuBar, QMenu {
    background-color: #1b1d20;
    color: #f1f1f1;
}
QMenuBar::item:selected, QMenu::item:selected {
    background-color: #383c42;
}
QTabBar::tab {
    background-color: #2b2d31;
    color: #f1f1f1;
    padding: 6px 12px;
    border: 1px solid #3a3d42;
}
QTabBar::tab:selected {
    background-color: #383c42;
}

QCheckBox {
    spacing: 8px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 2px solid #9aa0a6;
    background-color: #15171a;
}
QCheckBox::indicator:hover {
    border: 2px solid #4fc3f7;
    background-color: #1f2933;
}
QCheckBox::indicator:checked {
    border: 2px solid #4fc3f7;
    background-color: #1976d2;
    image: none;
}
QCheckBox::indicator:checked:hover {
    border: 2px solid #80d8ff;
    background-color: #2196f3;
}
QCheckBox::indicator:checked:disabled {
    border: 2px solid #5f6368;
    background-color: #3a3d42;
}
QCheckBox::indicator:unchecked:disabled {
    border: 2px solid #4b4f57;
    background-color: #202124;
}
QToolBar {
    background-color: #1b1d20;
    border-bottom: 1px solid #3a3d42;
    spacing: 6px;
}
"""


def _find_logo() -> QIcon:
    root = Path(__file__).resolve().parents[1]
    candidates = [
        Path(__file__).resolve().parent / "assets" / "boa_logo.png",
        root / "assets" / "boa_logo.png",
        root / "assets" / "boa_logo.ico",
        root / "assets" / "logo.png",
        root / "assets" / "logo.ico",
    ]
    for path in candidates:
        if path.exists():
            return QIcon(str(path))
    return QIcon()


def run() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Boa")
    app.setStyleSheet(DARK_STYLE)

    icon = _find_logo()
    if not icon.isNull():
        app.setWindowIcon(icon)

    window = MainWindow()
    if not icon.isNull():
        window.setWindowIcon(icon)
    window.show()
    def startup_notices() -> None:
        show_welcome_if_needed(window)
        show_python_index_notice(window)

    QTimer.singleShot(0, startup_notices)

    sys.exit(app.exec())
