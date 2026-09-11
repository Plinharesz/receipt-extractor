"""
Tests for src.core.extractor.

Design decision: instead of relying on a static PDF file committed to
the repo (which can go stale, get lost, or make diffs hard to review),
we GENERATE valid PDFs on the fly using reportlab, inside a pytest
`tmp_path` (a temporary directory pytest creates and destroys
automatically for each test). This makes tests fully self-contained
and reproducible on any machine, including CI runners that have never
seen this repo before.
"""

from pathlib import Path

import pytest
from reportlab.pdfgen import canvas

from src.core.extractor import extract_text_from_pdf
from src.exceptions import UnreadablePDFError


# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------
# A fixture is a reusable "setup" function that pytest injects into any
# test that declares it as a parameter. `tmp_path` itself is a
# BUILT-IN pytest fixture (a fresh temp folder per test) -- we build our
# own fixture on top of it to avoid repeating PDF-generation code in
# every test function.

@pytest.fixture
def valid_pdf_with_text(tmp_path: Path) -> Path:
    """
    Creates a real, valid PDF file containing known text, and returns
    its path. Used by tests that need a "happy path" PDF to read from.
    """
    pdf_path = tmp_path / "sample_receipt.pdf"

    c = canvas.Canvas(str(pdf_path))
    c.drawString(100, 750, "ACME Supplies Ltd.")
    c.drawString(100, 730, "Total: 149.90")
    c.save()

    return pdf_path


@pytest.fixture
def blank_pdf(tmp_path: Path) -> Path:
    """
    Creates a technically valid PDF with NO text on it at all --
    simulates the "pure image scan with no text layer" edge case
    without needing an actual scanned image.
    """
    pdf_path = tmp_path / "blank.pdf"

    c = canvas.Canvas(str(pdf_path))
    c.showPage()  # creates a blank page, no drawString() calls
    c.save()

    return pdf_path


# ---------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------

def test_extract_text_from_valid_pdf_returns_text(valid_pdf_with_text: Path):
    """
    Given a valid PDF with known text, the function should return
    that text content.
    """
    result = extract_text_from_pdf(str(valid_pdf_with_text))

    assert "ACME Supplies Ltd." in result
    assert "149.90" in result


# ---------------------------------------------------------------------
# Error scenarios
# ---------------------------------------------------------------------

def test_extract_text_raises_when_file_does_not_exist():
    """
    A path that doesn't exist on disk should raise our specific
    UnreadablePDFError -- not a generic FileNotFoundError -- so that
    calling code (API, Streamlit UI) can catch ONE known exception type.
    """
    fake_path = "/tmp/this_file_does_not_exist_12345.pdf"

    with pytest.raises(UnreadablePDFError) as exc_info:
        extract_text_from_pdf(fake_path)

    # We also assert on the exception's attributes, not just that it
    # was raised -- this locks in the *contract* of the exception,
    # so a future refactor that breaks it fails loudly in CI.
    assert exc_info.value.file_path == fake_path
    assert "does not exist" in exc_info.value.reason


def test_extract_text_raises_when_file_is_not_a_pdf(tmp_path: Path):
    """
    A file that exists but isn't a PDF (wrong extension) should be
    rejected before we even try to parse it.
    """
    txt_path = tmp_path / "not_a_receipt.txt"
    txt_path.write_text("this is just plain text, not a PDF")

    with pytest.raises(UnreadablePDFError) as exc_info:
        extract_text_from_pdf(str(txt_path))

    assert "not a PDF" in exc_info.value.reason


def test_extract_text_raises_when_pdf_has_no_text(blank_pdf: Path):
    """
    A structurally valid PDF that contains no extractable text (e.g.
    a pure image scan) should raise UnreadablePDFError with a hint
    that OCR might be needed -- this documents, via a test, the
    known limitation we'll address in a future sprint.
    """
    with pytest.raises(UnreadablePDFError) as exc_info:
        extract_text_from_pdf(str(blank_pdf))

    assert "no extractable text" in exc_info.value.reason