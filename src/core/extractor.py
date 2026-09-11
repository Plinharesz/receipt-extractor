"""
Core logic for extracting raw text from PDF receipt files.

This module has ONE responsibility: given a file path, return the raw
text content of that PDF. It knows nothing about parsing fields,
exporting to Excel, or the UI — that separation is what makes it
independently testable and reusable (by the API, by Streamlit, by CLI).
"""

import logging
from pathlib import Path

import pdfplumber

from src.exceptions import UnreadablePDFError

# Module-level logger, following the standard library convention.
# Using `print()` in application code is a common beginner mistake --
# logging lets you control verbosity and route output properly later
# (to a file, to a monitoring service, etc.) without changing this code.
logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract and return all text content from a PDF file.

    Args:
        file_path: Path to the PDF file on disk.

    Returns:
        The concatenated text of all pages in the PDF.

    Raises:
        UnreadablePDFError: If the file doesn't exist, isn't a valid PDF,
            or contains no extractable text (e.g., a pure image scan).
    """
    path = Path(file_path)

    # Fail fast with a clear, specific error instead of letting
    # pdfplumber throw a cryptic low-level exception later.
    if not path.exists():
        raise UnreadablePDFError(file_path, reason="file does not exist")

    if path.suffix.lower() != ".pdf":
        raise UnreadablePDFError(file_path, reason="file is not a PDF")

    try:
        with pdfplumber.open(path) as pdf:
            pages_text = []
            for page in pdf.pages:
                # extract_text() returns None if the page has no
                # extractable text layer (common in scanned images) --
                # we guard against that instead of crashing on
                # `None + str`.
                text = page.extract_text()
                if text:
                    pages_text.append(text)

            full_text = "\n".join(pages_text)

    except Exception as original_error:
        # We DO catch the generic Exception here, but only at this one
        # boundary -- the point where we translate an unpredictable
        # third-party library failure into OUR OWN known exception type.
        # This is the one acceptable place for a broad except: at the
        # edge of the system, converting external chaos into an internal
        # contract the rest of the app can rely on.
        logger.error(f"pdfplumber failed on '{file_path}': {original_error}")
        raise UnreadablePDFError(
            file_path, reason=f"pdfplumber error: {original_error}"
        ) from original_error

    if not full_text.strip():
        # The file opened fine, but had no extractable text at all --
        # this is the "pure image scan" case, which will need OCR
        # (pytesseract) as a fallback in a future sprint. For now we
        # raise clearly instead of silently returning an empty string.
        raise UnreadablePDFError(
            file_path, reason="no extractable text found (may need OCR)"
        )

    return full_text