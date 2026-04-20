"""Image enhancement: rotation, deskew, denoise, binarize, resize."""

import cv2
import numpy as np
import logging

from config import TARGET_LONG_EDGE, MIN_LONG_EDGE

logger = logging.getLogger(__name__)


def rotate_90_cw(image: np.ndarray) -> np.ndarray:
    """Rotate image 90 degrees clockwise."""
    return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)


def rotate_90_ccw(image: np.ndarray) -> np.ndarray:
    """Rotate image 90 degrees counter-clockwise."""
    return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)


def deskew(image: np.ndarray) -> np.ndarray:
    """Fine-grained skew correction using text contour analysis.

    Detects small rotation angles (< 15 degrees) and corrects them.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # Use adaptive threshold to find text regions
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 21, 10
    )

    # Find coordinates of all non-zero pixels (text)
    coords = np.column_stack(np.where(thresh > 0))
    if len(coords) < 100:
        return image

    # Get minimum area rectangle
    angle = cv2.minAreaRect(coords)[-1]

    # Adjust angle
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    # Only correct if angle is small (< 15 degrees) to avoid over-correction
    if abs(angle) < 0.5 or abs(angle) > 15:
        return image

    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(image, rotation_matrix, (w, h),
                             flags=cv2.INTER_CUBIC,
                             borderMode=cv2.BORDER_REPLICATE)
    return rotated


def denoise(image: np.ndarray) -> np.ndarray:
    """Remove paper texture, shadows, and noise."""
    # Light Gaussian blur to reduce noise while preserving edges
    denoised = cv2.GaussianBlur(image, (3, 3), 0)
    return denoised


def binarize(image: np.ndarray) -> np.ndarray:
    """Convert to binary image using adaptive thresholding.

    Handles uneven lighting from phone camera photos.
    Returns a single-channel binary image (0 or 255).
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 21, 10
    )
    return binary


def adapt_resolution(image: np.ndarray,
                     target_long_edge: int = TARGET_LONG_EDGE,
                     min_long_edge: int = MIN_LONG_EDGE) -> np.ndarray:
    """Scale image to optimal OCR input size.

    Balances recognition accuracy with CPU inference time.
    """
    h, w = image.shape[:2]
    long_edge = max(h, w)

    if long_edge <= target_long_edge and long_edge >= min_long_edge:
        return image

    if long_edge > target_long_edge:
        scale = target_long_edge / long_edge
    else:
        scale = min_long_edge / long_edge

    new_w = int(w * scale)
    new_h = int(h * scale)
    interp = cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC
    resized = cv2.resize(image, (new_w, new_h), interpolation=interp)
    return resized


def enhance_image(image: np.ndarray) -> np.ndarray:
    """Preprocessing pipeline for OCR input.

    Steps: deskew → denoise → resize.
    Note: Rotation is handled manually by the user via toolbar buttons.
    Binarization is NOT applied because PaddleOCR works better with color input.

    Returns:
        Enhanced BGR image ready for OCR.
    """
    image = deskew(image)
    image = denoise(image)
    image = adapt_resolution(image)
    return image
