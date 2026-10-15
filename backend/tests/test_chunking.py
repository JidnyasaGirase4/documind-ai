from app.rag.chunker import chunk_pages
from app.services.pdf_service import PageText, PdfError, extract_pages
from tests.conftest import make_pdf


def test_chunks_keep_page_numbers_and_never_cross_pages():
    pages = [PageText(1, "alpha " * 200), PageText(2, "beta " * 50), PageText(3, "gamma " * 200)]
    chunks = chunk_pages(pages, size=300, overlap=50)
    assert [c.index for c in chunks] == list(range(len(chunks)))
    for c in chunks:
        assert len(c.text) <= 300
        word = {1: "alpha", 2: "beta", 3: "gamma"}[c.page_number]
        assert set(c.text.split()) == {word}, "a chunk must only contain text from its own page"
    assert {c.page_number for c in chunks} == {1, 2, 3}
    assert [c.page_number for c in chunks] == sorted(c.page_number for c in chunks)


def test_chunks_overlap_and_make_progress():
    words = [f"w{i}" for i in range(400)]
    chunks = chunk_pages([PageText(1, " ".join(words))], size=200, overlap=60)
    assert len(chunks) > 3
    for first, second in zip(chunks, chunks[1:]):
        assert set(first.text.split()) & set(second.text.split()), "neighbouring chunks should share context"
    assert set(" ".join(c.text for c in chunks).split()) == set(words), "no text is lost"


def test_short_page_is_one_chunk():
    assert [c.text for c in chunk_pages([PageText(4, "short text")], 800, 120)] == ["short text"]


def test_extract_pages_reports_page_numbers_and_skips_empty_pages(tmp_path):
    f = tmp_path / "x.pdf"
    f.write_bytes(make_pdf(["First page text is here for the test", "", "Third page has words too, plenty of them"]))
    pages = extract_pages(f)
    assert [p.page_number for p in pages] == [1, 3]
    assert "First page" in pages[0].text


def test_extract_pages_rejects_scanned_and_corrupt_pdfs(tmp_path):
    scanned = tmp_path / "scan.pdf"
    scanned.write_bytes(make_pdf(["", ""]))
    try:
        extract_pages(scanned)
        raise AssertionError("expected PdfError")
    except PdfError as e:
        assert e.code == "NO_EXTRACTABLE_TEXT"

    corrupt = tmp_path / "bad.pdf"
    corrupt.write_bytes(b"%PDF-1.7 not really")
    try:
        extract_pages(corrupt)
        raise AssertionError("expected PdfError")
    except PdfError as e:
        assert e.code == "INVALID_PDF"
