from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox

from boa import __version__
from boa.core.preferences import save_preferences
from boa.i18n import tr


def show_quick_start(parent) -> None:
    _show(parent, tr("help.quick_start"), tr("help.quick_start_text"))


def show_controls(parent) -> None:
    _show(parent, tr("help.controls"), tr("help.controls_text"))


def show_conversion_limits(parent) -> None:
    _show(parent, tr("help.conversion"), tr("help.conversion_text"))


def show_about(parent) -> None:
    _show(parent, tr("help.about"), tr("help.about_text", version=__version__))


def show_welcome_if_needed(parent) -> None:
    if parent.preferences.get("welcome_shown", False):
        return
    show_quick_start(parent)
    parent.preferences["welcome_shown"] = True
    save_preferences(parent.preferences)


def _show(parent, title: str, text: str) -> None:
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setTextFormat(Qt.TextFormat.RichText)
    box.setText(text)
    box.setStandardButtons(QMessageBox.StandardButton.Ok)
    box.exec()
