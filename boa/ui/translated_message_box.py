from PySide6.QtWidgets import QMessageBox


def ask_yes_no(parent, title: str, message: str, yes_text: str, no_text: str) -> bool:
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Question)
    box.setWindowTitle(title)
    box.setText(message)
    yes_button = box.addButton(yes_text, QMessageBox.ButtonRole.YesRole)
    no_button = box.addButton(no_text, QMessageBox.ButtonRole.NoRole)
    box.setDefaultButton(no_button)
    box.exec()
    return box.clickedButton() is yes_button
