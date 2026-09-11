"""
Custom exceptions for the receipt-extractor application.

Why custom exceptions instead of raising generic Exception?
- Generic `except Exception` blocks hide bugs and make debugging harder.
- Custom exceptions let callers catch SPECIFIC failure modes and react
  differently (e.g., retry, log, show a friendly UI message) instead of
  guessing what went wrong from a string message.
"""


class AppError(Exception):
    """
    Base exception for all application-specific errors.

    Having one base class lets other parts of the app catch
    `except AppError` to handle ANY known failure from this app,
    while still letting truly unexpected errors (real bugs) bubble up
    uncaught — which is what you want during development.
    """
    pass


class UnreadablePDFError(AppError):
    """
    Raised when a PDF file cannot be opened or has no extractable text
    (e.g., corrupted file, password-protected, or a pure image scan
    with no OCR fallback applied yet).
    """

    def __init__(self, file_path: str, reason: str = "unknown reason"):
        # We store the original context (file_path, reason) as attributes,
        # not just inside the message string. This means calling code can
        # do `except UnreadablePDFError as e: log(e.file_path)` instead of
        # parsing a string — much more robust and testable.
        self.file_path = file_path
        self.reason = reason
        super().__init__(f"Could not read PDF at '{file_path}': {reason}")