"""
Export service: converts validated Receipt objects into downloadable
spreadsheet files (XLSX or CSV).

This module is intentionally the ONLY place in the codebase that knows
about pandas/openpyxl. If we ever swap the export engine (e.g. to a
templated PDF report), only this file changes -- core.extractor and
core.parser remain completely untouched.
"""

import logging
from typing import List

import pandas as pd

from src.core.models import Receipt
from src.exceptions import ExportError

logger = logging.getLogger(__name__)

# Column order and display names defined once here, so output stays
# consistent regardless of which export function is called.
_COLUMNS = {
    "vendor": "Vendor",
    "issue_date": "Date",
    "total": "Total",
}


def _receipts_to_dataframe(receipts: List[Receipt]) -> pd.DataFrame:
    """
    Converts a list of Receipt objects into a pandas DataFrame with
    human-readable column names, ready for export.

    Kept private and separate from the public export_* functions so
    it can be unit tested independently of any file I/O.
    """
    rows = [
        {
            "vendor": r.vendor,
            "issue_date": r.issue_date,
            # Decimal isn't natively serializable by pandas/openpyxl --
            # converting to float here, at the export boundary, keeps
            # the precision of Decimal everywhere else in the system.
            "total": float(r.total) if r.total is not None else None,
        }
        for r in receipts
    ]

    # Passing `columns=` explicitly guarantees correct column order
    # and names even when `rows` is an empty list.
    df = pd.DataFrame(rows, columns=list(_COLUMNS.keys()))
    return df.rename(columns=_COLUMNS)


def export_to_excel(receipts: List[Receipt], output_path: str) -> str:
    """
    Writes the given receipts to an XLSX file at output_path.
    Returns output_path on success, for convenient chaining (e.g.
    passing straight into a Streamlit download button).
    """
    df = _receipts_to_dataframe(receipts)

    try:
        df.to_excel(output_path, index=False, engine="openpyxl")
    except Exception as original_error:
        # Same error boundary pattern as extractor.py: translate an
        # unpredictable third-party failure (bad path, disk full,
        # permission denied) into our own known exception type.
        logger.error(f"Failed to write Excel file at '{output_path}': {original_error}")
        raise ExportError(f"could not write Excel file: {original_error}") from original_error

    return output_path


def export_to_csv(receipts: List[Receipt], output_path: str) -> str:
    """
    Writes the given receipts to a CSV file at output_path.
    """
    df = _receipts_to_dataframe(receipts)

    try:
        df.to_csv(output_path, index=False)
    except Exception as original_error:
        logger.error(f"Failed to write CSV file at '{output_path}': {original_error}")
        raise ExportError(f"could not write CSV file: {original_error}") from original_error

    return output_path