from __future__ import annotations

from PySide6.QtCore import QEvent, QPoint, Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMainWindow, QMenu, QSplitter, QTabBar, QTabWidget, QToolBar, QWidget

from boa.i18n import tr
from boa.ui.block_library import BlockLibrary
from boa.ui.toolbar import BoaToolBar


class DetachableTabBar(QTabBar):
    detach_requested = Signal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent); self._pressed = -1; self.setMovable(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu); self.customContextMenuRequested.connect(self._menu)

    def mousePressEvent(self, event) -> None:
        self._pressed = self.tabAt(event.position().toPoint()); super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        index = self._pressed; self._pressed = -1
        if index >= 0 and not self.rect().contains(event.position().toPoint()):
            self.detach_requested.emit(index); event.accept(); return
        super().mouseReleaseEvent(event)

    def _menu(self, pos: QPoint) -> None:
        index = self.tabAt(pos)
        if index < 0: return
        menu = QMenu(self); detach = menu.addAction(tr("tabs.detach"))
        if menu.exec(self.mapToGlobal(pos)) == detach: self.detach_requested.emit(index)


class DocumentTabs(QTabWidget):
    document_activated = Signal(str, str, object)
    document_closed = Signal(str, str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent); bar = DetachableTabBar(self); self.setTabBar(bar)
        self.setTabsClosable(True); self.setMovable(True); self._meta: dict[QWidget, tuple[str, str]] = {}; self._windows: dict[tuple[str, str], DetachedDocumentWindow] = {}
        bar.detach_requested.connect(self.detach_tab); self.tabCloseRequested.connect(self.close_tab); self.currentChanged.connect(self._activated)

    def open_document(self, kind: str, uid: str, title: str, widget: QWidget) -> QWidget:
        key = (kind, uid); existing = self.widget_for(kind, uid)
        if existing:
            window = self._windows.get(key)
            if window: window.show(); window.raise_(); window.activateWindow(); self.document_activated.emit(kind, uid, existing)
            else: self.setCurrentWidget(existing)
            return existing
        self._meta[widget] = key; index = self.addTab(widget, title); self.setCurrentIndex(index); return widget

    def widget_for(self, kind: str, uid: str) -> QWidget | None:
        return next((widget for widget, meta in self._meta.items() if meta == (kind, uid)), None)

    def detach_tab(self, index: int) -> None:
        widget = self.widget(index)
        if widget is None: return
        kind, uid = self._meta[widget]; title = self.tabText(index); self.removeTab(index)
        window = DetachedDocumentWindow(widget, kind, title, self)
        window.reattach_requested.connect(lambda: self.reattach(kind, uid))
        window.view_closed.connect(lambda: self._close_detached(kind, uid))
        window.activated.connect(lambda: self.document_activated.emit(kind, uid, widget))
        self._windows[(kind, uid)] = window; window.show(); window.raise_(); self.document_activated.emit(kind, uid, widget)

    def reattach(self, kind: str, uid: str) -> None:
        key = (kind, uid); window = self._windows.pop(key, None); widget = self.widget_for(kind, uid)
        if not window or not widget: return
        title = window.document_title; window.take_document(); window.close_for_reattach()
        index = self.addTab(widget, title); self.setCurrentIndex(index)

    def close_tab(self, index: int) -> None:
        widget = self.widget(index)
        if widget is None: return
        kind, uid = self._meta.pop(widget); self.removeTab(index); widget.deleteLater(); self.document_closed.emit(kind, uid)

    def close_document(self, kind: str, uid: str) -> None:
        widget = self.widget_for(kind, uid)
        if not widget: return
        window = self._windows.get((kind, uid))
        if window: window.close(); return
        self.close_tab(self.indexOf(widget))

    def rename_document(self, kind: str, uid: str, title: str) -> None:
        widget = self.widget_for(kind, uid)
        if not widget: return
        window = self._windows.get((kind, uid))
        if window: window.set_document_title(title)
        else:
            index = self.indexOf(widget)
            if index >= 0: self.setTabText(index, title)

    def documents(self) -> list[tuple[str, str, QWidget]]:
        return [(kind, uid, widget) for widget, (kind, uid) in list(self._meta.items())]

    def clear_documents(self) -> None:
        for window in list(self._windows.values()):
            document = window.take_document(); document.deleteLater(); window.close_for_reattach(); window.deleteLater()
        self._windows.clear()
        while self.count():
            widget = self.widget(0); self.removeTab(0); widget.deleteLater()
        self._meta.clear()

    def _activated(self, index: int) -> None:
        widget = self.widget(index)
        if widget in self._meta:
            kind, uid = self._meta[widget]; self.document_activated.emit(kind, uid, widget)

    def _close_detached(self, kind: str, uid: str) -> None:
        widget = self.widget_for(kind, uid); self._windows.pop((kind, uid), None)
        if widget: self._meta.pop(widget, None); widget.deleteLater()
        self.document_closed.emit(kind, uid)


class DetachedDocumentWindow(QMainWindow):
    reattach_requested = Signal()
    view_closed = Signal()
    activated = Signal()

    def __init__(self, document: QWidget, kind: str, title: str, parent=None) -> None:
        super().__init__(parent, Qt.WindowType.Window); self.document = document; self.document_kind = kind; self.document_title = title; self._reattaching = False
        self.set_document_title(title); self.resize(1180, 760)
        if hasattr(document, "add_block"):
            toolbar = BoaToolBar(self); toolbar.set_document_kind(kind); toolbar.block_requested.connect(document.add_block); self.addToolBar(toolbar)
            library = BlockLibrary(self); library.set_document_kind(kind); library.block_requested.connect(document.add_block)
            splitter = QSplitter(); splitter.addWidget(document); splitter.addWidget(library); splitter.setSizes([900, 260]); self.setCentralWidget(splitter)
        else: self.setCentralWidget(document)
        actions = QToolBar(tr("tabs.window"), self); attach = QAction(tr("tabs.reattach"), self); attach.triggered.connect(self.reattach_requested.emit); actions.addAction(attach); self.addToolBar(actions)

    def set_document_title(self, title: str) -> None:
        self.document_title = title; self.setWindowTitle(f"Boa — {title}")

    def take_document(self) -> QWidget:
        self.document.setParent(None); return self.document

    def close_for_reattach(self) -> None:
        self._reattaching = True; self.close()

    def event(self, event) -> bool:
        if event.type() == QEvent.Type.WindowActivate: self.activated.emit()
        return super().event(event)

    def closeEvent(self, event) -> None:
        if not self._reattaching: self.view_closed.emit()
        event.accept()
