"""Splits page text into overlapping chunks without ever crossing a page boundary,
so every chunk keeps an accurate page number for citations."""

from dataclasses import dataclass

from app.services.pdf_service import PageText


@dataclass
class Chunk:
    index: int  # position within the document, starting at 0
    page_number: int
    text: str


def _split_page(text: str, size: int, overlap: int) -> list[str]:
    if len(text) <= size:
        return [text]
    pieces: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            # Prefer to cut at a space, but never shrink the chunk below 60% of its size.
            cut = text.rfind(" ", start + int(size * 0.6), end)
            if cut > start:
                end = cut
        piece = text[start:end].strip()
        if piece:
            pieces.append(piece)
        if end >= len(text):
            break
        next_start = end - overlap
        if next_start <= start:
            next_start = end  # always make progress
        elif text[next_start - 1] != " ":
            # The overlap would begin mid-word: move forward to the start of the next word.
            space = text.find(" ", next_start)
            next_start = space + 1 if space != -1 else end
        start = next_start
        while start < len(text) and text[start] == " ":
            start += 1
    return pieces


def chunk_pages(pages: list[PageText], size: int, overlap: int) -> list[Chunk]:
    chunks: list[Chunk] = []
    for page in pages:
        for piece in _split_page(page.text, size, overlap):
            chunks.append(Chunk(index=len(chunks), page_number=page.page_number, text=piece))
    return chunks
