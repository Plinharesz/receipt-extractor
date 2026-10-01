# Receipt Extractor

[![CI](https://github.com/plinharesz/receipt-extractor/actions/workflows/ci.yml/badge.svg)](https://github.com/plinharesz/receipt-extractor/actions/workflows/ci.yml)

Extract structured data from PDF receipts and export a consolidated spreadsheet — no manual data entry required.

## The problem

Small business owners, freelancers, and accountants routinely spend hours each week manually copying data from receipts and invoices into spreadsheets, just to reconcile them against bank statements afterward. It's repetitive, time-consuming, and error-prone.

**Receipt Extractor** automates that workflow: drop in a batch of PDF receipts, get back a clean, structured Excel file in seconds.

## Demo

![Demo of the Streamlit app processing PDF receipts](docs/demo.gif)

*Upload multiple PDFs → review extracted data → download a consolidated Excel file.*

## Features

- Drag-and-drop upload of multiple PDF receipts at once
- Automatic extraction of vendor, date, and total amount
- Handles both standard (`149.90`) and Brazilian (`1.234,56`) currency formats
- Graceful error handling — a single bad file never blocks the rest of the batch
- One-click export to a consolidated `.xlsx` file
- Fully tested core pipeline (16 automated tests, CI on every push)

## Tech stack

| Layer | Technology | Why |
|---|---|---|
| PDF text extraction | `pdfplumber` | Reliable text-layer extraction from native PDFs |
| Data validation | `Pydantic` | Automatic validation and type safety for parsed fields |
| Field parsing | Regex (standard library) | Deterministic, fast, zero external dependency for the MVP |
| Spreadsheet export | `pandas` + `openpyxl` | Single interface for both Excel and CSV output |
| Web interface | `Streamlit` | Fast, code-first UI — no separate frontend needed |
| Testing | `pytest` | Dynamic test-PDF generation via `reportlab`, no static fixtures |
| CI/CD | `GitHub Actions` | Automated test run on every push |

Full technical decisions and trade-offs are documented in [ARCHITECTURE.md](./ARCHITECTURE.md).

## Getting started

### Prerequisites

- Python 3.12+
- pip

### Installation

```bash
git clone https://github.com/plinharesz/receipt-extractor.git
cd receipt-extractor
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Running the app

```bash
streamlit run app_streamlit.py
```

The app opens automatically at `http://localhost:8501`.

### Running the tests

```bash
pytest -v
```

All tests generate their own sample PDFs on the fly (via `reportlab`) — no external fixture files required, so the suite runs identically on any machine, including CI.

### Generating sample PDFs for manual testing

```bash
python3 scripts/generate_sample_pdfs.py
```

This creates a batch of sample receipts (including edge cases and intentionally invalid files) in the `samples/` folder, ready to drag into the running app.

## Project structure
receipt-extractor/
├── src/
│ ├── core/ # Pure business logic — no external I/O
│ │ ├── extractor.py # PDF → raw text
│ │ ├── parser.py # Raw text → structured fields
│ │ └── models.py # Receipt data model (Pydantic)
│ ├── services/
│ │ └── export_service.py # Receipt list → Excel/CSV file
│ └── exceptions.py # Custom exception hierarchy
├── app_streamlit.py # Presentation layer (drag-and-drop UI)
├── scripts/
│ └── generate_sample_pdfs.py # Dev tool for manual testing
├── tests/ # Automated test suite (pytest)
└── .github/workflows/ci.yml # CI pipeline


## Known limitations

- Vendor extraction assumes the vendor name is the first non-empty line of the document — works for most standard layouts, but not all.
- No OCR support yet — scanned image-only PDFs (no text layer) are rejected with a clear error rather than silently failing. OCR fallback via `pytesseract` is a planned extension.
- Field parsing uses regex heuristics rather than an LLM, by deliberate design choice (see [ARCHITECTURE.md](./ARCHITECTURE.md) for the trade-off discussion).

## License

MIT
EOF