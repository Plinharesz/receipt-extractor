"""
Parsing logic: converts raw extracted PDF text into a structured
Receipt object.

Design note: implemented with REGEX heuristics, not an LLM call, for
this MVP.
- Pros: deterministic, free, runs in milliseconds, no external
  dependency or API cost.
- Cons: fragile against receipt layouts very different from the
  expected pattern.
- Trade-off accepted: regex covers the majority of common cases for
  this MVP. An LLM-based fallback for edge cases is a documented
  future iteration, not an oversight.
"""

import logging
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

from src.core.models import Receipt

logger = logging.getLogger(__name__)

# Precompiled regex patterns -- compiling once at module load time is
# more efficient than recompiling on every function call, since this
# code may run over thousands of receipts in production.
_TOTAL_PATTERN = re.compile(
    r"total\s*[:\-]?\s*R?\$?\s*([\d]{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)",
    re.IGNORECASE,
)

# List of (pattern, strptime_format) pairs, tried in order. The first
# one that matches AND parses successfully wins.
_DATE_PATTERNS = [
    (re.compile(r"\b(\d{2}[/-]\d{2}[/-]\d{4})\b"), "%d/%m/%Y"),  # dd/mm/yyyy
    (re.compile(r"\b(\d{4}-\d{2}-\d{2})\b"), "%Y-%m-%d"),        # yyyy-mm-dd (ISO)
]


def _extract_vendor(raw_text: str) -> Optional[str]:
    """
    Heuristic: the vendor name is usually the first non-empty line
    of a receipt. Works for many standard layouts, but not all --
    this is a documented known limitation, not an oversight.
    """
    for line in raw_text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return None


def _extract_total(raw_text: str) -> Optional[Decimal]:
    """
    Finds a monetary value following the word "total" (case-insensitive).
    If multiple matches exist, we take the LAST one, since receipts
    often list a subtotal before the final total.
    """
    matches = _TOTAL_PATTERN.findall(raw_text)
    if not matches:
        return None

    raw_value = matches[-1]

    # Normalize Brazilian-style "1.234,56" (dot as thousands separator,
    # comma as decimal) into a Decimal-parseable string like "1234.56".
    # A plain "149.90" (US/ISO style, no comma) passes through unchanged.
    if "," in raw_value:
        normalized = raw_value.replace(".", "").replace(",", ".")
    else:
        normalized = raw_value

    try:
        return Decimal(normalized)
    except InvalidOperation:
        # Malformed number matched the pattern but can't become a
        # Decimal -- log it and move on instead of crashing the
        # whole parse over one bad field.
        logger.warning(f"Could not parse total value: '{raw_value}'")
        return None


def _extract_date(raw_text: str) -> Optional[date]:
    """
    Tries each known date pattern in order and returns the first
    successfully parsed match.
    """
    for pattern, date_format in _DATE_PATTERNS:
        match = pattern.search(raw_text)
        if match:
            date_str = match.group(0)
            try:
                return datetime.strptime(date_str, date_format).date()
            except ValueError:
                # Pattern matched the shape (e.g. "99/99/9999") but
                # the value isn't a real date -- keep trying other
                # patterns instead of giving up entirely.
                logger.warning(f"Matched date pattern but failed to parse: '{date_str}'")
                continue
    return None


def parse_receipt(raw_text: str) -> Receipt:
    """
    Converts raw PDF text into a structured, validated Receipt object.

    Any field we fail to extract is left as None (per the Optional
    fields on the Receipt model) instead of raising -- a partially
    filled Receipt is more useful downstream than no Receipt at all.
    """
    vendor = _extract_vendor(raw_text)
    issue_date = _extract_date(raw_text)
    total = _extract_total(raw_text)

    # Pydantic validation (e.g., total >= 0) runs automatically here,
    # at construction time. If the regex somehow extracted a negative
    # number, it fails LOUDLY on this line -- not three layers deeper,
    # inside the export logic.
    return Receipt(
        vendor=vendor,
        issue_date=issue_date,
        total=total,
        raw_text=raw_text,
    )