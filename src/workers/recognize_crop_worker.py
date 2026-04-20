"""Background worker for re-recognizing a single cropped text box."""

from PySide6.QtCore import QThread, Signal

import numpy as np
import logging

from src.parsing.data_models import TextBox
from src.ocr.recognizer import TextCropRecognizer

logger = logging.getLogger(__name__)


class RecognizeCropWorker(QThread):
    """Background thread for re-OCR on a single resized box."""

    finished = Signal(str, str, float)  # (box_id, new_text, confidence)
    error = Signal(str, str)            # (box_id, error_message)

    def __init__(self, image: np.ndarray, box: TextBox, parent=None):
        super().__init__(parent)
        self._image = image
        self._box = box

    def run(self):
        try:
            recognizer = TextCropRecognizer()
            updated = recognizer.recognize_single(self._image, self._box)
            self.finished.emit(updated.box_id, updated.text, updated.confidence)
        except Exception as e:
            self.error.emit(self._box.box_id, f"重新识别失败: {e}")
