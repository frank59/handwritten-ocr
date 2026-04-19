"""QGraphicsView-based image canvas with interactive text box overlays.

Displays the source image and hosts TextBoxItem instances for each
detected text region. Supports zoom (Ctrl+scroll), pan (scroll bars),
Shift-hold to hide overlays, and Ctrl+drag to create new boxes.
"""

import uuid

import cv2
import numpy as np

from PySide6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsRectItem,
    QGraphicsProxyWidget,
)
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPixmap, QImage, QPainter, QColor, QPen, QBrush

from src.parsing.data_models import TextBox
from src.gui.canvas.text_box_item import TextBoxItem
from src.gui.canvas.text_edit_proxy import TextBoxSignals


def _numpy_to_qpixmap(image: np.ndarray) -> QPixmap:
    """Convert BGR numpy array to QPixmap."""
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    h, w, ch = rgb.shape
    bytes_per_line = ch * w
    qimage = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
    return QPixmap.fromImage(qimage.copy())


class ImageCanvas(QGraphicsView):
    """Image viewer with interactive text box overlays."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        self._pixmap_item = None
        self._image_np = None  # current image as numpy BGR
        self._text_box_items = {}  # box_id -> TextBoxItem
        self._guide_lines = []     # list of ColumnGuideItem

        self.signals = TextBoxSignals()
        self.signals.guide_selected.connect(self._on_guide_selected)

        # Shift-hide state
        self._boxes_hidden = False

        # Ctrl+drag drawing state
        self._is_drawing = False
        self._draw_start = None
        self._rubber_band = None

        # View settings
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setViewportUpdateMode(QGraphicsView.SmartViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setFocusPolicy(Qt.StrongFocus)

        # Styling
        self.setStyleSheet("background-color: #2b2b2b; border: none;")

    def set_image(self, image: np.ndarray):
        """Display a new image and clear all text boxes."""
        self._image_np = image.copy()
        self.clear_boxes()
        self.clear_guide_lines()

        pixmap = _numpy_to_qpixmap(image)

        if self._pixmap_item:
            self._scene.removeItem(self._pixmap_item)

        self._pixmap_item = QGraphicsPixmapItem(pixmap)
        self._pixmap_item.setZValue(0)
        self._scene.addItem(self._pixmap_item)
        self._scene.setSceneRect(QRectF(pixmap.rect()))

        self.fit_in_view()

    def fit_in_view(self):
        """Fit the image in the viewport."""
        if self._pixmap_item:
            self.fitInView(self._pixmap_item, Qt.KeepAspectRatio)

    def rotate_image(self, degrees: int):
        """Rotate the current image by degrees (90 or -90) and clear boxes."""
        if self._image_np is None:
            return

        if degrees == 90:
            self._image_np = cv2.rotate(self._image_np, cv2.ROTATE_90_CLOCKWISE)
        elif degrees == -90:
            self._image_np = cv2.rotate(self._image_np, cv2.ROTATE_90_COUNTERCLOCKWISE)

        self.set_image(self._image_np)

    # --- Text box management ---

    def add_text_boxes(self, boxes: list):
        """Add TextBoxItem overlays for each TextBox."""
        for box in boxes:
            if box.is_deleted:
                continue
            item = TextBoxItem(
                box_id=box.box_id,
                rect=box.rect,
                text=box.text,
                confidence=box.confidence,
                signals=self.signals,
            )
            self._scene.addItem(item)
            self._text_box_items[box.box_id] = item

    def clear_boxes(self):
        """Remove all text box overlays."""
        for item in self._text_box_items.values():
            if item.scene():
                self._scene.removeItem(item)
        self._text_box_items.clear()

    def remove_box(self, box_id: str):
        """Remove a single text box by ID."""
        item = self._text_box_items.pop(box_id, None)
        if item and item.scene():
            self._scene.removeItem(item)

    def update_box_text(self, box_id: str, text: str, confidence: float):
        """Update the text and confidence of a specific box."""
        item = self._text_box_items.get(box_id)
        if item:
            item.set_text(text)
            item.set_confidence(confidence)

    def get_all_boxes(self) -> list:
        """Collect current state of all text boxes."""
        boxes = []
        for box_id, item in self._text_box_items.items():
            pos = item.pos()
            r = item.rect()
            box = TextBox(
                box_id=box_id,
                rect=(int(pos.x()), int(pos.y()), int(r.width()), int(r.height())),
                text=item.get_text(),
                confidence=item.get_confidence(),
            )
            boxes.append(box)
        return boxes

    def get_image_np(self) -> np.ndarray:
        """Return the current numpy image (for cropping during re-OCR)."""
        return self._image_np

    def has_image(self) -> bool:
        return self._image_np is not None

    def has_boxes(self) -> bool:
        return len(self._text_box_items) > 0

    # --- Guide line management ---

    def generate_guide_lines(self):
        """Generate vertical guide lines from the topmost row of text boxes.

        For each box in the topmost row, creates a vertical guide line
        at the box's X-center, spanning from y=0 to the image bottom edge.
        """
        from src.gui.canvas.column_guide_item import ColumnGuideItem

        self.clear_guide_lines()
        boxes = self.get_all_boxes()
        if not boxes:
            return

        img_h = self._image_np.shape[0] if self._image_np is not None else 1000
        img_w = self._image_np.shape[1] if self._image_np is not None else 1000

        # Find the topmost row by Y-center proximity
        sorted_by_y = sorted(boxes, key=lambda b: b.rect[1] + b.rect[3] / 2)
        top_y = sorted_by_y[0].rect[1] + sorted_by_y[0].rect[3] / 2

        heights = [b.rect[3] for b in boxes]
        heights.sort()
        median_h = heights[len(heights) // 2]
        threshold = max(median_h * 0.5, 5)

        first_row = []
        for b in sorted_by_y:
            y_center = b.rect[1] + b.rect[3] / 2
            if y_center - top_y <= threshold:
                first_row.append(b)
            else:
                break

        # Sort left-to-right, create a vertical guide per box
        first_row.sort(key=lambda b: b.rect[0] + b.rect[2] / 2)

        for box in first_row:
            x_center = box.rect[0] + box.rect[2] / 2
            guide = ColumnGuideItem(
                x_position=x_center,
                image_height=img_h,
                signals=self.signals,
                image_width=img_w,
            )
            self._scene.addItem(guide)
            self._guide_lines.append(guide)

    def add_guide_line(self):
        """Add a single guide line at the center of the image."""
        from src.gui.canvas.column_guide_item import ColumnGuideItem

        if self._image_np is None:
            return

        img_h, img_w = self._image_np.shape[:2]
        x_center = img_w / 2

        guide = ColumnGuideItem(
            x_position=x_center,
            image_height=img_h,
            signals=self.signals,
            image_width=img_w,
        )
        self._scene.addItem(guide)
        self._guide_lines.append(guide)

    def remove_guide_line(self, guide_id: str):
        """Remove a specific guide line by ID."""
        for guide in self._guide_lines:
            if guide.guide_id == guide_id:
                if guide.scene():
                    self._scene.removeItem(guide)
                self._guide_lines.remove(guide)
                break

    def clear_guide_lines(self):
        """Remove all guide lines."""
        for guide in self._guide_lines:
            if guide.scene():
                self._scene.removeItem(guide)
        self._guide_lines.clear()

    def get_guide_lines(self) -> list:
        """Return guide line data: [(guide_id, (x1,y1), (x2,y2)), ...]."""
        result = []
        for guide in self._guide_lines:
            pts = guide.get_line_points()
            result.append((guide.guide_id, pts[0], pts[1]))
        return result

    def has_guide_lines(self) -> bool:
        return len(self._guide_lines) > 0

    # --- Shift: hide/show all overlays ---

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Shift and not event.isAutoRepeat():
            self._set_overlays_visible(False)
            event.accept()
            return
        if event.key() == Qt.Key_Control and not event.isAutoRepeat():
            if self.has_image():
                self.viewport().setCursor(Qt.CrossCursor)
            event.accept()
            return
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            # Guard: don't intercept DEL/Backspace when editing text inline
            focus = self._scene.focusItem()
            if focus and isinstance(focus, QGraphicsProxyWidget):
                super().keyPressEvent(event)
                return
            self._delete_selected_items()
            event.accept()
            return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Shift and not event.isAutoRepeat():
            self._set_overlays_visible(True)
            event.accept()
            return
        if event.key() == Qt.Key_Control and not event.isAutoRepeat():
            self.viewport().unsetCursor()
            event.accept()
            return
        super().keyReleaseEvent(event)

    def _set_overlays_visible(self, visible: bool):
        """Show or hide all text boxes and guide lines."""
        self._boxes_hidden = not visible
        for item in self._text_box_items.values():
            item.setVisible(visible)
        for guide in self._guide_lines:
            guide.setVisible(visible)

    def _delete_selected_items(self):
        """Delete all currently selected text boxes and guide lines."""
        from src.gui.canvas.column_guide_item import ColumnGuideItem

        selected = list(self._scene.selectedItems())
        for item in selected:
            if isinstance(item, TextBoxItem):
                item._delete_self()
            elif isinstance(item, ColumnGuideItem):
                item._delete_self()

    def _on_guide_selected(self, guide_id: str, is_selected: bool):
        """Highlight text boxes that intersect the selected guide line."""
        from src.parsing.table_generator import TableGenerator

        if not is_selected:
            # Clear all highlights
            for item in self._text_box_items.values():
                item.set_highlighted(False)
            return

        # Find the guide line
        guide = None
        for g in self._guide_lines:
            if g.guide_id == guide_id:
                guide = g
                break
        if guide is None:
            return

        (x1, y1), (x2, y2) = guide.get_line_points()
        for item in self._text_box_items.values():
            pos = item.pos()
            r = item.rect()
            rx, ry = int(pos.x()), int(pos.y())
            rw, rh = int(r.width()), int(r.height())
            hit = TableGenerator._line_intersects_rect(x1, y1, x2, y2, rx, ry, rw, rh)
            item.set_highlighted(hit)

    # --- Ctrl+drag: create new box ---

    def mousePressEvent(self, event):
        if (event.button() == Qt.LeftButton
                and event.modifiers() & Qt.ControlModifier
                and self.has_image()):
            self._is_drawing = True
            self._draw_start = self.mapToScene(event.position().toPoint())
            # Create rubber band rectangle
            self._rubber_band = QGraphicsRectItem()
            self._rubber_band.setPen(QPen(QColor(255, 140, 0, 200), 2, Qt.DashLine))
            self._rubber_band.setBrush(QBrush(QColor(255, 140, 0, 40)))
            self._rubber_band.setZValue(5)
            self._scene.addItem(self._rubber_band)
            self.setDragMode(QGraphicsView.NoDrag)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._is_drawing and self._rubber_band:
            current = self.mapToScene(event.position().toPoint())
            rect = QRectF(self._draw_start, current).normalized()
            # Clamp to image bounds
            if self._pixmap_item:
                rect = rect.intersected(self._pixmap_item.boundingRect())
            self._rubber_band.setRect(rect)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._is_drawing:
            self._is_drawing = False
            self.setDragMode(QGraphicsView.ScrollHandDrag)

            if self._rubber_band:
                rect = self._rubber_band.rect()
                self._scene.removeItem(self._rubber_band)
                self._rubber_band = None

                x, y, w, h = int(rect.x()), int(rect.y()), int(rect.width()), int(rect.height())
                if w >= 10 and h >= 10:
                    self._create_manual_box(x, y, w, h)

            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _create_manual_box(self, x, y, w, h):
        """Create a new text box from manual selection."""
        box_id = str(uuid.uuid4())
        item = TextBoxItem(
            box_id=box_id,
            rect=(x, y, w, h),
            text="",
            confidence=0.0,
            signals=self.signals,
        )
        self._scene.addItem(item)
        self._text_box_items[box_id] = item
        self.signals.box_created.emit(box_id, (x, y, w, h))

    def leaveEvent(self, event):
        """Cancel drawing if mouse leaves the view."""
        if self._is_drawing:
            self._is_drawing = False
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            if self._rubber_band:
                self._scene.removeItem(self._rubber_band)
                self._rubber_band = None
        super().leaveEvent(event)

    # --- Zoom ---

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            factor = 1.15
            if event.angleDelta().y() < 0:
                factor = 1.0 / factor
            self.scale(factor, factor)
            event.accept()
        else:
            super().wheelEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._pixmap_item and not self._text_box_items:
            self.fit_in_view()
