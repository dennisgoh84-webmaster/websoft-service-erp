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
from app.models.payables import Supplier, SupplierPayment
from app.models.payments import Payment
from app.models.quotations import Quotation


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


def quotation_to_docx(quotation: Quotation, customer: Customer, company: Company) -> bytes:
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
    run = title.add_run("QUOTATION")
    run.bold = True
    run.font.size = Pt(16)

    meta = doc.add_paragraph()
    meta.add_run(f"{quotation.quotation_number}\n").bold = True
    meta.add_run(f"Date: {quotation.quotation_date.isoformat()}\n")
    if quotation.valid_until:
        meta.add_run(f"Valid Until: {quotation.valid_until.isoformat()}\n")

    doc.add_paragraph().add_run("To").italic = True
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

    table = doc.add_table(rows=1, cols=5)
    table.style = "Light Grid Accent 1"
    hdr = table.rows[0].cells
    hdr[0].text = "Description"
    hdr[1].text = "UoM"
    hdr[2].text = "Qty"
    hdr[3].text = "Unit Price ($)"
    hdr[4].text = "Amount ($)"
    for line in quotation.lines:
        row = table.add_row().cells
        row[0].text = line.description
        row[1].text = line.unit_of_measure or ""
        row[2].text = f"{float(line.quantity):.2f}"
        row[3].text = f"{float(line.unit_price_sgd):.2f}"
        row[4].text = f"{float(line.line_total_sgd):.2f}"

    doc.add_paragraph()
    totals = doc.add_table(rows=3, cols=2)
    for i, (label, value) in enumerate(
        [
            ("Subtotal", f"{float(quotation.amount_sgd):.2f}"),
            (f"Tax {float(quotation.gst_rate)}% ({quotation.tax_code})", f"{float(quotation.gst_amount_sgd):.2f}"),
            ("Grand Total (SGD)", f"{float(quotation.total_amount_sgd):.2f}"),
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

    if quotation.notes:
        doc.add_paragraph()
        notes = doc.add_paragraph()
        notes.add_run("Notes: ").bold = True
        notes.add_run(quotation.notes)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def receipt_to_docx(
    payment: Payment, customer: Customer, company: Company, invoice_numbers: dict
) -> bytes:
    doc = Document()

    header = doc.add_paragraph()
    header.add_run(company.name).bold = True
    if company.address:
        doc.add_paragraph(company.address)
    if company.phone:
        doc.add_paragraph(f"Tel: {company.phone}")
    if company.uen:
        doc.add_paragraph(f"Business Reg# {company.uen}")

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("OFFICIAL RECEIPT")
    run.bold = True
    run.font.size = Pt(16)

    meta = doc.add_paragraph()
    meta.add_run(f"{payment.voucher_number}\n").bold = True
    meta.add_run(f"Date: {payment.payment_date.isoformat()}\n")
    meta.add_run(f"Method: {payment.method.value}\n")
    if payment.reference:
        meta.add_run(f"Reference: {payment.reference}\n")

    doc.add_paragraph().add_run("Received From").italic = True
    from_p = doc.add_paragraph()
    from_p.add_run(customer.name + "\n").bold = True
    if customer.uen:
        from_p.add_run(f"UEN: {customer.uen}")

    doc.add_paragraph()
    total = doc.add_paragraph()
    total.add_run(f"Amount Received: SGD {float(payment.amount_sgd):.2f}").bold = True

    if payment.allocations:
        doc.add_paragraph().add_run("Applied To").italic = True
        table = doc.add_table(rows=1, cols=2)
        table.style = "Light Grid Accent 1"
        hdr = table.rows[0].cells
        hdr[0].text = "Invoice"
        hdr[1].text = "Amount ($)"
        for a in payment.allocations:
            row = table.add_row().cells
            row[0].text = invoice_numbers.get(a.invoice_id, "")
            row[1].text = f"{float(a.amount_sgd):.2f}"

    unallocated = float(payment.unallocated_sgd)
    if unallocated > 0:
        doc.add_paragraph()
        doc.add_paragraph(f"Unallocated (on account): SGD {unallocated:.2f}")

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def payment_voucher_to_docx(
    payment: SupplierPayment, supplier: Supplier, company: Company, bill_numbers: dict
) -> bytes:
    doc = Document()

    header = doc.add_paragraph()
    header.add_run(company.name).bold = True
    if company.address:
        doc.add_paragraph(company.address)
    if company.phone:
        doc.add_paragraph(f"Tel: {company.phone}")
    if company.uen:
        doc.add_paragraph(f"Business Reg# {company.uen}")

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("PAYMENT VOUCHER")
    run.bold = True
    run.font.size = Pt(16)

    meta = doc.add_paragraph()
    meta.add_run(f"{payment.voucher_number}\n").bold = True
    meta.add_run(f"Date: {payment.payment_date.isoformat()}\n")
    meta.add_run(f"Method: {payment.method}\n")
    if payment.reference:
        meta.add_run(f"Reference: {payment.reference}\n")

    doc.add_paragraph().add_run("Paid To").italic = True
    to_p = doc.add_paragraph()
    to_p.add_run(supplier.name + "\n").bold = True
    if supplier.gst_registration_no:
        to_p.add_run(f"GST Reg# {supplier.gst_registration_no}")

    doc.add_paragraph()
    total = doc.add_paragraph()
    total.add_run(f"Amount Paid: SGD {float(payment.amount_sgd):.2f}").bold = True

    if payment.allocations:
        doc.add_paragraph().add_run("Applied To").italic = True
        table = doc.add_table(rows=1, cols=2)
        table.style = "Light Grid Accent 1"
        hdr = table.rows[0].cells
        hdr[0].text = "Bill"
        hdr[1].text = "Amount ($)"
        for a in payment.allocations:
            row = table.add_row().cells
            row[0].text = bill_numbers.get(a.supplier_invoice_id, "")
            row[1].text = f"{float(a.amount_sgd):.2f}"

    unallocated = float(payment.unallocated_sgd)
    if unallocated > 0:
        doc.add_paragraph()
        doc.add_paragraph(f"Unallocated: SGD {unallocated:.2f}")

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
