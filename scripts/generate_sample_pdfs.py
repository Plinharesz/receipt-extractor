"""
Utility script to generate a battery of test PDF files for manually
testing the Streamlit UI (app_streamlit.py) end-to-end.

This is a DEV-ONLY tool -- it is NOT part of the automated test suite
(pytest already covers these same scenarios with PDFs generated
in-memory, see tests/test_extractor.py). This script exists purely so
you have real .pdf files on disk to drag-and-drop into the running
Streamlit app and watch the full pipeline react.

Usage:
    python scripts/generate_sample_pdfs.py
"""

from pathlib import Path

from reportlab.pdfgen import canvas

OUTPUT_DIR = Path(__file__).parent.parent / "samples"


def generate_valid_receipt(path: Path) -> None:
    """Scenario 1: clean, standard receipt -- the happy path."""
    c = canvas.Canvas(str(path))
    c.drawString(100, 750, "Tech Store Ltda")
    c.drawString(100, 730, "Date: 15/03/2026")
    c.drawString(100, 710, "Total: R$ 1.499,90")
    c.save()


def generate_receipt_with_subtotal(path: Path) -> None:
    """
    Scenario 2: BR currency format + multiple totals on the page.
    Exercises _extract_total()'s rule of taking the LAST match (the
    real total), not the subtotal or the shipping line.
    """
    c = canvas.Canvas(str(path))
    c.drawString(100, 750, "Office Supplies Co.")
    c.drawString(100, 730, "Date: 22/04/2026")
    c.drawString(100, 710, "Subtotal: 1.000,00")
    c.drawString(100, 690, "Shipping: 50,50")
    c.drawString(100, 670, "Total: R$ 2.350,50")
    c.save()


def generate_irregular_layout(path: Path) -> None:
    """
    Scenario 3: no extra blank lines are literally drawn (reportlab
    doesn't emit empty text lines by default), so we simulate the
    "irregular layout" by starting content lower on the page --
    mimicking a receipt with letterhead/logo space before the first
    real text line. Tests that _extract_vendor() still finds the
    first NON-EMPTY line correctly.
    """
    c = canvas.Canvas(str(path))
    c.drawString(100, 700, "Market Fresh Groceries")
    c.drawString(100, 680, "Date: 01/01/2026")
    c.drawString(100, 660, "Total: 87,20")
    c.save()


def generate_blank_pdf(path: Path) -> None:
    """
    Scenario 4a: structurally valid PDF with NO text layer at all --
    simulates a pure image scan. Should trigger UnreadablePDFError
    with a reason mentioning that OCR might be needed.
    """
    c = canvas.Canvas(str(path))
    c.showPage()
    c.save()


def generate_fake_pdf(path: Path) -> None:
    """
    Scenario 4b: a plain text file wearing a .pdf extension. Passes
    Streamlit's client-side filter (type=["pdf"]) and our own
    extension check, but fails when pdfplumber actually tries to open
    it -- exercising the error-boundary `except Exception` branch in
    extractor.py, which translates it into UnreadablePDFError.
    """
    path.write_text("This is not a real PDF file, just plain text pretending to be one.")


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)

    scenarios = {
        "01_valid_receipt.pdf": generate_valid_receipt,
        "02_receipt_with_subtotal.pdf": generate_receipt_with_subtotal,
        "03_irregular_layout.pdf": generate_irregular_layout,
        "04_blank_no_text.pdf": generate_blank_pdf,
        "05_fake_not_a_real_pdf.pdf": generate_fake_pdf,
    }

    for filename, generator in scenarios.items():
        file_path = OUTPUT_DIR / filename
        generator(file_path)
        print(f"Generated: {file_path}")

    print(f"\nDone. {len(scenarios)} sample files created in '{OUTPUT_DIR}/'.")


if __name__ == "__main__":
    main()