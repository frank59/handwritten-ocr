"""Interactive column guide line for table column definition.

Each guide line has two draggable endpoint handles (top and bottom).
By angling the line, users can match tilted column layouts.
Text boxes are assigned to the nearest guide line during table generation.
"""

import math
import uuid

from PySide6.QtWidgets import (
    QGraphicsLineItem, QGraphicsEllipseItem, QGraphicsItem, QMenu,
)
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QColor, QPen, QBrush, QCursor, QPainterPath, QPainterPathStroker

GUIDE_COLOR = QColor(0, 180, 80, 160)
HANDLE_COLOR = QColor(0, 200, 100, 200)
GUIDE_COLOR_SELECTED = QColor(220, 50, 50, 200)
HANDLE_COLOR_SELECTED = QColor(240, 80, 80, 220)
HANDLE_RADIUS = 6


class GuideEndpointHandle(QGraphicsEllipseItem):
    """Draggable circle at the endpoint of a guide line."""

    def __init__(self, x, y, parent_guide, max_x, max_y):
        r = HANDLE_RADIUS
        super().__init__(-r, -r, r * 2, r * 2, parent_guide)
        self.setPos(x, y)

        self._parent_guide = parent_guide
        self._max_x = max_x
        self._max_y = max_y

        self.setBrush(QBrush(HANDLE_COLOR))
        self.setPen(QPen(QColor(0, 120, 50, 200), 1))
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setCursor(QCursor(Qt.SizeAllCursor))
        self.setAcceptHoverEvents(True)
        self.setZValue(8)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange:
            # Clamp position to image bounds
            new_pos = QPointF(value)
            new_pos.setX(max(0.0, min(new_pos.x(), self._max_x)))
            new_pos.setY(max(0.0, min(new_pos.y(), self._max_y)))
            return new_pos
        if change == QGraphicsItem.ItemPositionHasChanged:
            self._parent_guide.update_line()
        return super().itemChange(change, value)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self._parent_guide.notify_drag_finished()


class ColumnGuideItem(QGraphicsLineItem):
    """A column guide line with two draggable endpoints."""

    def __init__(self, x_position, image_height, signals, image_width=None, parent=None):
        """
        Args:
            x_position: Initial X center of the guide line.
            image_height: Image height for initial vertical span.
            signals: Shared TextBoxSignals for deletion events.
            image_width: Image width for endpoint clamping.
        """
        super().__init__(parent)
        self.guide_id = str(uuid.uuid4())
        self._signals = signals

        max_x = float(image_width) if image_width is not None else 1e6
        max_y = float(image_height)

        # Visual
        pen = QPen(GUIDE_COLOR, 2, Qt.DashLine)
        self.setPen(pen)
        self.setZValue(2)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

        # Create endpoint handles (relative to this item's coordinate system)
        self._top_handle = GuideEndpointHandle(x_position, 0, self, max_x, max_y)
        self._bottom_handle = GuideEndpointHandle(x_position, image_height, self, max_x, max_y)

        self.update_line()

    def boundingRect(self):
        """Expand bounding rect to match the wider shape() hit area."""
        return self.shape().boundingRect()

    def shape(self):
        """Widen hit-test area to ~12px for easier clicking."""
        path = QPainterPath()
        line = self.line()
        path.moveTo(line.p1())
        path.lineTo(line.p2())
        stroker = QPainterPathStroker()
        stroker.setWidth(12)
        return stroker.createStroke(path)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedHasChanged:
            selected = bool(value)
            self._apply_visual_state(selected)
            self._signals.guide_selected.emit(self.guide_id, selected)
        return super().itemChange(change, value)

    def _apply_visual_state(self, selected):
        """Switch line and handle colors between normal (green) and selected (red)."""
        if selected:
            self.setPen(QPen(GUIDE_COLOR_SELECTED, 2, Qt.SolidLine))
            self._top_handle.setBrush(QBrush(HANDLE_COLOR_SELECTED))
            self._bottom_handle.setBrush(QBrush(HANDLE_COLOR_SELECTED))
        else:
            self.setPen(QPen(GUIDE_COLOR, 2, Qt.DashLine))
            self._top_handle.setBrush(QBrush(HANDLE_COLOR))
            self._bottom_handle.setBrush(QBrush(HANDLE_COLOR))

    def update_line(self):
        """Recompute line geometry from endpoint positions."""
        p1 = self._top_handle.pos()
        p2 = self._bottom_handle.pos()
        self.setLine(p1.x(), p1.y(), p2.x(), p2.y())

    def notify_drag_finished(self):
        """Called by endpoint handle after drag completes."""
        if self.isSelected():
            self._signals.guide_selected.emit(self.guide_id, True)

    def get_line_points(self):
        """Return endpoint positions as ((x1,y1), (x2,y2))."""
        p1 = self._top_handle.pos()
        p2 = self._bottom_handle.pos()
        return ((p1.x(), p1.y()), (p2.x(), p2.y()))

    def get_average_x(self):
        """Return average X position (for left-to-right column ordering)."""
        p1 = self._top_handle.pos()
        p2 = self._bottom_handle.pos()
        return (p1.x() + p2.x()) / 2

    def point_to_line_distance(self, px, py):
        """Compute perpendicular distance from point (px, py) to this guide line.

        Uses the standard point-to-line distance formula:
        dist = |((y2-y1)*px - (x2-x1)*py + x2*y1 - y2*x1)| / sqrt((y2-y1)^2 + (x2-x1)^2)
        """
        p1 = self._top_handle.pos()
        p2 = self._bottom_handle.pos()
        x1, y1 = p1.x(), p1.y()
        x2, y2 = p2.x(), p2.y()

        dx = x2 - x1
        dy = y2 - y1
        length_sq = dx * dx + dy * dy

        if length_sq < 1e-6:
            # Degenerate: both endpoints at same position
            return math.sqrt((px - x1) ** 2 + (py - y1) ** 2)

        numerator = abs(dy * px - dx * py + x2 * y1 - y2 * x1)
        denominator = math.sqrt(length_sq)
        return numerator / denominator

    def contextMenuEvent(self, event):
        if not self.isSelected():
            if self.scene():
                self.scene().clearSelection()
            self.setSelected(True)
        menu = QMenu()
        delete_action = menu.addAction("删除辅助线")
        action = menu.exec(event.screenPos())
        if action == delete_action:
            self._delete_self()

    def _delete_self(self):
        """Emit deletion signal (ImageCanvas handles scene removal)."""
        self._signals.guide_deleted.emit(self.guide_id)
