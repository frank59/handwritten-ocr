"""Utility dialogs: progress, error messages."""

from PySide6.QtWidgets import QProgressDialog, QMessageBox
from PySide6.QtCore import Qt


class ProcessingDialog(QProgressDialog):
    """Progress dialog shown during OCR processing."""

    def __init__(self, parent=None):
        super().__init__("正在处理图片...", "取消", 0, 100, parent)
        self.setWindowTitle("处理中")
        self.setWindowModality(Qt.WindowModal)
        self.setMinimumDuration(0)
        self.setAutoClose(True)
        self.setAutoReset(True)

    def update_status(self, message: str, progress: int) -> None:
        """Update the progress label and bar value."""
        self.setLabelText(message)
        self.setValue(progress)


def show_error(parent, title: str, message: str) -> None:
    """Show an error dialog."""
    QMessageBox.critical(parent, title, message)


def show_info(parent, title: str, message: str) -> None:
    """Show an info dialog."""
    QMessageBox.information(parent, title, message)


def confirm_action(parent, title: str, message: str) -> bool:
    """Show a confirmation dialog. Returns True if user confirms."""
    result = QMessageBox.question(
        parent, title, message,
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.No,
    )
    return result == QMessageBox.Yes
