"""Page rendering and citation highlighting (PyMuPDF).

A citation's supporting passage is a stored chunk of text. To highlight it, the chunk's words are aligned with the
words PyMuPDF reports for that page (with their bounding boxes). Rectangles are only returned when most of the chunk
really was found on the page; otherwise `reliable` is false and no rectangles are sent, so the viewer simply opens the
right page without drawing a guess."""

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path

import pymupdf

from app.services.pdf_service import PdfError, _open

MIN_SCALE, MAX_SCALE, DEFAULT_SCALE = 0.5, 3.0, 1.5
MIN_RUN = 3  # a matching run shorter than this is coincidence, not evidence
RELIABLE_COVERAGE = 0.6  # share of the passage's words that must be located on the page

_VECTOR_ID = re.compile(r"^chunk-(\d+)$")


def chunk_pk_from_vector_id(vector_id: str) -> int | None:
    m = _VECTOR_ID.match(vector_id or "")
    return int(m.group(1)) if m else None


@dataclass
class Highlights:
    page_number: int
    page_width: float
    page_height: float
    rects: list[dict] = field(default_factory=list)  # fractions of the page: x, y, w, h in 0..1
    matched_words: int = 0
    total_words: int = 0
    coverage: float = 0.0
    reliable: bool = False


def _norm(word: str) -> str:
    return word.casefold()


def render_page_png(path: Path, page_number: int, scale: float = DEFAULT_SCALE) -> bytes:
    scale = min(max(scale, MIN_SCALE), MAX_SCALE)
    doc = _open(path)
    try:
        if not 1 <= page_number <= doc.page_count:
            raise PdfError("PAGE_OUT_OF_RANGE", "That page does not exist in this document.")
        pix = doc[page_number - 1].get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)
        return pix.tobytes("png")
    finally:
        doc.close()


def locate(path: Path, page_number: int, passage: str) -> Highlights:
    doc = _open(path)
    try:
        if not 1 <= page_number <= doc.page_count:
            raise PdfError("PAGE_OUT_OF_RANGE", "That page does not exist in this document.")
        page = doc[page_number - 1]
        width, height = float(page.rect.width), float(page.rect.height)
        result = Highlights(page_number=page_number, page_width=width, page_height=height)

        target = [_norm(w) for w in passage.split()]
        result.total_words = len(target)
        words = page.get_text("words")  # (x0, y0, x1, y1, text, block, line, word_no)
        if not target or not words:
            return result
        page_words = [_norm(w[4]) for w in words]

        blocks = SequenceMatcher(None, page_words, target, autojunk=False).get_matching_blocks()
        min_run = min(MIN_RUN, len(target))
        picked = [b for b in blocks if b.size >= min_run]
        matched = sum(b.size for b in picked)
        result.matched_words = matched
        result.coverage = round(matched / len(target), 3)
        if result.coverage < RELIABLE_COVERAGE:
            return result

        # One rectangle per text line keeps the overlay tidy.
        lines: dict[tuple[int, int], pymupdf.Rect] = {}
        for b in picked:
            for w in words[b.a : b.a + b.size]:
                key = (w[5], w[6])
                rect = pymupdf.Rect(w[0], w[1], w[2], w[3])
                lines[key] = lines[key] | rect if key in lines else rect
        for rect in lines.values():
            r = rect * page.rotation_matrix  # words are reported unrotated; the rendered page is rotated
            r.normalize()
            result.rects.append(
                {
                    "x": round(max(r.x0 / width, 0.0), 5),
                    "y": round(max(r.y0 / height, 0.0), 5),
                    "w": round(min((r.x1 - r.x0) / width, 1.0), 5),
                    "h": round(min((r.y1 - r.y0) / height, 1.0), 5),
                }
            )
        result.rects.sort(key=lambda r: (r["y"], r["x"]))
        result.reliable = bool(result.rects)
        return result
    finally:
        doc.close()
