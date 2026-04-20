"""Application entry point."""

import sys
import os
import logging
from logging.handlers import RotatingFileHandler

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

        # Work directory and log directory
        os.chdir(application_path)

        # Create logs directory next to exe
        logs_dir = os.path.join(application_path, 'logs')
        os.makedirs(logs_dir, exist_ok=True)

        # Configure logging with rotation (max 5MB per file, keep 3 backups)
        log_file = os.path.join(logs_dir, 'app.log')
        rotating_handler = RotatingFileHandler(
            log_file,
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=3,
            encoding='utf-8',
        )
        rotating_handler.setLevel(logging.DEBUG)
        rotating_handler.setFormatter(logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        ))

        root = logging.getLogger()
        root.setLevel(logging.DEBUG)
        root.addHandler(rotating_handler)
        root.addHandler(logging.StreamHandler(sys.stderr))

        logging.info(f'Logs written to: {log_file} (max 5MB, 3 backups)')
        logging.info(f'Application path: {application_path}')


setup_frozen_environment()

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from config import APP_NAME
from src.gui.main_window import MainWindow


def main():
    # If not frozen, just set basic config
    if not getattr(sys, 'frozen', False):
        logging.basicConfig(
            level=logging.WARNING,
            format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        )

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
