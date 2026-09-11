"""
Data models for the receipt-extractor application, using Pydantic.

Why Pydantic instead of a plain class or dict?
- Pydantic validates data automatically at creation time (e.g., rejects
  a negative `total` or a malformed date) instead of letting bad data
  silently flow through the system and fail somewhere unrelated later.
- It gives us free serialization to/from JSON and dict, useful later
  for the FastAPI layer and for tests.
"""

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class Receipt(BaseModel):
    """
    Represents a single parsed receipt/invoice.

    Fields are intentionally optional where the value might not be
    extractable from every document type (e.g., OCR might fail to find
    a date on a low-quality scan). Making them Optional now avoids
    crashing the whole pipeline over one missing field — we'd rather
    return a partially-filled Receipt than nothing at all.
    """

    vendor: Optional[str] = Field(
        default=None,
        description="Name of the store/company that issued the receipt.",
    )
    issue_date: Optional[date] = Field(
        default=None,
        description="Date the receipt was issued.",
    )
    total: Optional[Decimal] = Field(
        default=None,
        description="Total amount charged on the receipt.",
    )
    raw_text: str = Field(
        ...,  # "..." means this field is REQUIRED, no default allowed
        description="Full raw text extracted from the source PDF, "
                    "kept for debugging and for future re-parsing.",
    )

    @field_validator("total")
    @classmethod
    def total_must_be_non_negative(cls, value: Optional[Decimal]) -> Optional[Decimal]:
        # Custom validation rule: a receipt total can never be negative.
        # If it is, we fail LOUDLY here instead of letting a bad number
        # silently corrupt a downstream Excel export.
        if value is not None and value < 0:
            raise ValueError("Receipt total cannot be negative.")
        return value

    class Config:
        # Allows Pydantic to work smoothly with Decimal <-> JSON conversions
        # later when we expose this via FastAPI.
        json_encoders = {Decimal: str}