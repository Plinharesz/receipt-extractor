"""
Tests for src.core.parser.

Since parse_receipt() operates on plain strings (not files), these
tests don't need tmp_path or any file generation -- just hand-crafted
text samples simulating what extractor.py would have produced.
"""

from datetime import date
from decimal import Decimal

from src.core.parser import parse_receipt


# ---------------------------------------------------------------------
# Vendor extraction
# ---------------------------------------------------------------------

def test_parse_receipt_extracts_vendor_from_first_line():
    raw_text = "ACME Supplies Ltd.\nSome other line\nTotal: 50.00"

    receipt = parse_receipt(raw_text)

    assert receipt.vendor == "ACME Supplies Ltd."


def test_parse_receipt_skips_leading_blank_lines_for_vendor():
    # Simulates a PDF where extra whitespace precedes the real content --
    # common artifact from how PDF text layers are structured.
    raw_text = "\n\n   \nACME Supplies Ltd.\nTotal: 50.00"

    receipt = parse_receipt(raw_text)

    assert receipt.vendor == "ACME Supplies Ltd."


# ---------------------------------------------------------------------
# Total extraction
# ---------------------------------------------------------------------

def test_parse_receipt_extracts_plain_total():
    raw_text = "ACME Store\nSubtotal: 100.00\nTotal: 149.90"

    receipt = parse_receipt(raw_text)

    assert receipt.total == Decimal("149.90")


def test_parse_receipt_extracts_br_formatted_total():
    # Brazilian number format: dot as thousands separator, comma as
    # decimal separator -- e.g. "1.234,56" means one thousand, two
    # hundred thirty-four reais and fifty-six cents.
    raw_text = "ACME Store\nTotal: R$ 1.234,56"

    receipt = parse_receipt(raw_text)

    assert receipt.total == Decimal("1234.56")


def test_parse_receipt_takes_last_total_when_multiple_matches():
    # Receipts often list a subtotal before the final total -- we must
    # take the LAST match, not the first.
    raw_text = "ACME Store\nSubtotal: 200.00\nTotal: 180.00"

    receipt = parse_receipt(raw_text)

    assert receipt.total == Decimal("180.00")


# ---------------------------------------------------------------------
# Date extraction
# ---------------------------------------------------------------------

def test_parse_receipt_extracts_date_dd_mm_yyyy():
    raw_text = "ACME Store\nDate: 15/03/2026\nTotal: 50.00"

    receipt = parse_receipt(raw_text)

    assert receipt.issue_date == date(2026, 3, 15)


def test_parse_receipt_extracts_date_iso_format():
    raw_text = "ACME Store\nIssued: 2026-03-15\nTotal: 50.00"

    receipt = parse_receipt(raw_text)

    assert receipt.issue_date == date(2026, 3, 15)


# ---------------------------------------------------------------------
# Graceful degradation -- the most important test in this file
# ---------------------------------------------------------------------

def test_parse_receipt_returns_none_fields_when_nothing_recognizable():
    """
    Critical behavior: text with none of the expected patterns should
    NOT raise an exception. It should return a Receipt with None in
    the fields we couldn't extract, keeping raw_text intact for manual
    review or a future re-parse attempt.
    """
    raw_text = "some unrelated scanned gibberish with no clear structure"

    receipt = parse_receipt(raw_text)

    assert receipt.vendor == "some unrelated scanned gibberish with no clear structure"
    assert receipt.issue_date is None
    assert receipt.total is None
    assert receipt.raw_text == raw_text