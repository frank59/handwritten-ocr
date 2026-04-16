"""Toolbar with state-aware action buttons."""

from enum import Enum, auto

from PySide6.QtWidgets import QToolBar
from PySide6.QtGui import QAction


class AppState(Enum):
    EMPTY = auto()
    IMAGE_LOADED = auto()
    OCR_DONE = auto()
    TABLE_GENERATED = auto()


class ToolBar(QToolBar):
    """Main toolbar with workflow-driven button states."""

    def __init__(self, parent=None):
        super().__init__("工具栏", parent)
        self.setMovable(False)

        # Open Image
        self.action_open = QAction("打开图片", self)
        self.action_open.setShortcut("Ctrl+O")
        self.action_open.setToolTip("打开图片文件 (Ctrl+O)")
        self.addAction(self.action_open)

        self.addSeparator()

        # Rotate Left
        self.action_rotate_left = QAction("↺ 左旋", self)
        self.action_rotate_left.setToolTip("逆时针旋转 90°")
        self.action_rotate_left.setEnabled(False)
        self.addAction(self.action_rotate_left)

        # Rotate Right
        self.action_rotate_right = QAction("↻ 右旋", self)
        self.action_rotate_right.setToolTip("顺时针旋转 90°")
        self.action_rotate_right.setEnabled(False)
        self.addAction(self.action_rotate_right)

        self.addSeparator()

        # Recognize
        self.action_recognize = QAction("识别", self)
        self.action_recognize.setToolTip("检测并识别图片中的文字")
        self.action_recognize.setEnabled(False)
        self.addAction(self.action_recognize)

        self.addSeparator()

        # Generate column guides
        self.action_generate_guides = QAction("生成列辅助", self)
        self.action_generate_guides.setToolTip("根据首行文字估算列位置，生成可拖拽的列辅助线")
        self.action_generate_guides.setEnabled(False)
        self.addAction(self.action_generate_guides)

        # Add guide line
        self.action_add_guide = QAction("添加辅助线", self)
        self.action_add_guide.setToolTip("在图片中心添加一条列辅助线")
        self.action_add_guide.setEnabled(False)
        self.addAction(self.action_add_guide)

        self.addSeparator()

        # Generate Table
        self.action_generate_table = QAction("生成表格", self)
        self.action_generate_table.setToolTip("根据文字区域坐标生成表格")
        self.action_generate_table.setEnabled(False)
        self.addAction(self.action_generate_table)

        self.addSeparator()

        # Export Excel
        self.action_export = QAction("导出 Excel", self)
        self.action_export.setShortcut("Ctrl+S")
        self.action_export.setToolTip("将表格导出为 Excel 文件 (Ctrl+S)")
        self.action_export.setEnabled(False)
        self.addAction(self.action_export)

    def set_state(self, state: AppState):
        """Update button enabled states based on application state."""
        has_image = state in (AppState.IMAGE_LOADED, AppState.OCR_DONE, AppState.TABLE_GENERATED)
        has_ocr = state in (AppState.OCR_DONE, AppState.TABLE_GENERATED)
        has_table = state == AppState.TABLE_GENERATED

        self.action_rotate_left.setEnabled(has_image)
        self.action_rotate_right.setEnabled(has_image)
        self.action_recognize.setEnabled(has_image)
        self.action_generate_guides.setEnabled(has_ocr)
        self.action_add_guide.setEnabled(has_ocr)
        self.action_generate_table.setEnabled(has_ocr)
        self.action_export.setEnabled(has_table)
