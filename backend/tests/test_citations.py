"""Clickable citations: page rendering and passage highlighting. Highlights are only returned when the passage was
really located on the page, and every endpoint is owner-only."""

from pathlib import Path

import pymupdf
from sqlalchemy import text as sql

from app.db.session import engine
from app.services import highlight_service
from tests.conftest import API, PARENTAL, WARRANTY, ask, make_pdf, new_conversation, new_user, ready_document
from tests.test_rag import use_llm


def _cited(client, h, doc_pages=(PARENTAL, WARRANTY), monkeypatch=None):
    doc = ready_document(client, h, list(doc_pages), "handbook.pdf")
    conv = new_conversation(client, h)
    use_llm(monkeypatch, "Primary caregivers get sixteen weeks of paid leave [S1].")
    ans = ask(client, h, conv["id"], "How many weeks of paid parental leave do primary caregivers get?").json()["assistant_message"]
    return doc, ans["citations"][0]


def test_citation_highlight_lands_on_the_cited_text(client, monkeypatch):
    h = new_user(client, "a@example.com")
    doc, c = _cited(client, h, monkeypatch=monkeypatch)
    r = client.get(f"{API}/documents/{doc['id']}/highlights", params={"chunk_id": c["chunk_id"]}, headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["page_number"] == c["page_number"] == 1
    assert body["reliable"] is True and body["coverage"] >= 0.6 and body["rects"]
    for rect in body["rects"]:
        assert 0 <= rect["x"] <= 1 and 0 <= rect["y"] <= 1 and rect["w"] > 0 and rect["h"] > 0
        assert rect["x"] + rect["w"] <= 1.001 and rect["y"] + rect["h"] <= 1.001

    # The rectangles really cover the words of the passage: read the text under them back out of the PDF.
    with engine.connect() as conn:
        stored = Path(conn.execute(sql("SELECT storage_path FROM documents WHERE id=:i"), {"i": doc["id"]}).scalar_one())
    pdf = pymupdf.open(stored)
    page = pdf[0]
    w, hgt = page.rect.width, page.rect.height
    under = " ".join(
        page.get_text("text", clip=pymupdf.Rect(r["x"] * w - 1, r["y"] * hgt - 1, (r["x"] + r["w"]) * w + 1, (r["y"] + r["h"]) * hgt + 1))
        for r in body["rects"]
    )
    pdf.close()
    assert "sixteen weeks" in " ".join(under.split())


def test_unlocatable_passage_is_not_highlighted(tmp_path):
    pdf = tmp_path / "x.pdf"
    pdf.write_bytes(make_pdf(["alpha beta gamma delta epsilon zeta eta theta"]))
    result = highlight_service.locate(pdf, 1, "completely different words that never appear anywhere here at all")
    assert result.reliable is False and result.rects == []


def test_highlights_and_pages_are_owner_only_and_validated(client, monkeypatch):
    a, b = new_user(client, "a@example.com"), new_user(client, "b@example.com")
    doc, c = _cited(client, a, monkeypatch=monkeypatch)
    url = f"{API}/documents/{doc['id']}"
    assert client.get(f"{url}/highlights", params={"chunk_id": c["chunk_id"]}, headers=b).status_code == 404
    assert client.get(f"{url}/pages/1/image", headers=b).status_code == 404
    assert client.get(f"{url}/pages/1/image").status_code == 401
    assert client.get(f"{url}/highlights", params={"chunk_id": c["chunk_id"]}).status_code == 401
    # a made-up or foreign chunk id never resolves
    assert client.get(f"{url}/highlights", params={"chunk_id": "chunk-999999"}, headers=a).status_code == 404
    assert client.get(f"{url}/highlights", params={"chunk_id": "nonsense"}, headers=a).status_code == 404
    other = ready_document(client, b, ["Completely unrelated text about gardening and soil."], "garden.pdf")
    foreign = client.get(f"{API}/documents/{other['id']}/highlights", params={"chunk_id": c["chunk_id"]}, headers=b)
    assert foreign.status_code == 404


def test_page_image_is_a_png_and_rejects_bad_pages(client, monkeypatch):
    h = new_user(client, "a@example.com")
    doc, _ = _cited(client, h, monkeypatch=monkeypatch)
    ok = client.get(f"{API}/documents/{doc['id']}/pages/2/image", headers=h)
    assert ok.status_code == 200 and ok.headers["content-type"] == "image/png" and ok.content.startswith(b"\x89PNG")
    assert client.get(f"{API}/documents/{doc['id']}/pages/3/image", headers=h).status_code == 404
    assert client.get(f"{API}/documents/{doc['id']}/pages/0/image", headers=h).status_code == 422
    assert client.get(f"{API}/documents/{doc['id']}/pages/1/image?scale=50", headers=h).status_code == 422
