"""Editable table widget for displaying and correcting OCR results."""

from PySide6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from config import LOW_CONFIDENCE_THRESHOLD
from src.parsing.data_models import ParsedDocument, ParsedRow


# Color for low-confidence cells
LOW_CONFIDENCE_COLOR = QColor(255, 220, 220)  # light red


class EditableTableWidget(QTableWidget):
    """QTableWidget that displays ParsedDocument data with editing support."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._headers = []
        self._row_confidences = []

        # Enable editing on double-click
        self.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setAlternatingRowColors(True)

        # Header stretches to fill
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.verticalHeader().setVisible(True)

    def load_data(self, doc: ParsedDocument) -> None:
        """Populate table from ParsedDocument."""
        self._headers = list(doc.headers)
        self._row_confidences = []

        self.clear()
        self.setColumnCount(len(self._headers))
        self.setHorizontalHeaderLabels(self._headers)
        self.setRowCount(len(doc.rows))

        for row_idx, parsed_row in enumerate(doc.rows):
            self._row_confidences.append(parsed_row.confidence)
            for col_idx, header in enumerate(self._headers):
                value = parsed_row.fields.get(header, "")
                item = QTableWidgetItem(value)

                # Highlight low-confidence cells
                if parsed_row.confidence < LOW_CONFIDENCE_THRESHOLD:
                    item.setBackground(LOW_CONFIDENCE_COLOR)

                self.setItem(row_idx, col_idx, item)

        # Auto-resize columns to content
        self.resizeColumnsToContents()

    def get_data(self) -> ParsedDocument:
        """Read current table state back into a ParsedDocument."""
        rows = []
        for row_idx in range(self.rowCount()):
            fields = {}
            for col_idx, header in enumerate(self._headers):
                item = self.item(row_idx, col_idx)
                fields[header] = item.text() if item else ""

            confidence = 1.0
            if row_idx < len(self._row_confidences):
                confidence = self._row_confidences[row_idx]

            rows.append(ParsedRow(fields=fields, confidence=confidence))

        return ParsedDocument(
            headers=list(self._headers),
            rows=rows,
        )

    def add_row(self) -> None:
        """Insert a new empty row below current selection."""
        current_row = self.currentRow()
        insert_at = current_row + 1 if current_row >= 0 else self.rowCount()

        self.insertRow(insert_at)
        for col_idx in range(self.columnCount()):
            self.setItem(insert_at, col_idx, QTableWidgetItem(""))

        self._row_confidences.insert(insert_at, 1.0)
        self.setCurrentCell(insert_at, 0)

    def delete_row(self) -> None:
        """Remove selected row(s)."""
        selected_rows = sorted(set(idx.row() for idx in self.selectedIndexes()), reverse=True)
        for row_idx in selected_rows:
            self.removeRow(row_idx)
            if row_idx < len(self._row_confidences):
                self._row_confidences.pop(row_idx)

    def get_headers(self) -> list:
        return list(self._headers)
