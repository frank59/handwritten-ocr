"""Image loading and validation."""

import os
import sys
import cv2
import numpy as np
import logging

from config import SUPPORTED_EXTENSIONS, MAX_FILE_SIZE_MB

logger = logging.getLogger(__name__)


class ImageLoadError(Exception):
    """Raised when image loading fails."""
    pass


def _to_fs_path(file_path: str) -> str:
    """Convert path to filesystem encoding for cv2.imread compatibility.

    On Windows with Chinese locale, cv2.imread may fail on paths with
    non-ASCII characters. Use os.fsdecode to normalize the path.
    """
    # If already bytes, decode with filesystem encoding
    if isinstance(file_path, bytes):
        return file_path
    # On Windows, try converting to filesystem encoding to help cv2.imread
    if sys.platform == 'win32':
        try:
            return os.fsencode(file_path).decode('gbk')
        except (UnicodeDecodeError, UnicodeEncodeError):
            pass
    return file_path


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

    # Convert path for cv2.imread compatibility on Windows with non-ASCII paths
    fs_path = _to_fs_path(file_path)

    image = cv2.imread(fs_path, cv2.IMREAD_COLOR)
    if image is None:
        raise ImageLoadError(f"无法读取图片文件，请确认文件完整: {file_path}")

    return image
