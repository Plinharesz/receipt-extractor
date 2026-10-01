# Architecture

This document explains the key technical decisions behind Receipt Extractor, the trade-offs considered, and known limitations. For setup and usage instructions, see [README.md](./README.md).

## System overview

The pipeline is a linear, single-direction flow. Each stage receives validated output from the previous one and has no knowledge of what comes after it:

PDF file
│
▼
extractor.py → raw text (string)
│
▼
parser.py → structured fields (regex)
│
▼
models.py (Receipt) → validated object (Pydantic)
│
▼
export_service.py → Excel/CSV file
│
▼
app_streamlit.py → delivered to the user


## Design principles

### 1. Separation of core logic from external dependencies

The codebase is split into three layers:

- **`src/core/`** — pure business logic (`extractor.py`, `parser.py`, `models.py`). No dependency on UI frameworks, file export libraries, or any I/O beyond reading the PDF itself. This layer is deterministic and fully unit-testable in isolation.
- **`src/services/`** — logic that depends on external, "heavier" libraries (`export_service.py` depends on `pandas`/`openpyxl`). Kept separate so that swapping the export engine (e.g. to a PDF report generator) never touches `core/`.
- **`app_streamlit.py`** — presentation layer. Contains zero business logic; it only collects input, calls `core`/`services` functions, and renders output.

**Why this matters:** each layer can change independently. The UI could be replaced with a FastAPI endpoint or a CLI tool tomorrow without modifying a single line of `core/` or `services/`, because neither of those layers knows the UI exists.

### 2. Error boundary pattern

Every module that wraps a third-party library (`pdfplumber` in `extractor.py`, `pandas`/`openpyxl` in `export_service.py`) follows the same rule: catch the generic, unpredictable exception from the external library **at exactly one point** — the boundary — and translate it into a specific, known exception from our own hierarchy (`AppError` → `UnreadablePDFError`, `ExportError`).

```python
try:
    # call into third-party library
except Exception as original_error:
    raise OurSpecificError(...) from original_error
```

Everywhere else in the codebase, code only needs to anticipate `AppError` and its subclasses — never a raw, unpredictable exception from a dependency. The UI layer (`app_streamlit.py`) catches `AppError` once, at its own boundary, and converts it into a user-facing message via `st.error()`.

**Alternative considered:** catching `Exception` broadly throughout the codebase. Rejected because it hides real bugs — a broad `except Exception` can't distinguish "the PDF is corrupted" from "there's a typo in my code."

### 3. `Decimal` instead of `float` for monetary values

`Receipt.total` is typed as `Decimal`, not `float`. Floating-point arithmetic has well-known rounding errors (`0.1 + 0.2 != 0.3` in IEEE 754) that are unacceptable when the value represents money. `Decimal` is converted to `float` only at the very last step, inside `export_service.py`, because `openpyxl` doesn't natively serialize `Decimal` — this keeps precision everywhere else in the system and isolates the conversion to one well-documented line.

### 4. Regex-based parsing instead of an LLM

`parser.py` extracts `vendor`, `issue_date`, and `total` using regular expressions and simple heuristics (e.g., "the vendor is the first non-empty line"; "the total is the last money value following the word 'total'").

| | Regex (chosen for MVP) | LLM-based extraction |
|---|---|---|
| Cost | Free | Per-call API cost |
| Latency | Milliseconds | Seconds, network-dependent |
| Determinism | Fully deterministic, easy to unit test | Non-deterministic, harder to test reliably |
| Robustness | Fails on unusual receipt layouts | Generalizes better to varied formats |
| External dependency | None | Requires an API key and network access |

**Decision:** regex covers the large majority of standard receipt layouts at zero cost and zero latency, which fits the MVP's goals. An LLM-based fallback for receipts that regex fails to parse is a natural extension, not a rejected idea — see "Future improvements" below.

### 5. Optional fields and graceful degradation

`Receipt.vendor`, `Receipt.issue_date`, and `Receipt.total` are all `Optional`. Only `raw_text` is required. If `parser.py` fails to find a field, it returns `None` for that field rather than raising an exception — a partially filled `Receipt` is more useful downstream (the user can review and fix it manually) than losing the whole document.

This same philosophy extends to batch processing in `app_streamlit.py`: if one uploaded PDF fails, the remaining files in the batch are still processed. A single bad file never blocks the whole upload.

## Testing strategy

All automated tests generate their own test data at runtime instead of depending on static fixture files:

- **PDF-based tests** (`test_extractor.py`) use `reportlab` to generate valid, blank, and malformed PDFs inside a pytest `tmp_path` — a fresh temporary directory per test.
- **Parser tests** (`test_parser.py`) operate directly on hand-written text strings, since `parser.py` has no file I/O.
- **Export tests** (`test_export_service.py`) write real `.xlsx`/`.csv` files to `tmp_path` and read them back, verifying a full round-trip rather than only checking an in-memory DataFrame.

**Why this matters:** no test depends on a file that could go missing, get out of sync, or behave differently on another machine. The same test suite runs identically on any developer's machine and in CI (GitHub Actions), with zero setup beyond `pip install -r requirements.txt`.

## Known limitations

- **Vendor detection** is a simple heuristic (first non-empty line) and will misidentify the vendor on receipts with unusual letterhead layouts.
- **No OCR support.** PDFs that are pure image scans (no text layer) are rejected with a clear `UnreadablePDFError` rather than silently failing or hanging.
- **Currency formats** are limited to standard (`149.90`) and Brazilian (`1.234,56`) decimal/thousands separator conventions.
- **No UI test coverage.** `app_streamlit.py` has no automated tests; correctness is guaranteed indirectly, since every function it calls is covered by the 16 tests in `core`/`services`.

## Future improvements

- OCR fallback (`pytesseract`) for scanned receipts with no text layer.
- LLM-based extraction as a fallback when regex parsing fails, rather than a full replacement.
- A FastAPI layer exposing the same `core`/`services` pipeline programmatically, for integrations beyond the Streamlit UI.
- Multi-currency support beyond BRL/USD-style formatting.
