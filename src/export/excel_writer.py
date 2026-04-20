"""Excel export using Pandas and OpenPyXL."""

import os
from datetime import datetime
import logging

import pandas as pd
from openpyxl.utils import get_column_letter

from src.parsing.data_models import ParsedDocument

logger = logging.getLogger(__name__)


class ExportError(Exception):
    """Raised when Excel export fails."""
    pass


def write_excel(doc: ParsedDocument, file_path: str) -> None:
    """Write ParsedDocument to an Excel file.

    Args:
        doc: The parsed and corrected document data.
        file_path: Output .xlsx file path.

    Raises:
        ExportError: If writing fails.
    """
    try:
        # Build data rows as list of dicts
        data = []
        for row in doc.rows:
            row_dict = {}
            for header in doc.headers:
                row_dict[header] = row.fields.get(header, "")
            data.append(row_dict)

        df = pd.DataFrame(data, columns=doc.headers)

        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='识别结果')

            # Auto-adjust column widths
            worksheet = writer.sheets['识别结果']
            for i, header in enumerate(doc.headers, 1):
                col_letter = get_column_letter(i)
                # Calculate max width from header and data
                max_len = len(str(header))
                for row in doc.rows:
                    val = row.fields.get(header, "")
                    # Account for Chinese characters (roughly 2x width)
                    char_len = sum(2 if ord(c) > 127 else 1 for c in str(val))
                    max_len = max(max_len, char_len)
                # Set width with padding
                worksheet.column_dimensions[col_letter].width = min(max_len + 4, 50)

    except PermissionError:
        raise ExportError(
            f"无法保存文件，请检查文件路径权限或关闭已打开的 Excel 文件:\n{file_path}"
        )
    except Exception as e:
        raise ExportError(f"导出 Excel 失败: {e}")
