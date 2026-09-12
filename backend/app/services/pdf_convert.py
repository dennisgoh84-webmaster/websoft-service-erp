"""Convert a generated .docx form (see docx_forms.py) to PDF bytes, for
"Email PO" (2026-09-12): a real send needs a real PDF attachment, and the
browser's own Print -> Save as PDF (used by every *PrintPage.tsx) isn't
available on the server.

Rather than a second, separately-maintained PDF layout (e.g. via
reportlab), this shells out to LibreOffice headless to convert the exact
same .docx bytes already built for the "Word" export button -- one
template, two output formats, so they can never drift apart. This adds
LibreOffice as a system dependency on whatever machine runs the backend
(`apt install libreoffice-core` or similar); see DEV_SETUP.md.
"""
import subprocess
import tempfile
import uuid
from pathlib import Path


class PdfConversionError(Exception):
    """LibreOffice isn't installed, or the conversion itself failed."""


def docx_bytes_to_pdf(docx_bytes: bytes, *, timeout_seconds: int = 30) -> bytes:
    with tempfile.TemporaryDirectory(prefix="websoft-pdf-") as tmp:
        tmp_path = Path(tmp)
        # A random name per call, plus each call getting its own tempdir as
        # -env:UserInstallation, avoids soffice's profile-lock contention if
        # two conversions ever land at the same moment.
        docx_path = tmp_path / f"{uuid.uuid4().hex}.docx"
        docx_path.write_bytes(docx_bytes)
        profile_dir = tmp_path / "profile"

        try:
            result = subprocess.run(
                [
                    "soffice",
                    "--headless",
                    "--norestore",
                    f"-env:UserInstallation=file://{profile_dir}",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    str(tmp_path),
                    str(docx_path),
                ],
                capture_output=True,
                timeout=timeout_seconds,
            )
        except FileNotFoundError as e:
            raise PdfConversionError(
                "PDF conversion is not available: LibreOffice (soffice) is not installed "
                "on this server. See DEV_SETUP.md."
            ) from e
        except subprocess.TimeoutExpired as e:
            raise PdfConversionError("PDF conversion timed out.") from e

        pdf_path = docx_path.with_suffix(".pdf")
        if result.returncode != 0 or not pdf_path.exists():
            stderr = result.stderr.decode("utf-8", errors="replace").strip()
            raise PdfConversionError(f"PDF conversion failed: {stderr or 'unknown error'}")

        return pdf_path.read_bytes()
