"""Application entry point."""

import sys
import os
import logging

# ============================================================
# PyInstaller 兼容性修复 - 必须在导入其他模块之前执行
# ============================================================
def setup_frozen_environment():
    """Setup environment for PyInstaller frozen executable."""
    if getattr(sys, 'frozen', False):
        # PyInstaller frozen environment
        application_path = os.path.dirname(sys.executable)
        
        # Fix site.USER_SITE being None
        import site
        if site.USER_SITE is None:
            site.ENABLE_USER_SITE = True
            site.USER_SITE = os.path.join(application_path, '_internal', 'Lib', 'site-packages')
        
        # Add _internal to path for paddle libs
        internal_path = os.path.join(application_path, '_internal')
        if internal_path not in sys.path:
            sys.path.insert(0, internal_path)
        
        # Set environment variables for paddle
        os.environ.setdefault('KMP_DUPLICATE_LIB_OK', 'TRUE')
        
        # Work directory for logging
        os.chdir(application_path)


setup_frozen_environment()

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