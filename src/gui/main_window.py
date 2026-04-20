"""Main application window with canvas-based OCR workflow."""

import logging
import os

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QLabel, QPushButton, QFileDialog, QMessageBox,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QKeySequence

from config import WINDOW_WIDTH, WINDOW_HEIGHT, APP_NAME
from src.preprocessing.loader import load_image, ImageLoadError
from src.parsing.data_models import TextBox, OCRResult, ParsedDocument
from src.export.excel_writer import write_excel, ExportError
from src.gui.canvas.image_canvas import ImageCanvas
from src.gui.table_widget import EditableTableWidget
from src.gui.toolbar import ToolBar, AppState
from src.gui.dialogs import ProcessingDialog, show_error, show_info, confirm_action
from src.workers.ocr_worker import OCRWorker
from src.workers.recognize_crop_worker import RecognizeCropWorker

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)

        self._app_state = AppState.EMPTY
        self._current_image = None      # np.ndarray BGR
        self._source_path = ""
        self._ocr_result = None         # OCRResult
        self._current_doc = None        # ParsedDocument
        self._worker = None
        self._crop_worker = None
        self._pending_resize_box_id = None
        self._pending_resize_rect = None
        self._resize_debounce_timer = QTimer(self)
        self._resize_debounce_timer.setSingleShot(True)
        self._resize_debounce_timer.setInterval(1000)
        self._resize_debounce_timer.timeout.connect(self._on_resize_debounce_timeout)

        self._setup_ui()
        self._connect_signals()
        self._set_state(AppState.EMPTY)

    def _setup_ui(self):
        # Toolbar
        self.toolbar = ToolBar(self)
        self.addToolBar(self.toolbar)

        # Stacked widget: page 0 = canvas, page 1 = table
        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        # Page 0: Canvas view
        self._canvas = ImageCanvas()
        self._stack.addWidget(self._canvas)

        # Page 1: Table view with navigation buttons
        table_page = QWidget()
        table_layout = QVBoxLayout(table_page)

        # Table toolbar
        table_toolbar = QHBoxLayout()
        self._btn_back_canvas = QPushButton("← 返回画布")
        self._btn_back_canvas.setToolTip("返回画布继续编辑文字区域")
        self._btn_add_row = QPushButton("添加行")
        self._btn_delete_row = QPushButton("删除行")
        table_toolbar.addWidget(self._btn_back_canvas)
        table_toolbar.addStretch()
        table_toolbar.addWidget(self._btn_add_row)
        table_toolbar.addWidget(self._btn_delete_row)
        table_layout.addLayout(table_toolbar)

        self._table_widget = EditableTableWidget()
        table_layout.addWidget(self._table_widget)
        self._stack.addWidget(table_page)

        # Status bar
        self.statusBar().showMessage("就绪")

        # Menu bar
        self._setup_menu()

    def _setup_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("文件")
        open_action = QAction("打开图片", self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self.on_open_image)
        file_menu.addAction(open_action)

        export_action = QAction("导出 Excel", self)
        export_action.setShortcut(QKeySequence.Save)
        export_action.triggered.connect(self.on_export_excel)
        file_menu.addAction(export_action)

        file_menu.addSeparator()
        quit_action = QAction("退出", self)
        quit_action.setShortcut(QKeySequence.Quit)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        help_menu = menubar.addMenu("帮助")
        about_action = QAction("关于", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _connect_signals(self):
        # Toolbar
        self.toolbar.action_open.triggered.connect(self.on_open_image)
        self.toolbar.action_rotate_left.triggered.connect(lambda: self.on_rotate(-90))
        self.toolbar.action_rotate_right.triggered.connect(lambda: self.on_rotate(90))
        self.toolbar.action_recognize.triggered.connect(self.on_recognize)
        self.toolbar.action_generate_guides.triggered.connect(self.on_generate_guides)
        self.toolbar.action_add_guide.triggered.connect(self.on_add_guide)
        self.toolbar.action_generate_table.triggered.connect(self.on_generate_table)
        self.toolbar.action_export.triggered.connect(self.on_export_excel)

        # Canvas signals
        self._canvas.signals.text_edited.connect(self._on_box_text_edited)
        self._canvas.signals.box_resized.connect(self._on_box_resized)
        self._canvas.signals.box_deleted.connect(self._on_box_deleted)
        self._canvas.signals.box_created.connect(self._on_box_created)
        self._canvas.signals.guide_deleted.connect(self._on_guide_deleted)

        # Table page buttons
        self._btn_back_canvas.clicked.connect(self._switch_to_canvas)
        self._btn_add_row.clicked.connect(self._table_widget.add_row)
        self._btn_delete_row.clicked.connect(self._table_widget.delete_row)

    def _set_state(self, state: AppState):
        self._app_state = state
        self.toolbar.set_state(state)

    # --- Open Image ---

    def on_open_image(self):
        ext_filter = "图片文件 (*.jpg *.jpeg *.png *.bmp);;所有文件 (*)"
        file_path, _ = QFileDialog.getOpenFileName(self, "选择图片", "", ext_filter)
        if not file_path:
            return

        logger.info("[ui] 打开图片: %s", file_path)
        try:
            image = load_image(file_path)
        except ImageLoadError as e:
            logger.error("[ui] 图片加载失败: %s", e)
            show_error(self, "加载失败", str(e))
            return

        self._current_image = image
        self._source_path = file_path
        self._ocr_result = None
        self._current_doc = None

        self._canvas.set_image(image)
        self._stack.setCurrentIndex(0)
        self._set_state(AppState.IMAGE_LOADED)
        logger.info("[ui] 图片加载成功: shape=%s", image.shape)
        self.statusBar().showMessage(f"已加载: {os.path.basename(file_path)}")

    # --- Rotate ---

    def on_rotate(self, degrees: int):
        if self._current_image is None:
            return

        # Warn if OCR results will be lost
        if self._canvas.has_boxes():
            if not confirm_action(self, "确认旋转",
                                  "旋转将清除当前识别结果，是否继续？"):
                return

        self._canvas.rotate_image(degrees)
        self._current_image = self._canvas.get_image_np()
        self._ocr_result = None
        self._current_doc = None
        self._set_state(AppState.IMAGE_LOADED)
        self.statusBar().showMessage("图片已旋转")

    # --- Recognize ---

    def on_recognize(self):
        if self._current_image is None:
            return

        # Clean up previous worker
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait()

        # Clear existing boxes and guides
        self._canvas.clear_boxes()
        self._canvas.clear_guide_lines()

        # Show progress
        self._progress = ProcessingDialog(self)
        self._progress.canceled.connect(self._on_cancel_ocr)

        self._worker = OCRWorker(self._current_image, self._source_path, self)
        self._worker.progress.connect(self._on_ocr_progress)
        self._worker.finished.connect(self._on_ocr_finished)
        self._worker.error.connect(self._on_ocr_error)
        self._worker.start()
        self._progress.show()

    def _on_ocr_progress(self, message, percent):
        if hasattr(self, '_progress') and self._progress:
            self._progress.update_status(message, percent)

    def _on_ocr_finished(self, result: OCRResult):
        if hasattr(self, '_progress') and self._progress:
            self._progress.close()

        self._ocr_result = result
        self._canvas.add_text_boxes(result.boxes)
        self._stack.setCurrentIndex(0)
        self._set_state(AppState.OCR_DONE)
        self.statusBar().showMessage(f"识别完成，共 {len(result.boxes)} 个文字区域")

    def _on_ocr_error(self, message):
        if hasattr(self, '_progress') and self._progress:
            self._progress.close()
        show_error(self, "识别错误", message)
        self.statusBar().showMessage("识别失败")

    def _on_cancel_ocr(self):
        if self._worker:
            self._worker.cancel()
        self.statusBar().showMessage("已取消识别")

    # --- Box interactions ---

    def _on_box_text_edited(self, box_id: str, new_text: str):
        """Update OCR result when user edits text in a box."""
        if self._ocr_result:
            for box in self._ocr_result.boxes:
                if box.box_id == box_id:
                    box.text = new_text
                    break

    def _on_box_resized(self, box_id: str, new_rect: tuple):
        """Debounce: schedule OCR re-recognition 1s after last resize event."""
        if self._current_image is None or self._ocr_result is None:
            return

        # Update box rect in OCR result immediately
        for box in self._ocr_result.boxes:
            if box.box_id == box_id:
                box.rect = new_rect
                break

        # Store pending info and restart the 1-second timer
        self._pending_resize_box_id = box_id
        self._pending_resize_rect = new_rect
        self._resize_debounce_timer.start()

    def _on_resize_debounce_timeout(self):
        """Timer fired: 1s since last resize — run OCR on the pending box."""
        box_id = self._pending_resize_box_id
        self._pending_resize_box_id = None
        self._pending_resize_rect = None

        if box_id is None or self._current_image is None or self._ocr_result is None:
            return

        target_box = None
        for box in self._ocr_result.boxes:
            if box.box_id == box_id:
                target_box = box
                break
        if not target_box:
            return

        # Disconnect previous crop worker signals to avoid stale results
        if self._crop_worker is not None:
            try:
                self._crop_worker.finished.disconnect(self._on_crop_recognized)
                self._crop_worker.error.disconnect(self._on_crop_error)
            except RuntimeError:
                pass

        self._crop_worker = RecognizeCropWorker(self._current_image, target_box, self)
        self._crop_worker.finished.connect(self._on_crop_recognized)
        self._crop_worker.error.connect(self._on_crop_error)
        self._crop_worker.start()
        self.statusBar().showMessage("正在重新识别...")

    def _on_crop_recognized(self, box_id: str, new_text: str, confidence: float):
        """Update box with re-recognized text."""
        self._canvas.update_box_text(box_id, new_text, confidence)
        if self._ocr_result:
            for box in self._ocr_result.boxes:
                if box.box_id == box_id:
                    box.text = new_text
                    box.confidence = confidence
                    break
        self.statusBar().showMessage("重新识别完成")

    def _on_crop_error(self, box_id: str, message: str):
        self.statusBar().showMessage(f"重新识别失败: {message}")

    def _on_box_deleted(self, box_id: str):
        """Mark box as deleted in OCR result."""
        self._canvas.remove_box(box_id)
        if self._ocr_result:
            for box in self._ocr_result.boxes:
                if box.box_id == box_id:
                    box.is_deleted = True
                    break
        self.statusBar().showMessage("已删除文字区域")

    def _on_box_created(self, box_id: str, rect: tuple):
        """Handle manually created box — add to OCR result and run recognition."""
        new_box = TextBox(box_id=box_id, rect=rect, text="", confidence=0.0)

        # Ensure OCR result exists
        if self._ocr_result is None:
            self._ocr_result = OCRResult(
                source_path=self._source_path,
                image_shape=self._current_image.shape if self._current_image is not None else (0, 0, 0),
                boxes=[],
            )
            self._set_state(AppState.OCR_DONE)

        self._ocr_result.boxes.append(new_box)

        # Run recognition on the new box
        if self._current_image is not None:
            if self._crop_worker is not None:
                try:
                    self._crop_worker.finished.disconnect(self._on_crop_recognized)
                    self._crop_worker.error.disconnect(self._on_crop_error)
                except RuntimeError:
                    pass

            self._crop_worker = RecognizeCropWorker(self._current_image, new_box, self)
            self._crop_worker.finished.connect(self._on_crop_recognized)
            self._crop_worker.error.connect(self._on_crop_error)
            self._crop_worker.start()
            self.statusBar().showMessage("正在识别新区域...")

    # --- Guide lines ---

    def on_generate_guides(self):
        """Generate column guide lines from first-row estimation."""
        self._canvas.generate_guide_lines()
        count = len(self._canvas._guide_lines)
        self.statusBar().showMessage(f"已生成 {count} 条列辅助线，拖动端点调整位置")

    def on_add_guide(self):
        """Add a single guide line."""
        self._canvas.add_guide_line()
        self.statusBar().showMessage("已添加辅助线")

    def _on_guide_deleted(self, guide_id: str):
        """Remove a guide line."""
        self._canvas.remove_guide_line(guide_id)
        self.statusBar().showMessage("已删除辅助线")

    # --- Generate Table ---

    def on_generate_table(self):
        if not self._canvas.has_boxes():
            show_error(self, "生成失败", "没有可用的文字区域，请先进行识别。")
            return

        from src.parsing.table_generator import TableGenerator

        boxes = self._canvas.get_all_boxes()
        generator = TableGenerator()

        # Use guide-line-based generation if guides exist
        if self._canvas.has_guide_lines():
            guide_lines = self._canvas.get_guide_lines()
            logger.warning("[生成表格] 使用辅助线模式: %d条辅助线, %d个矩形",
                           len(guide_lines), len(boxes))
            doc = generator.generate_with_guides(boxes, guide_lines, self._source_path)
        else:
            logger.warning("[生成表格] 使用自动聚类模式: %d个矩形", len(boxes))
            doc = generator.generate(boxes, self._source_path)

        if not doc.rows:
            show_error(self, "生成失败", "无法从文字区域生成表格。")
            return

        self._current_doc = doc
        self._table_widget.load_data(doc)
        self._stack.setCurrentIndex(1)
        self._set_state(AppState.TABLE_GENERATED)
        self.statusBar().showMessage(f"表格已生成: {len(doc.rows)} 行 × {len(doc.headers)} 列")

    # --- Canvas / Table navigation ---

    def _switch_to_canvas(self):
        self._stack.setCurrentIndex(0)
        self._set_state(AppState.OCR_DONE)
        self.statusBar().showMessage("返回画布编辑")

    # --- Export ---

    def on_export_excel(self):
        if self._current_doc is None:
            show_error(self, "导出错误", "没有可导出的数据，请先生成表格。")
            return

        doc = self._table_widget.get_data()
        doc.source_path = self._source_path
        doc.input_type = "generated"

        default_name = "识别结果.xlsx"
        if self._source_path:
            base = os.path.splitext(os.path.basename(self._source_path))[0]
            default_name = f"{base}_识别结果.xlsx"

        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存 Excel 文件", default_name,
            "Excel 文件 (*.xlsx);;所有文件 (*)"
        )
        if not file_path:
            return

        try:
            write_excel(doc, file_path)
            show_info(self, "导出成功", f"已保存到:\n{file_path}")
            self.statusBar().showMessage(f"已导出: {file_path}")
        except ExportError as e:
            show_error(self, "导出失败", str(e))

    def _show_about(self):
        QMessageBox.about(
            self, "关于",
            f"{APP_NAME}\n\n"
            "纯本地离线运行的手写表格识别工具\n"
            "上传图片 → OCR识别 → 可视化纠错 → 生成表格 → 导出Excel\n\n"
            "快捷操作:\n"
            "  Ctrl+拖拽: 手动框选新区域\n"
            "  Shift(按住): 临时隐藏所有矩形框\n"
            "  双击矩形: 编辑识别文字\n"
            "  Delete键: 删除选中区域\n\n"
            "技术栈: PaddleOCR + PySide6"
        )

    def closeEvent(self, event):
        """Clean up background workers before closing the window.

        Ensures the process terminates completely when the user clicks
        the × button, without leaving orphaned threads.
        """
        logger.info("[ui] 窗口关闭，开始清理后台线程...")

        # Cancel and wait for OCR worker
        if self._worker is not None and self._worker.isRunning():
            logger.info("[ui] 取消 OCR worker...")
            self._worker.cancel()
            self._worker.wait(3000)  # wait up to 3 seconds
            if self._worker.isRunning():
                logger.warning("[ui] OCR worker 未能在 3s 内结束，强制终止")
                self._worker.terminate()
                self._worker.wait()
            self._worker = None

        # Cancel and wait for crop recognition worker
        if self._crop_worker is not None and self._crop_worker.isRunning():
            logger.info("[ui] 取消 crop worker...")
            self._crop_worker.wait(3000)
            if self._crop_worker.isRunning():
                self._crop_worker.terminate()
                self._crop_worker.wait()
            self._crop_worker = None

        # Close progress dialog if open
        if hasattr(self, '_progress') and self._progress is not None:
            self._progress.close()
            self._progress = None

        logger.info("[ui] 所有线程已清理，进程即将退出")
        event.accept()

