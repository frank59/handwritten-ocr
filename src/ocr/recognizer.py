"""Single-region text recognition using PaddleOCR.

Used for re-recognizing a text box after the user resizes it.
"""

import logging

import numpy as np

from src.parsing.data_models import TextBox
from src.ocr.engine import OCREngine

logger = logging.getLogger(__name__)


class TextCropRecognizer:
    """Recognize text in a cropped image region."""

    def __init__(self):
        self._engine = OCREngine()

    def recognize_single(self, image: np.ndarray, box: TextBox) -> TextBox:
        """Recognize text in a single cropped region of the image.

        Crops the image at box.rect and runs recognition-only OCR.

        Args:
            image: Full BGR image.
            box: TextBox with rect specifying the crop region.

        Returns:
            Updated TextBox with new text and confidence.
        """
        x, y, w, h = box.rect
        # Clamp to image bounds
        img_h, img_w = image.shape[:2]
        x = max(0, x)
        y = max(0, y)
        w = min(w, img_w - x)
        h = min(h, img_h - y)

        if w <= 0 or h <= 0:
            box.text = ""
            box.confidence = 0.0
            return box

        crop = image[y:y + h, x:x + w]

        ocr = self._engine.get_text_ocr()
        try:
            results = ocr.ocr(crop, det=False, cls=True)
            if results and results[0]:
                # det=False returns [(text, confidence), ...]
                texts = []
                total_conf = 0.0
                count = 0
                for item in results[0]:
                    if item and len(item) == 2:
                        text, conf = item
                        texts.append(text.strip())
                        total_conf += conf
                        count += 1
                box.text = " ".join(texts) if texts else ""
                box.confidence = total_conf / count if count > 0 else 0.0
            else:
                box.text = ""
                box.confidence = 0.0
        except Exception as e:
            logger.warning(f"Recognition failed for box {box.box_id}: {e}")
            box.text = ""
            box.confidence = 0.0

        return box
