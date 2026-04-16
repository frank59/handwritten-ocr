"""Application entry point."""

import sys
import logging

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from config import APP_NAME
from src.gui.main_window import MainWindow


def main():
    logging.basicConfig(level=logging.WARNING, format="%(message)s")

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
