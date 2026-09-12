"""Shared "Email this document" helper (2026-09-12), used by every
document type that offers an Email button: Purchase Order, Sales
Quotation, Sales Invoice, Receipt Voucher, Payment Voucher, Service
Record, Statement of Accounts. Each router builds its own .docx (via
docx_forms.py) and calls this rather than repeating the PDF-conversion +
SMTP-send boilerplate six times over.
"""
from app.services import mailer
from app.services.pdf_convert import PdfConversionError, docx_bytes_to_pdf


class DocumentEmailError(Exception):
    """Wraps PdfConversionError/MailerNotConfigured/MailerError so a
    router needs only one except clause; `status_code` says which HTTP
    status the router should raise."""

    def __init__(self, message: str, *, status_code: int):
        super().__init__(message)
        self.status_code = status_code


def send_document_email(
    *,
    to_email: str,
    subject: str,
    body_text: str,
    docx_bytes: bytes,
    filename_stem: str,
) -> None:
    try:
        pdf_bytes = docx_bytes_to_pdf(docx_bytes)
    except PdfConversionError as e:
        raise DocumentEmailError(str(e), status_code=422) from e

    try:
        mailer.send_email(
            to_email=to_email,
            subject=subject,
            body_text=body_text,
            attachment_filename=f"{filename_stem}.pdf",
            attachment_bytes=pdf_bytes,
        )
    except mailer.MailerNotConfigured as e:
        raise DocumentEmailError(str(e), status_code=422) from e
    except mailer.MailerError as e:
        raise DocumentEmailError(str(e), status_code=502) from e
