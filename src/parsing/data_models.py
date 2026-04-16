"""Shared data models used across all layers."""

import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TextBox:
    """A detected text region on the image with recognized content."""
    box_id: str = ""
    polygon: list = field(default_factory=list)  # [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
    rect: tuple = (0, 0, 0, 0)  # (x, y, width, height) in original image coords
    text: str = ""
    confidence: float = 0.0
    is_deleted: bool = False

    def __post_init__(self):
        if not self.box_id:
            self.box_id = str(uuid.uuid4())

    @staticmethod
    def from_polygon(polygon, text="", confidence=0.0):
        """Create a TextBox from a 4-point polygon."""
        xs = [p[0] for p in polygon]
        ys = [p[1] for p in polygon]
        x, y = min(xs), min(ys)
        w, h = max(xs) - x, max(ys) - y
        return TextBox(
            polygon=polygon,
            rect=(int(x), int(y), int(w), int(h)),
            text=text,
            confidence=confidence,
        )


@dataclass
class OCRResult:
    """Container for full detection + recognition result for one image."""
    source_path: str = ""
    image_shape: tuple = (0, 0, 0)  # (H, W, C)
    boxes: list = field(default_factory=list)  # list[TextBox]


@dataclass
class ParsedRow:
    """One row of structured data."""
    fields: dict = field(default_factory=dict)
    confidence: float = 1.0


@dataclass
class ParsedDocument:
    """Complete result flowing into table widget and Excel export."""
    input_type: str = "generated"
    headers: list = field(default_factory=list)
    rows: list = field(default_factory=list)  # list[ParsedRow]
    source_path: str = ""
