"""Shared export helpers -- CSV and Excel for list/report pages, so
every module's "export" button uses the same two small functions
instead of each one reinventing serialization. Word (.docx) is handled
per-document in app/services/docx_forms.py, since a single-record form
(an invoice, a receipt) needs its own layout rather than a generic
row/column table.
"""
import csv
import io

import openpyxl


def rows_to_csv(fieldnames: list[str], rows: list[dict]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buf.getvalue()


def rows_to_excel(fieldnames: list[str], rows: list[dict], *, sheet_name: str = "Sheet1") -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet_name[:31]  # Excel sheet-name length limit
    ws.append(fieldnames)
    for cell in ws[1]:
        cell.font = openpyxl.styles.Font(bold=True)
    for row in rows:
        ws.append([row.get(f, "") for f in fieldnames])
    for col in ws.columns:
        width = max((len(str(c.value)) for c in col if c.value is not None), default=10)
        ws.column_dimensions[col[0].column_letter].width = min(max(width + 2, 10), 50)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
