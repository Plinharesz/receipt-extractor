"""
Tests for src.services.export_service.

These tests write real files to a pytest tmp_path, then read them
back to confirm the content survived the round-trip -- more
trustworthy than only checking the DataFrame in memory, since it also
catches engine-specific serialization issues.
"""

from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

from src.core.models import Receipt
from src.exceptions import ExportError
from src.services.export_service import export_to_csv, export_to_excel


@pytest.fixture
def sample_receipts() -> list[Receipt]:
    return [
        Receipt(
            vendor="ACME Supplies Ltd.",
            issue_date=None,
            total=Decimal("149.90"),
            raw_text="ACME Supplies Ltd.\nTotal: 149.90",
        ),
        Receipt(
            vendor="Office Depot",
            issue_date=None,
            total=Decimal("89.50"),
            raw_text="Office Depot\nTotal: 89.50",
        ),
    ]


def test_export_to_excel_creates_file_with_correct_rows(tmp_path: Path, sample_receipts):
    output_path = tmp_path / "receipts.xlsx"

    export_to_excel(sample_receipts, str(output_path))

    assert output_path.exists()
    df = pd.read_excel(output_path)
    assert list(df["Vendor"]) == ["ACME Supplies Ltd.", "Office Depot"]
    assert list(df["Total"]) == [149.90, 89.50]


def test_export_to_csv_creates_file_with_correct_rows(tmp_path: Path, sample_receipts):
    output_path = tmp_path / "receipts.csv"

    export_to_csv(sample_receipts, str(output_path))

    assert output_path.exists()
    df = pd.read_csv(output_path)
    assert list(df["Vendor"]) == ["ACME Supplies Ltd.", "Office Depot"]


def test_export_handles_empty_receipt_list(tmp_path: Path):
    """
    Exporting an empty list should produce a valid file with just the
    header row, not raise -- an empty batch is a normal outcome, not
    an error.
    """
    output_path = tmp_path / "empty.xlsx"

    export_to_excel([], str(output_path))

    df = pd.read_excel(output_path)
    assert len(df) == 0
    assert list(df.columns) == ["Vendor", "Date", "Total"]


def test_export_to_excel_raises_export_error_on_invalid_path(sample_receipts):
    """
    Writing to a path in a directory that doesn't exist should raise
    our own ExportError, not a raw OSError leaking from pandas/openpyxl.
    """
    invalid_path = "/this/directory/does/not/exist/receipts.xlsx"

    with pytest.raises(ExportError):
        export_to_excel(sample_receipts, invalid_path)