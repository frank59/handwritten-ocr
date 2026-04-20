"""Generate table structure from TextBox positions using coordinate clustering.

Groups text boxes into rows by Y-coordinate proximity, then determines
column assignments either by X-coordinate clustering or by user-placed
column guide lines.
"""

import math
import logging
from src.parsing.data_models import TextBox, ParsedDocument, ParsedRow

logger = logging.getLogger(__name__)


class TableGenerator:
    """Converts a list of TextBoxes into a ParsedDocument table structure."""

    def generate(self, boxes: list, source_path: str = "") -> ParsedDocument:
        """Generate a table from text boxes using 2D coordinate clustering.

        Args:
            boxes: list of TextBox from the canvas.
            source_path: original image path for metadata.

        Returns:
            ParsedDocument with inferred rows and columns.
        """
        # Filter out deleted / empty boxes
        active = [b for b in boxes if not b.is_deleted and b.text.strip()]
        if not active:
            return ParsedDocument(source_path=source_path)

        # 1. Cluster into rows by Y center
        rows_of_boxes = self._cluster_rows(active)

        # 2. Sort each row by X
        for row in rows_of_boxes:
            row.sort(key=lambda b: b.rect[0])

        # 3. Determine column positions from all rows
        col_centers = self._determine_columns(rows_of_boxes)
        num_cols = len(col_centers)

        if num_cols == 0:
            return ParsedDocument(source_path=source_path)

        # 4. Build headers
        headers = [f"\u5217{i + 1}" for i in range(num_cols)]

        # 5. Assign each box to a column and build rows
        parsed_rows = []
        for row_boxes in rows_of_boxes:
            fields = {h: "" for h in headers}
            min_conf = 1.0

            for box in row_boxes:
                col_idx = self._find_nearest_column(box, col_centers)
                col_name = headers[col_idx]
                # If column already occupied, append with space
                if fields[col_name]:
                    fields[col_name] += " " + box.text
                else:
                    fields[col_name] = box.text
                min_conf = min(min_conf, box.confidence)

            parsed_rows.append(ParsedRow(fields=fields, confidence=min_conf))

        logger.info("Generated table: %d rows x %d cols from %d boxes",
                     len(parsed_rows), num_cols, len(active))

        return ParsedDocument(
            input_type="generated",
            headers=headers,
            rows=parsed_rows,
            source_path=source_path,
        )

    def _cluster_rows(self, boxes: list) -> list:
        """Cluster boxes into rows by Y-center proximity.

        Uses a gap-based approach: sort by Y center, then split whenever
        the gap between consecutive Y centers exceeds a dynamic threshold.

        Returns:
            List of lists of TextBox, each sub-list is one row (top to bottom).
        """
        if not boxes:
            return []

        # Compute median height for dynamic threshold
        heights = [b.rect[3] for b in boxes]
        heights.sort()
        median_h = heights[len(heights) // 2]

        # Threshold: half of median box height
        threshold = max(median_h * 0.5, 5)

        # Sort by Y center
        sorted_boxes = sorted(boxes, key=lambda b: b.rect[1] + b.rect[3] / 2)

        rows = [[sorted_boxes[0]]]
        for box in sorted_boxes[1:]:
            current_y = box.rect[1] + box.rect[3] / 2
            prev_y = rows[-1][-1].rect[1] + rows[-1][-1].rect[3] / 2
            if current_y - prev_y > threshold:
                rows.append([box])
            else:
                rows[-1].append(box)

        return rows

    def _determine_columns(self, rows_of_boxes: list) -> list:
        """Determine column center X-positions from all boxes.

        Collects X-centers from all boxes, clusters them, and returns
        sorted column center positions.

        Returns:
            Sorted list of column center X coordinates.
        """
        # Collect all (x_center, width) pairs
        all_x_centers = []
        for row in rows_of_boxes:
            for box in row:
                x_center = box.rect[0] + box.rect[2] / 2
                all_x_centers.append(x_center)

        if not all_x_centers:
            return []

        # Compute median width for threshold
        all_widths = []
        for row in rows_of_boxes:
            for box in row:
                all_widths.append(box.rect[2])
        all_widths.sort()
        median_w = all_widths[len(all_widths) // 2]

        # Threshold: half of median width
        threshold = max(median_w * 0.5, 20)

        # Sort and cluster
        all_x_centers.sort()
        clusters = [[all_x_centers[0]]]
        for xc in all_x_centers[1:]:
            cluster_mean = sum(clusters[-1]) / len(clusters[-1])
            if xc - cluster_mean > threshold:
                clusters.append([xc])
            else:
                clusters[-1].append(xc)

        # Return mean of each cluster
        col_centers = [sum(c) / len(c) for c in clusters]
        return col_centers

    def _find_nearest_column(self, box: TextBox, col_centers: list) -> int:
        """Find the column index closest to this box's X center."""
        x_center = box.rect[0] + box.rect[2] / 2
        min_dist = float('inf')
        best_idx = 0
        for i, cc in enumerate(col_centers):
            dist = abs(x_center - cc)
            if dist < min_dist:
                min_dist = dist
                best_idx = i
        return best_idx

    # --- Guide-line-based generation ---

    def generate_with_guides(self, boxes: list, guide_lines: list,
                             source_path: str = "") -> ParsedDocument:
        """Generate a table using user-placed column guide lines.

        Column assignment uses strict line-segment / rectangle intersection.
        Within each column, boxes are sorted top-to-bottom by Y-center,
        and each box maps to exactly one cell.

        Args:
            boxes: list of TextBox from the canvas.
            guide_lines: list of (guide_id, (x1,y1), (x2,y2)) tuples.
            source_path: original image path for metadata.

        Returns:
            ParsedDocument with columns defined by guide lines.
        """
        active = [b for b in boxes if not b.is_deleted]
        if not active or not guide_lines:
            logger.warning("[guide] 跳过: active=%d, guides=%d", len(boxes), len(guide_lines) if guide_lines else 0)
            return ParsedDocument(source_path=source_path)

        # Sort guide lines left-to-right by average X
        sorted_guides = sorted(guide_lines, key=lambda g: (g[1][0] + g[2][0]) / 2)
        num_cols = len(sorted_guides)
        headers = [f"\u5217{i + 1}" for i in range(num_cols)]

        logger.info("[guide] 生成模式: %d条辅助线, %d个矩形", num_cols, len(active))
        for i, (gid, p1, p2) in enumerate(sorted_guides):
            logger.debug("[guide] guide[%d]: (%.1f,%.1f)-(%.1f,%.1f)", i, p1[0], p1[1], p2[0], p2[1])

        # 1. Assign boxes to columns by strict intersection
        #    columns[col_idx] = list of TextBox
        columns = [[] for _ in range(num_cols)]
        unassigned = []
        for box in active:
            rx, ry, rw, rh = box.rect
            matched = False
            for col_idx, (_, p1, p2) in enumerate(sorted_guides):
                hit = self._line_intersects_rect(p1[0], p1[1], p2[0], p2[1],
                                                 rx, ry, rw, rh)
                if hit:
                    columns[col_idx].append(box)
                    logger.warning("[guide]   box '%s' rect=(%d,%d,%d,%d) -> col%d",
                                   box.text[:10], rx, ry, rw, rh, col_idx)
                    matched = True
                    break  # each box belongs to at most one column
            if not matched:
                unassigned.append(box)
                logger.warning("[guide]   box '%s' rect=(%d,%d,%d,%d) -> NO MATCH",
                               box.text[:10], rx, ry, rw, rh)

        for i, col in enumerate(columns):
            logger.warning("[guide] col%d: %d boxes", i, len(col))
        if unassigned:
            logger.warning("[guide] unassigned: %d boxes", len(unassigned))

        # 2. Sort each column top-to-bottom by Y-center
        for col in columns:
            col.sort(key=lambda b: b.rect[1] + b.rect[3] / 2)

        # 3. Build rows by index alignment: Nth box in each column = row N
        num_rows = max((len(col) for col in columns), default=0)
        if num_rows == 0:
            logger.warning("[guide] 没有任何矩形与辅助线相交！")
            return ParsedDocument(source_path=source_path)

        parsed_rows = []
        for row_idx in range(num_rows):
            fields = {h: "" for h in headers}
            min_conf = 1.0
            for col_idx, col in enumerate(columns):
                if row_idx < len(col):
                    box = col[row_idx]
                    fields[headers[col_idx]] = box.text
                    min_conf = min(min_conf, box.confidence)
            parsed_rows.append(ParsedRow(fields=fields, confidence=min_conf))

        total_assigned = sum(len(col) for col in columns)
        logger.info("Generated table with guides: %d rows x %d cols from %d boxes",
                     len(parsed_rows), num_cols, total_assigned)

        return ParsedDocument(
            input_type="generated",
            headers=headers,
            rows=parsed_rows,
            source_path=source_path,
        )

    @staticmethod
    def _line_intersects_rect(x1, y1, x2, y2, rx, ry, rw, rh):
        """Check if line segment (x1,y1)-(x2,y2) intersects axis-aligned rect.

        Uses the Liang-Barsky clipping algorithm.

        Args:
            x1, y1, x2, y2: line segment endpoints.
            rx, ry, rw, rh: rectangle (left, top, width, height).

        Returns:
            True if the segment passes through the rectangle.
        """
        dx = x2 - x1
        dy = y2 - y1
        left = rx
        right = rx + rw
        top = ry
        bottom = ry + rh

        p = [-dx, dx, -dy, dy]
        q = [x1 - left, right - x1, y1 - top, bottom - y1]

        t_min = 0.0
        t_max = 1.0

        for i in range(4):
            if abs(p[i]) < 1e-10:
                # Line is parallel to this edge
                if q[i] < 0:
                    return False  # outside and parallel
            else:
                t = q[i] / p[i]
                if p[i] < 0:
                    t_min = max(t_min, t)
                else:
                    t_max = min(t_max, t)
                if t_min > t_max:
                    return False

        return True

    @staticmethod
    def _point_to_line_distance(px, py, x1, y1, x2, y2):
        """Perpendicular distance from point (px,py) to line (x1,y1)-(x2,y2)."""
        dx = x2 - x1
        dy = y2 - y1
        length_sq = dx * dx + dy * dy
        if length_sq < 1e-6:
            return math.sqrt((px - x1) ** 2 + (py - y1) ** 2)
        numerator = abs(dy * px - dx * py + x2 * y1 - y2 * x1)
        return numerator / math.sqrt(length_sq)
