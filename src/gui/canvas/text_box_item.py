"""Interactive text box overlay for the image canvas.

Each TextBoxItem represents one detected text region, rendered as a
semi-transparent rectangle with recognized text overlaid on the image.
Supports drag, resize, double-click editing, and deletion.
"""

from PySide6.QtWidgets import (
    QGraphicsRectItem, QGraphicsItem, QGraphicsTextItem,
    QGraphicsProxyWidget, QLineEdit, QMenu,
)
from PySide6.QtCore import Qt, QRectF, QPointF, QTimer
from PySide6.QtGui import (
    QColor, QPen, QBrush, QPainter, QFont, QCursor, QPainterPath,
)

from config import LOW_CONFIDENCE_THRESHOLD

# Colors
FILL_NORMAL = QColor(70, 130, 180, 60)
FILL_LOW_CONF = QColor(220, 80, 60, 60)
FILL_HOVER = QColor(70, 130, 180, 90)
FILL_EDITED = QColor(100, 200, 100, 70)
BORDER_NORMAL = QColor(50, 100, 150, 180)
BORDER_SELECTED = QColor(255, 140, 0, 220)
BORDER_HIGHLIGHTED = QColor(220, 50, 50, 200)
TEXT_COLOR = QColor(0, 0, 0, 220)
HANDLE_COLOR = QColor(255, 140, 0, 200)

HANDLE_SIZE = 8


class ResizeHandle(QGraphicsRectItem):
    """Small square handle for resizing a TextBoxItem."""

    def __init__(self, cursor_shape, parent=None):
        super().__init__(-HANDLE_SIZE / 2, -HANDLE_SIZE / 2, HANDLE_SIZE, HANDLE_SIZE, parent)
        self.setBrush(QBrush(HANDLE_COLOR))
        self.setPen(QPen(Qt.NoPen))
        self.setFlag(QGraphicsItem.ItemIsMovable, False)
        self.setCursor(QCursor(cursor_shape))
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.NoButton)  # Let clicks pass through to parent
        self.setVisible(False)
        self.setZValue(10)


