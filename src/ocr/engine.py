"""PaddleOCR engine singleton manager.

Manages lifecycle of the PaddleOCR model instance.
Model is loaded lazily on first use and cached.
"""

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

            # Determine model paths.
            # In PyInstaller frozen env, models are bundled at:
            #   _internal/models/<model_name>/
            # PADDLE_OCR_BASE_DIR is set by runtime_hook_paddle.py.
            # We pass explicit paths so PaddleOCR won't try to download.
            bundled_models = os.environ.get('PADDLE_OCR_BASE_DIR', '')
            if bundled_models and os.path.isdir(bundled_models):
                det_model_dir = os.path.join(bundled_models, 'ch_PP-OCRv4_det_infer')
                rec_model_dir = os.path.join(bundled_models, 'ch_PP-OCRv4_rec_infer')
                cls_model_dir = os.path.join(bundled_models, 'ch_ppocr_mobile_v2.0_cls_infer')
                logger.info("Using bundled models from: %s", bundled_models)
            else:
                det_model_dir = None
                rec_model_dir = None
                cls_model_dir = None
                logger.warning("Bundled models not found, will download if needed")

            self._text_ocr = PaddleOCR(
                use_angle_cls=True,
                lang='ch',
                use_gpu=False,
                show_log=False,
                det_db_thresh=OCR_DET_DB_THRESH,
                det_db_unclip_ratio=OCR_DET_DB_UNCLIP_RATIO,
                rec_batch_num=OCR_REC_BATCH_NUM,
                drop_score=OCR_DROP_SCORE,
                det_model_dir=det_model_dir,
                rec_model_dir=rec_model_dir,
                cls_model_dir=cls_model_dir,
            )
            logger.info("PP-OCRv4 engine initialized.")
        return self._text_ocr

    def warmup(self) -> None:
        """Pre-load model. Call in background thread on app start."""
        self.get_text_ocr()
