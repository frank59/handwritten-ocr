"""PaddleOCR engine singleton manager.

Manages lifecycle of the PaddleOCR model instance.
Model is loaded lazily on first use and cached.
"""

import sys
import os
import logging

from paddleocr import PaddleOCR

from config import (
    OCR_DROP_SCORE,
    OCR_DET_DB_THRESH,
    OCR_DET_DB_UNCLIP_RATIO,
    OCR_REC_BATCH_NUM,
)

logger = logging.getLogger(__name__)


class OCREngine:
    """Singleton manager for PaddleOCR model instance."""

    _instance = None
    _text_ocr = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_text_ocr(self) -> PaddleOCR:
        """Get or initialize PP-OCRv4 instance."""
        if self._text_ocr is None:
            logger.info("Initializing PP-OCRv4 OCR engine...")
            # PaddleOCR may download model weights on first run.
            # tqdm writes to sys.stdout which is None in PyInstaller frozen env,
            # causing "'NoneType' object has no attribute 'write'" crash.
            # Redirect stdout to devnull to silence tqdm during download.
            _orig_stdout = sys.stdout
            _null_fd = open(os.devnull, 'w')
            sys.stdout = _null_fd
            try:
                self._text_ocr = PaddleOCR(
                    use_angle_cls=True,
                    lang='ch',
                    use_gpu=False,
                    show_log=False,
                    det_db_thresh=OCR_DET_DB_THRESH,
                    det_db_unclip_ratio=OCR_DET_DB_UNCLIP_RATIO,
                    rec_batch_num=OCR_REC_BATCH_NUM,
                    drop_score=OCR_DROP_SCORE,
                )
            finally:
                sys.stdout = _orig_stdout
                _null_fd.close()
            logger.info("PP-OCRv4 engine initialized.")
        return self._text_ocr

    def warmup(self) -> None:
        """Pre-load model. Call in background thread on app start."""
        self.get_text_ocr()
