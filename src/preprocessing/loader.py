"""Image loading and validation."""

import os
import cv2
import numpy as np
import logging

from config import SUPPORTED_EXTENSIONS, MAX_FILE_SIZE_MB

logger = logging.getLogger(__name__)


class ImageLoadError(Exception):
    """Raised when image loading fails."""
    pass


def validate_file(file_path: str) -> None:
    """Validate that the file exists, has supported format, and reasonable size."""
    if not os.path.exists(file_path):
        raise ImageLoadError(f"文件不存在: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ImageLoadError(
            f"不支持的文件格式: {ext}\n支持的格式: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise ImageLoadError(f"图片文件过大 ({size_mb:.1f}MB)，请压缩到 {MAX_FILE_SIZE_MB}MB 以下")

    if os.path.getsize(file_path) == 0:
        raise ImageLoadError("图片文件为空")


def load_image(file_path: str) -> np.ndarray:
    """Load an image from disk and return as BGR numpy array.

    Args:
        file_path: Path to image file (JPG, PNG, BMP).

    Returns:
        BGR numpy array (H, W, C).

    Raises:
        ImageLoadError: If file is invalid or unreadable.
    """
    validate_file(file_path)

    # Use open() + cv2.imdecode() instead of cv2.imread() to support
    # non-ASCII (e.g. Chinese) file paths on Windows.
    # cv2.imread relies on C runtime fopen() which cannot handle Unicode paths.
    try:
        with open(file_path, 'rb') as f:
            file_bytes = np.frombuffer(f.read(), np.uint8)
        image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    except OSError as e:
        logger.error("读取图片文件失败: %s, 错误: %s", file_path, e)
        raise ImageLoadError(f"无法读取图片文件: {file_path}\n{e}")

    if image is None:
        raise ImageLoadError(f"无法解码图片文件，请确认文件完整: {file_path}")

    logger.info("成功加载图片: %s, 尺寸: %s", file_path, image.shape)
    return image
