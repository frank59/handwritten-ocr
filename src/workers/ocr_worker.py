"""Background worker for full OCR detection + recognition."""

from PySide6.QtCore import QThread, Signal

import numpy as np

from src.preprocessing.enhancer import enhance_image
from src.preprocessing.loader import ImageLoadError
from src.ocr.detector import TextDetector
from src.parsing.data_models import OCRResult


class OCRWorker(QThread):
    """Background thread for running the OCR pipeline."""

    progress = Signal(str, int)      # (message, percent)
    finished = Signal(object)        # OCRResult
    error = Signal(str)              # error message

    def __init__(self, image: np.ndarray, source_path: str, parent=None):
        super().__init__(parent)
        self._image = image
        self._source_path = source_path
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            self.progress.emit("图像预处理...", 10)
            enhanced = enhance_image(self._image)
            if self._cancelled:
                return

            self.progress.emit("文字检测与识别中...", 30)
            detector = TextDetector()
            result = detector.detect_and_recognize(enhanced, self._source_path)
            if self._cancelled:
                return

            if not result.boxes:
                self.error.emit("未检测到文字区域，请确认图片清晰度。")
                return

            # Scale bounding boxes back if image was resized during enhancement
            orig_h, orig_w = self._image.shape[:2]
            enh_h, enh_w = enhanced.shape[:2]
            if (orig_h, orig_w) != (enh_h, enh_w):
                sx = orig_w / enh_w
                sy = orig_h / enh_h
                for box in result.boxes:
                    x, y, w, h = box.rect
                    box.rect = (int(x * sx), int(y * sy), int(w * sx), int(h * sy))
                    box.polygon = [[p[0] * sx, p[1] * sy] for p in box.polygon]
                result.image_shape = self._image.shape

            self.progress.emit("识别完成", 100)
            self.finished.emit(result)

        except Exception as e:
            self.error.emit(f"处理出错: {e}")
