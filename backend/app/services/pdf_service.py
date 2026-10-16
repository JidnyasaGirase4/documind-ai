"""PDF validation and page-aware text extraction (PyMuPDF). OCR is not supported."""

import re
from dataclasses import dataclass
from pathlib import Path

import pymupdf

from app.core.config import settings

MIN_USEFUL_CHARACTERS = 20


class PdfError(Exception):
    """A problem with the PDF that can be explained to the user."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class PageText:
    page_number: int  # 1-based
    text: str


def _open(path: Path) -> pymupdf.Document:
    # The file is read into memory first: PyMuPDF can otherwise keep a handle open on a corrupt
    # file, which on Windows prevents the rejected upload from being deleted.
    try:
        doc = pymupdf.open(stream=path.read_bytes(), filetype="pdf")
    except Exception as exc:
        raise PdfError("INVALID_PDF", "This file could not be read as a PDF.") from exc
    if doc.needs_pass:
        doc.close()
        raise PdfError("PASSWORD_PROTECTED", "Password-protected PDFs are not supported.")
    if doc.page_count == 0:
        doc.close()
        raise PdfError("INVALID_PDF", "This PDF has no pages.")
    return doc


def validate_pdf(path: Path) -> int:
    """Confirms the file parses as a PDF and returns its page count."""
    doc = _open(path)
    try:
        if doc.page_count > settings.max_pdf_pages:
            raise PdfError("TOO_MANY_PAGES", f"This PDF has more than {settings.max_pdf_pages} pages, which is the limit.")
        return doc.page_count
    finally:
        doc.close()


def extract_pages(path: Path) -> list[PageText]:
    """Returns the text of each page that has any. Raises PdfError when no page has usable text."""
    doc = _open(path)
    pages: list[PageText] = []
    try:
        for index in range(doc.page_count):
            text = " ".join(doc[index].get_text("text").split())
            if text:
                pages.append(PageText(page_number=index + 1, text=text))
    except PdfError:
        raise
    except Exception as exc:
        raise PdfError("INVALID_PDF", "Text could not be extracted from this PDF.") from exc
    finally:
        doc.close()

    if sum(len(p.text) for p in pages) < MIN_USEFUL_CHARACTERS:
        raise PdfError(
            "NO_EXTRACTABLE_TEXT",
            "No extractable text was found. This PDF may contain only scanned images; OCR is not supported yet.",
        )
    return pages


@dataclass
class TextUnit:
    page_number: int  # 1-based
    text: str


_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(\[])")


def extract_units(path: Path, max_units: int = 20000) -> list[TextUnit]:
    """Reading-order text units for version comparison: each paragraph/text block of each page, split into sentences.
    Paragraph structure is kept (unlike extract_pages, which flattens a page). Returns [] for a PDF without text."""
    doc = _open(path)
    units: list[TextUnit] = []
    try:
        for index in range(doc.page_count):
            for block in doc[index].get_text("blocks", sort=True):
                if block[6] != 0:  # images and other non-text blocks
                    continue
                text = " ".join(str(block[4]).split())
                for sentence in _SENTENCE_END.split(text):
                    sentence = sentence.strip()
                    if sentence:
                        units.append(TextUnit(index + 1, sentence))
                if len(units) > max_units:
                    return units
    except PdfError:
        raise
    except Exception as exc:
        raise PdfError("INVALID_PDF", "Text could not be extracted from this PDF.") from exc
    finally:
        doc.close()
    return units
