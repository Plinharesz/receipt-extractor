"""
Streamlit presentation layer for receipt-extractor.

This file is intentionally "dumb": it contains ZERO business logic.
Its only job is to:
1. Collect PDF uploads from the user.
2. Call the existing core/services functions (already tested in
   Sprints 1-3) to do the real work.
3. Render the results and offer a download.

If this file breaks, the core pipeline remains safe and independently
tested -- that separation is the whole point of the architecture
we've been building since Sprint 1.
"""

import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from src.core.extractor import extract_text_from_pdf
from src.core.models import Receipt
from src.core.parser import parse_receipt
from src.exceptions import AppError
from src.services.export_service import export_to_excel

st.set_page_config(page_title="Receipt Extractor", page_icon="🧾", layout="centered")

st.title("Receipt Extractor")
st.write(
    "Upload one or more PDF receipts to extract structured data "
    "and export a consolidated Excel file."
)

# type=["pdf"] restricts the file picker at the UI level, but
# extractor.py ALSO validates the extension independently -- this is
# defense in depth. Never trust validation from only one layer,
# especially the client-facing one.
uploaded_files = st.file_uploader(
    "Drag and drop PDF files here",
    type=["pdf"],
    accept_multiple_files=True,
)

if uploaded_files:
    receipts: list[Receipt] = []
    errors: list[tuple[str, str]] = []

    with st.spinner(f"Processing {len(uploaded_files)} file(s)..."):
        for uploaded_file in uploaded_files:
            # delete=False is required here: we need the file to still
            # exist on disk AFTER this `with` block closes it, so that
            # extract_text_from_pdf() (which reopens it by path) can
            # read it. We take on the responsibility of deleting it
            # ourselves in the `finally` block below.
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(uploaded_file.getvalue())
                tmp_path = tmp.name

            try:
                raw_text = extract_text_from_pdf(tmp_path)
                receipt = parse_receipt(raw_text)
                receipts.append(receipt)
            except AppError as e:
                # We catch our OWN exception hierarchy (AppError and
                # its subclasses) here -- a genuinely unexpected error
                # (a real bug) is NOT caught and will surface loudly,
                # which is what we want during development.
                errors.append((uploaded_file.name, str(e)))
            finally:
                # Always clean up the temp file, whether extraction
                # succeeded or failed -- otherwise every upload leaves
                # orphaned files on disk.
                Path(tmp_path).unlink(missing_ok=True)

    # Show one error message per failed file, without blocking the
    # successfully processed ones from being displayed below.
    if errors:
        for filename, message in errors:
            st.error(f"Could not process '{filename}': {message}")

    if receipts:
        st.subheader("Extracted data")

        # Build a lightweight preview table. This is deliberately
        # separate from export_service's DataFrame logic -- on-screen
        # preview and file export are different concerns (e.g. we
        # might want different formatting on screen vs. in the file).
        preview_df = pd.DataFrame(
            [
                {
                    "Vendor": r.vendor or "—",
                    "Date": r.issue_date.isoformat() if r.issue_date else "—",
                    "Total": float(r.total) if r.total is not None else None,
                }
                for r in receipts
            ]
        )
        st.dataframe(preview_df, use_container_width=True)

        # st.download_button needs raw bytes, not a file path -- so we
        # export to a temp file first, then read it back as bytes,
        # then delete the temp file. A few extra lines, but it reuses
        # export_to_excel() exactly as tested in Sprint 3, with zero
        # changes to that function's contract.
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_out:
            output_path = tmp_out.name

        export_to_excel(receipts, output_path)

        with open(output_path, "rb") as f:
            excel_bytes = f.read()
        Path(output_path).unlink(missing_ok=True)

        st.download_button(
            label="Download consolidated Excel",
            data=excel_bytes,
            file_name="receipts_export.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    else:
        st.warning("No receipts could be processed from the uploaded files.")