class TextBoxItem(QGraphicsRectItem):
    """Interactive overlay for a single detected text region."""

    def __init__(self, box_id, rect, text, confidence, signals, parent=None):
        """
        Args:
            box_id: Unique identifier for this box.
            rect: (x, y, w, h) in image pixel coordinates.
            text: Recognized text content.
            confidence: OCR confidence 0-1.
            signals: Shared TextBoxSignals instance.
        """
        x, y, w, h = rect
        super().__init__(0, 0, w, h, parent)
        self.setPos(x, y)

        self.box_id = box_id
        self._text = text
        self._confidence = confidence
        self._signals = signals
        self._is_editing = False
        self._edit_proxy = None
        self._is_hovering = False
        self._is_resizing = False
        self._is_edited = False
        self._is_highlighted = False
        self._resize_handle = None
        self._resize_start_rect = None
        self._resize_start_pos = None

        # Qt flags
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)
        self.setZValue(1)

        # Create resize handles
        self._handles = self._create_handles()
        self._update_handle_positions()

    def _create_handles(self):
        cursors = [
            Qt.SizeFDiagCursor, Qt.SizeVerCursor, Qt.SizeBDiagCursor,
            Qt.SizeHorCursor,                       Qt.SizeHorCursor,
            Qt.SizeBDiagCursor, Qt.SizeVerCursor, Qt.SizeFDiagCursor,
        ]
        handles = []
        for cursor in cursors:
            h = ResizeHandle(cursor, self)
            handles.append(h)
        return handles

    def _update_handle_positions(self):
        r = self.rect()
        positions = [
            r.topLeft(), QPointF(r.center().x(), r.top()), r.topRight(),
            QPointF(r.left(), r.center().y()),              QPointF(r.right(), r.center().y()),
            r.bottomLeft(), QPointF(r.center().x(), r.bottom()), r.bottomRight(),
        ]
        for handle, pos in zip(self._handles, positions):
            handle.setPos(pos)

    def _show_handles(self, visible):
        for h in self._handles:
            h.setVisible(visible)

    def boundingRect(self):
        """Expand bounding rect when selected to include resize handles outside edges."""
        r = self.rect()
        if self.isSelected():
            margin = HANDLE_SIZE / 2 + 4  # handle radius + hit padding
            return r.adjusted(-margin, -margin, margin, margin)
        return r

    def shape(self):
        """Expand hit-test area when selected to cover resize handle regions."""
        path = QPainterPath()
        if self.isSelected():
            margin = HANDLE_SIZE / 2 + 4
            path.addRect(self.rect().adjusted(-margin, -margin, margin, margin))
        else:
            path.addRect(self.rect())
        return path

    # --- Painting ---

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing)

        # Fill
        if self._is_hovering and not self.isSelected():
            fill = FILL_HOVER
        elif self._is_edited:
            fill = FILL_EDITED
        elif self._confidence < LOW_CONFIDENCE_THRESHOLD:
            fill = FILL_LOW_CONF
        else:
            fill = FILL_NORMAL

        painter.setBrush(QBrush(fill))

        # Border
        if self.isSelected():
            pen = QPen(BORDER_SELECTED, 2)
        elif self._is_highlighted:
            pen = QPen(BORDER_HIGHLIGHTED, 2)
        else:
            pen = QPen(BORDER_NORMAL, 1.5)
        painter.setPen(pen)
        painter.drawRect(self.rect())

        # Text — adaptive font size based on box height
        if self._text and not self._is_editing:
            painter.setPen(TEXT_COLOR)
            box_h = self.rect().height()
            font_pt = max(10, min(int(box_h * 0.45), 28))
            font = QFont()
            font.setPointSize(font_pt)
            painter.setFont(font)
            text_rect = self.rect().adjusted(2, 2, -2, -2)
            painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter | Qt.TextWordWrap, self._text)

    # --- Hover ---

    def hoverEnterEvent(self, event):
        self._is_hovering = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self._is_hovering = False
        self.update()
        super().hoverLeaveEvent(event)

    # --- Selection ---

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedHasChanged:
            self._show_handles(bool(value))
        if change == QGraphicsItem.ItemPositionHasChanged:
            self._notify_moved()
        return super().itemChange(change, value)

    def _notify_moved(self):
        """Emit box_resized after drag (position change = effective rect change)."""
        if not self._is_resizing:
            self._emit_resize_signal()

    def _emit_resize_signal(self):
        new_rect = self._get_image_rect()
        self._signals.box_resized.emit(self.box_id, new_rect)

    def _get_image_rect(self):
        """Get current rect in image coordinates as (x, y, w, h)."""
        pos = self.pos()
        r = self.rect()
        return (int(pos.x()), int(pos.y()), int(r.width()), int(r.height()))

    # --- Mouse events for resize ---

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.isSelected():
            handle_idx = self._hit_handle(event.pos())
            if handle_idx is not None:
                self._is_resizing = True
                self._resize_handle = handle_idx
                self._resize_start_rect = QRectF(self.rect())
                self._resize_start_pos = event.scenePos()
                self._resize_start_item_pos = QPointF(self.pos())
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._is_resizing:
            delta = event.scenePos() - self._resize_start_pos
            self._apply_resize(delta)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._is_resizing:
            self._is_resizing = False
            self._resize_handle = None
            self._update_handle_positions()
            # Emit resize signal for re-OCR
            self._emit_resize_signal()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _hit_handle(self, local_pos):
        """Check if local_pos hits any resize handle. Returns handle index or None."""
        for i, h in enumerate(self._handles):
            hr = h.mapRectToParent(h.rect())
            if hr.adjusted(-4, -4, 4, 4).contains(local_pos):
                return i
        return None

    def _apply_resize(self, delta):
        """Apply resize based on which handle is being dragged."""
        r = QRectF(self._resize_start_rect)
        dx, dy = delta.x(), delta.y()
        idx = self._resize_handle

        # 0=TL, 1=T, 2=TR, 3=L, 4=R, 5=BL, 6=B, 7=BR
        if idx in (0, 3, 5):  # left edge
            r.setLeft(r.left() + dx)
        if idx in (2, 4, 7):  # right edge
            r.setRight(r.right() + dx)
        if idx in (0, 1, 2):  # top edge
            r.setTop(r.top() + dy)
        if idx in (5, 6, 7):  # bottom edge
            r.setBottom(r.bottom() + dy)

        # Enforce minimum size
        if r.width() < 20:
            r.setWidth(20)
        if r.height() < 10:
            r.setHeight(10)

        # Update position and rect (use saved start pos to avoid cumulative drift)
        self.prepareGeometryChange()
        self.setPos(self._resize_start_item_pos.x() + r.x(),
                    self._resize_start_item_pos.y() + r.y())
        self.setRect(0, 0, r.width(), r.height())
        self._update_handle_positions()

    # --- Double-click to edit ---

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._start_editing()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def _start_editing(self):
        if self._is_editing:
            return
        self._is_editing = True

        box_h = self.rect().height()
        font_px = max(14, min(int(box_h * 0.45 * 1.33), 36))

        edit = QLineEdit()
        edit.setText(self._text)
        edit.setStyleSheet(
            f"background: white; color: black; border: 2px solid #FF8C00;"
            f" padding: 2px; font-size: {font_px}px;"
        )
        edit.selectAll()

        proxy = QGraphicsProxyWidget(self)
        proxy.setWidget(edit)
        proxy.setPos(0, 0)
        r = self.rect()
        edit.setFixedWidth(max(int(r.width()), 80))
        edit.setFixedHeight(max(int(r.height()), 24))
        proxy.setZValue(20)

        edit.editingFinished.connect(self._finish_editing)
        edit.setFocus()

        self._edit_proxy = proxy

    def _finish_editing(self):
        if not self._is_editing or not self._edit_proxy:
            return

        # Guard against re-entrant calls: set flags BEFORE any cleanup
        proxy = self._edit_proxy
        self._edit_proxy = None
        self._is_editing = False

        widget = proxy.widget()
        new_text = widget.text().strip() if widget else self._text

        # Disconnect signal to prevent re-entrant trigger during removal
        if widget:
            try:
                widget.editingFinished.disconnect(self._finish_editing)
            except RuntimeError:
                pass

        # Schedule safe cleanup via deleteLater instead of immediate removal
        proxy.setParentItem(None)
        proxy.deleteLater()

        if new_text != self._text:
            self._text = new_text
            self._is_edited = True
            self._signals.text_edited.emit(self.box_id, new_text)

        self.update()

    # --- Context menu / Delete ---

    def contextMenuEvent(self, event):
        menu = QMenu()
        delete_action = menu.addAction("删除此区域")
        reocr_action = menu.addAction("重新识别")
        action = menu.exec(event.screenPos())
        if action == delete_action:
            self._delete_self()
        elif action == reocr_action:
            self._emit_resize_signal()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace) and not self._is_editing:
            self._delete_self()
            event.accept()
            return
        super().keyPressEvent(event)

    def _delete_self(self):
        self._signals.box_deleted.emit(self.box_id)
        if self.scene():
            self.scene().removeItem(self)

    # --- Public API ---

    def get_text(self):
        return self._text

    def set_text(self, text):
        self._text = text
        self.update()

    def get_confidence(self):
        return self._confidence

    def set_confidence(self, conf):
        self._confidence = conf
        self.update()

    def set_highlighted(self, highlighted: bool):
        if self._is_highlighted != highlighted:
            self._is_highlighted = highlighted
            self.update()

    def reset_editing_state(self):
        """Clear selection, resize handles, and resizing flags after re-recognition.

        Called automatically by the canvas after a box resize triggers re-OCR.
        """
        self.setSelected(False)
        self._is_resizing = False
        self._resize_handle = None
        self._is_edited = False
        self._is_editing = False
        if self._edit_proxy is not None:
            proxy = self._edit_proxy
            self._edit_proxy = None
            widget = proxy.widget()
            if widget:
                try:
                    widget.editingFinished.disconnect(self._finish_editing)
                except RuntimeError:
                    pass
                proxy.setParentItem(None)
                proxy.deleteLater()
        self._show_handles(False)
        self.update()
