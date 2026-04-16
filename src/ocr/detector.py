"""Text detection and recognition using PaddleOCR.

Runs the full OCR pipeline (detection + recognition) in one pass for efficiency.
"""

import logging

import numpy as np

from src.parsing.data_models import TextBox, OCRResult
from src.ocr.engine import OCREngine

logger = logging.getLogger(__name__)


class TextDetector:
    """Detect and recognize all text regions in an image."""

    def __init__(self):
        self._engine = OCREngine()

    def detect_and_recognize(self, image: np.ndarray, source_path: str = "") -> OCRResult:
        """Run full OCR pipeline: detect text regions and recognize their content.

        Uses PaddleOCR's combined pipeline for efficiency (batched recognition).

        Args:
            image: Preprocessed BGR numpy array.
            source_path: Path to the source image file.

        Returns:
            OCRResult with all detected TextBoxes containing text and confidence.
        """
        ocr = self._engine.get_text_ocr()
        results = ocr.ocr(image, cls=True)

        boxes = []
        if results and results[0]:
            for line_result in results[0]:
                polygon = line_result[0]  # [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
                text, confidence = line_result[1]

                box = TextBox.from_polygon(
                    polygon=polygon,
                    text=text.strip(),
                    confidence=confidence,
                )
                boxes.append(box)

        logger.info(f"Detected {len(boxes)} text regions.")
        return OCRResult(
            source_path=source_path,
            image_shape=image.shape,
            boxes=boxes,
        )
