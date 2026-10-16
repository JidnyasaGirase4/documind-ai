"""Records the data of the public demo site from a RUNNING DocuMind AI backend that holds the sample data
(run scripts/seed_demo_data.py first). Everything in the demo is a real response of the real backend for the demo account:
list/detail/version/review/conflict/analytics JSON, rendered PDF pages, citation highlight rectangles, the PDF files and the text
passages used by the demo's simple search. Nothing is invented here.

    cd backend && python scripts/record_demo_fixtures.py [--api http://127.0.0.1:8001] [--no-chats]

Writes frontend/src/demo/fixtures.json and frontend/public/demo/{pages,pdfs}/. Development tool only."""

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
OUT_JSON = ROOT / "frontend" / "src" / "demo" / "fixtures.json"
OUT_PUBLIC = ROOT / "frontend" / "public" / "demo"
QUESTIONS = ["Within how many minutes must a Severity 1 incident be acknowledged?", "How many approvals does a pull request need?"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://127.0.0.1:8001")
    ap.add_argument("--email", default="demo@example.com")
    ap.add_argument("--password", default="DocuMind2026")
    ap.add_argument("--no-chats", action="store_true")
    a = ap.parse_args()
    base = a.api.rstrip("/") + "/api/v1"
    tok = requests.post(f"{base}/auth/login", json={"email": a.email, "password": a.password}, timeout=30).json()["access_token"]
    h = {"Authorization": "Bearer " + tok}
    get = lambda p, **k: requests.get(base + p, headers=h, timeout=120, **k)  # noqa: E731
    j = lambda p, **k: get(p, **k).json()  # noqa: E731

    fx: dict = {"recorded_from": "DocuMind AI backend with the sample data (scripts/seed_demo_data.py)"}
    fx["user"] = j("/auth/me")
    fx["dashboard_stats"], fx["dashboard_activity"] = j("/dashboard/stats"), j("/dashboard/activity")
    fx["analytics"] = {k: j(f"/analytics/{k}") for k in ("overview", "feedback", "queries", "evaluations")}
    docs = j("/documents", params={"page_size": 100})["items"]
    fx["documents"] = docs
    fx["collections"] = j("/collections", params={"page_size": 100})["items"]
    fx["members"] = {str(c["id"]): j(f"/collections/{c['id']}/members") for c in fx["collections"]}
    fx["categories"], fx["tags"] = j("/categories"), j("/tags")
    fx["versions"], fx["compare"], fx["review"], fx["review_history"] = {}, {}, {}, {}
    shutil.rmtree(OUT_PUBLIC, ignore_errors=True)
    (OUT_PUBLIC / "pages").mkdir(parents=True)
    (OUT_PUBLIC / "pdfs").mkdir(parents=True)
    files = {"pages": [], "pdfs": []}
    for d in docs:
        did = d["id"]
        vs = j(f"/documents/{did}/versions")
        fx["versions"][str(did)] = vs
        fx["review"][str(did)] = j(f"/documents/{did}/review")
        fx["review_history"][str(did)] = j(f"/documents/{did}/review/history", params={"page_size": 50})
        for v in vs:
            pdf = get(f"/documents/{did}/versions/{v['id']}/download")
            (OUT_PUBLIC / "pdfs" / f"{v['id']}.pdf").write_bytes(pdf.content)
            files["pdfs"].append({"version_id": v["id"], "file": f"pdfs/{v['id']}.pdf"})
            for n in range(1, (v.get("total_pages") or 1) + 1):
                img = get(f"/documents/{did}/pages/{n}/image", params={"version_id": v["id"], "scale": 1.5})
                if img.status_code == 200:
                    (OUT_PUBLIC / "pages" / f"{v['id']}-{n}.png").write_bytes(img.content)
                    files["pages"].append({"version_id": v["id"], "page": n, "file": f"pages/{v['id']}-{n}.png"})
        for x in vs:
            for y in vs:
                if x["id"] != y["id"] and x["version_number"] < y["version_number"]:
                    fx["compare"][f"{did}:{x['id']}:{y['id']}"] = j(f"/documents/{did}/versions/compare", params={"from": x["id"], "to": y["id"]})
    fx["files"] = files
    fx["reviews_list"] = j("/reviews", params={"page_size": 100})["items"]
    fx["review_summary"] = j("/reviews/summary")
    fx["conflicts"] = j("/conflicts", params={"page_size": 50})["items"]
    fx["decisions"] = {str(c["id"]): j(f"/conflicts/{c['id']}/decisions") for c in fx["conflicts"]}
    fx["reports"] = j("/conflicts/reports", params={"page_size": 20})["items"]

    # passages (the demo's search and chat work on these) and the real highlight rectangles of every one of them
    from sqlalchemy import select

    from app.db.session import SessionLocal
    from app.models.document import Document, DocumentChunk, DocumentVersion

    chunks, highlights = [], {}
    with SessionLocal() as db:
        mine = {d["id"]: d for d in docs}
        cur = {d["id"]: d["version_number"] for d in docs}
        rows = db.execute(
            select(DocumentChunk, DocumentVersion.version_number, Document.current_version_id)
            .join(DocumentVersion, DocumentVersion.id == DocumentChunk.version_id)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(DocumentChunk.document_id.in_(list(mine)))
            .order_by(DocumentChunk.document_id, DocumentChunk.version_id, DocumentChunk.chunk_index)
        ).all()
        for c, vnum, current_vid in rows:
            chunks.append({"id": c.id, "chunk_id": f"chunk-{c.id}", "document_id": c.document_id, "version_id": c.version_id, "version_number": vnum,
                           "page": c.page_number, "text": " ".join(c.extracted_text.split()), "is_current": c.version_id == current_vid})
    for c in chunks:
        r = get(f"/documents/{c['document_id']}/highlights", params={"chunk_id": c["chunk_id"]})
        if r.status_code == 200:
            highlights[c["chunk_id"]] = r.json()
    fx["chunks"], fx["highlights"] = chunks, highlights

    if not a.no_chats:  # two real conversations answered by the real backend (needs the AI model)
        convs = []
        for q in QUESTIONS:
            cv = requests.post(f"{base}/conversations", headers=h, json={}).json()
            t = time.time()
            requests.post(f"{base}/conversations/{cv['id']}/messages", headers=h, json={"content": q}, timeout=300)
            convs.append(j(f"/conversations/{cv['id']}"))
            print(f"recorded chat in {int(time.time() - t)}s:", q)
            requests.delete(f"{base}/conversations/{cv['id']}", headers=h)  # leave your own data as it was
        fx["conversations"] = convs
    else:
        fx["conversations"] = []

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(fx, ensure_ascii=False, indent=1), encoding="utf-8")
    size = OUT_JSON.stat().st_size // 1024
    print(f"wrote {OUT_JSON} ({size} KB), {len(files['pages'])} page images, {len(files['pdfs'])} PDFs, {len(chunks)} passages, {len(highlights)} highlights")
    return 0


if __name__ == "__main__":
    sys.exit(main())
