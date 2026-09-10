"""Word (.docx) versions of the printable forms -- same content as the
matching print page (e.g. frontend/src/pages/InvoicePrintPage.tsx for
invoice_to_docx), built with python-docx so it opens as a normal,
editable Word document. Each form gets its own small function here
rather than a generic templating layer, since a one-record form's
layout is specific to what it's showing.
"""
import io

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

from app.models.billing import Invoice
from app.models.core import Company
from app.models.customers import Customer


def invoice_to_docx(invoice: Invoice, customer: Customer, company: Company) -> bytes:
    doc = Document()

    header = doc.add_paragraph()
    header.add_run(company.name).bold = True
    if company.address:
        doc.add_paragraph(company.address)
    if company.phone:
        doc.add_paragraph(f"Tel: {company.phone}")
    if company.website:
        doc.add_paragraph(company.website)
    if company.uen:
        doc.add_paragraph(f"Business Reg# {company.uen}")
    if company.gst_registration_no:
        doc.add_paragraph(f"GST Reg# {company.gst_registration_no}")

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("TAX INVOICE")
    run.bold = True
    run.font.size = Pt(16)

    meta = doc.add_paragraph()
    meta.add_run(f"{invoice.invoice_number}\n").bold = True
    meta.add_run(f"Issued: {invoice.issued_at.date().isoformat()}\n")
    if invoice.due_date:
        meta.add_run(f"Due: {invoice.due_date.isoformat()}\n")

    doc.add_paragraph().add_run("Bill To").italic = True
    bill_to = doc.add_paragraph()
    bill_to.add_run(customer.name + "\n").bold = True
    if customer.uen:
        bill_to.add_run(f"UEN: {customer.uen}\n")
    if customer.contact_person:
        bill_to.add_run(f"Contact Person: {customer.contact_person}\n")
    if customer.billing_email:
        bill_to.add_run(f"Contact Email: {customer.billing_email}\n")
    if customer.phone:
        bill_to.add_run(f"Contact No: {customer.phone}\n")
    address = ", ".join(
        filter(None, [customer.address_line1, customer.address_line2, customer.address_city, customer.address_country])
    )
    if address:
        bill_to.add_run(address)

    table = doc.add_table(rows=1, cols=4)
    table.style = "Light Grid Accent 1"
    hdr = table.rows[0].cells
    hdr[0].text = "Description"
    hdr[1].text = "Qty"
    hdr[2].text = "Unit Price ($)"
    hdr[3].text = "Amount ($)"
    row = table.add_row().cells
    row[0].text = invoice.description
    row[1].text = "1.00"
    row[2].text = f"{invoice.amount_sgd:.2f}"
    row[3].text = f"{invoice.amount_sgd:.2f}"

    doc.add_paragraph()
    totals = doc.add_table(rows=3, cols=2)
    for i, (label, value) in enumerate(
        [
            ("Subtotal", f"{invoice.amount_sgd:.2f}"),
            (f"Tax {invoice.gst_rate}% ({invoice.tax_code})", f"{invoice.gst_amount_sgd:.2f}"),
            ("Grand Total (SGD)", f"{invoice.total_amount_sgd:.2f}"),
        ]
    ):
        cells = totals.rows[i].cells
        cells[0].text = label
        cells[1].text = value
        if label.startswith("Grand Total"):
            for cell in cells:
                for p in cell.paragraphs:
                    for r in p.runs:
                        r.bold = True

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
