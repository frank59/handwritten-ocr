"""Signal hub for TextBoxItem communication.

QGraphicsRectItem cannot emit signals directly (not a QObject),
so we use a shared signal hub that all items reference.
"""

from PySide6.QtCore import QObject, Signal


class TextBoxSignals(QObject):
    """Shared signal emitter for all TextBoxItems on a canvas."""

    text_edited = Signal(str, str)       # (box_id, new_text)
    box_resized = Signal(str, tuple)     # (box_id, (x, y, w, h))
    box_deleted = Signal(str)            # (box_id,)
    box_created = Signal(str, tuple)     # (box_id, (x, y, w, h))
    guide_deleted = Signal(str)          # (guide_id,)
    guide_selected = Signal(str, bool)   # (guide_id, is_selected)
