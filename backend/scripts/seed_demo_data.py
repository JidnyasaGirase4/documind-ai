"""Adds realistic sample data (engineering policies and runbooks) to a DocuMind AI account through the normal HTTP API.

    python scripts/seed_demo_data.py [--api http://127.0.0.1:8001] [--email demo@example.com] [--password DocuMind2026]

Creates PDFs in a temporary folder, uploads them, then adds collections, categories, tags, review schedules, one review, a second
version of one document and two deliberately conflicting policies (so conflict detection has something to find). It only adds
data and skips files that already exist for the account (by file name), so it can be run again safely. Development use only."""

import argparse
import sys
import tempfile
import time
from datetime import date, timedelta
from pathlib import Path

import pymupdf
import requests

DOCS = {
    "api-security-guidelines.pdf": [
        "API Security Guidelines (2026)\n\nAll public endpoints must be served over HTTPS with TLS 1.2 or newer. Access tokens expire after 15 minutes and refresh tokens after 7 days.\n\nService and user passwords must be rotated every 90 days. Secrets such as database passwords and API keys must be stored in the secrets vault, never in source code or environment files committed to git.\n\nEvery public API must enforce a rate limit of 100 requests per minute per client and return HTTP 429 when the limit is exceeded.",
        "Input validation and logging\n\nAll request bodies must be validated against a schema before use. Application logs must never contain passwords, tokens or full card numbers. Security-relevant events such as failed logins and permission changes must be written to the audit log.\n\nDependencies must be scanned for known vulnerabilities on every pull request and critical findings must be fixed within 7 days.",
    ],
    "security-baseline-2023.pdf": [
        "Security Baseline (2023, legacy)\n\nPasswords must be rotated every 180 days. Access tokens are valid for 60 minutes.\n\nApplication logs must be retained for 30 days and then deleted. Vulnerabilities of critical severity must be fixed within 30 days.",
    ],
    "git-workflow-and-code-review.pdf": [
        "Git Workflow and Code Review\n\nBranches are named feature/<ticket>, fix/<ticket> or hotfix/<ticket>. The main branch is protected: direct pushes are not allowed.\n\nEvery pull request needs at least 2 approvals and a passing CI pipeline before it can be merged. Pull requests are merged with squash. Reviewers should respond within 1 business day.",
        "Releases and hotfixes\n\nRegular releases are made every second Tuesday. A hotfix must be reviewed and deployed within 24 hours of the incident declaration. Every release is tagged with a semantic version number, for example v2.4.1, and the changelog is updated before the tag is created.",
    ],
    "incident-response-runbook.pdf": [
        "Incident Response Runbook\n\nSeverity 1 incidents (production down or data loss) must be acknowledged within 15 minutes by the on-call engineer. Severity 2 incidents must be acknowledged within 1 hour.\n\nThe incident commander posts an update on the status page every 30 minutes until the incident is resolved. The on-call rotation changes weekly on Monday at 09:00 UTC.",
        "After the incident\n\nA blameless postmortem must be written within 5 business days of every Severity 1 incident. The postmortem lists the timeline, the root cause, what went well and the follow-up actions with owners and due dates.",
    ],
    "database-backup-and-retention.pdf": [
        "Database Backup and Retention Standard\n\nProduction databases are backed up every night at 02:00 UTC. Nightly backups are retained for 30 days. Application and audit logs are retained for 90 days before deletion.\n\nRecovery point objective (RPO) is 24 hours and recovery time objective (RTO) is 4 hours. A restore test must be performed every quarter and the result recorded.",
    ],
    "developer-onboarding-guide.pdf": [
        "Developer Onboarding Guide\n\nDay 1: receive your laptop, set up two-factor authentication and request access to the repositories and the staging environment. Day 2: clone the monorepo, run the setup script and start the backend and the frontend locally.\n\nBackend: Python 3.11 with FastAPI and a MySQL database. Frontend: React with Vite. Run the test suites before every pull request.",
        "First week\n\nPair with a buddy on a starter ticket, attend the architecture walkthrough and read the API security guidelines and the git workflow. By Friday you should have your first pull request merged.",
    ],
}

NEW_VERSION = {
    "git-workflow-and-code-review.pdf": [
        "Git Workflow and Code Review (updated)\n\nBranches are named feature/<ticket>, fix/<ticket> or hotfix/<ticket>. The main branch is protected: direct pushes are not allowed.\n\nEvery pull request needs at least 2 approvals, 3 for repositories that deploy to production, and a passing CI pipeline before it can be merged. Pull requests are merged with squash. Reviewers should respond within 1 business day.",
        DOCS["git-workflow-and-code-review.pdf"][1],
    ]
}

COLLECTIONS = {
    "Engineering Policies": ("burgundy", "scale", "Security and engineering process policies", ["api-security-guidelines.pdf", "security-baseline-2023.pdf", "git-workflow-and-code-review.pdf"]),
    "Operations Runbooks": ("emerald", "shield", "Incident response and data protection", ["incident-response-runbook.pdf", "database-backup-and-retention.pdf"]),
    "Onboarding": ("sky", "book", "Material for new developers", ["developer-onboarding-guide.pdf"]),
}
CATEGORY = {
    "api-security-guidelines.pdf": "Security", "security-baseline-2023.pdf": "Security", "git-workflow-and-code-review.pdf": "Engineering Process",
    "incident-response-runbook.pdf": "Operations", "database-backup-and-retention.pdf": "Operations", "developer-onboarding-guide.pdf": "Onboarding",
}
TAGS = {
    "api-security-guidelines.pdf": ["security", "api", "2026"], "security-baseline-2023.pdf": ["security", "legacy"], "git-workflow-and-code-review.pdf": ["git", "code-review"],
    "incident-response-runbook.pdf": ["incident", "on-call"], "database-backup-and-retention.pdf": ["backup", "retention"], "developer-onboarding-guide.pdf": ["onboarding"],
}
REVIEWS = {  # days until the next review, repeat interval
    "api-security-guidelines.pdf": (10, 90), "security-baseline-2023.pdf": (3, 180), "git-workflow-and-code-review.pdf": (60, 180),
    "incident-response-runbook.pdf": (25, 90), "database-backup-and-retention.pdf": (45, 90),
}


def make_pdf(path: Path, pages: list[str]) -> None:
    doc = pymupdf.open()
    for body in pages:
        page = doc.new_page()
        page.insert_textbox(pymupdf.Rect(50, 50, 545, 790), body, fontsize=11)
    doc.save(path)
    doc.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://127.0.0.1:8001")
    ap.add_argument("--email", default="demo@example.com")
    ap.add_argument("--password", default="DocuMind2026")
    a = ap.parse_args()
    base = a.api.rstrip("/") + "/api/v1"
    r = requests.post(f"{base}/auth/login", json={"email": a.email, "password": a.password}, timeout=30)
    if r.status_code != 200:
        print("Login failed:", r.status_code, r.text[:200])
        return 1
    h = {"Authorization": "Bearer " + r.json()["access_token"]}

    def call(method, path, **kw):
        resp = requests.request(method, base + path, headers=h, timeout=120, **kw)
        return resp

    existing = {d["filename"] if "filename" in d else d["original_filename"]: d for d in call("GET", "/documents", params={"page_size": 100}).json()["items"]}
    tmp = Path(tempfile.mkdtemp(prefix="documind-seed-"))
    ids: dict[str, int] = {}
    for name, pages in DOCS.items():
        if name in existing:
            ids[name] = existing[name]["id"]
            print("exists   ", name)
            continue
        make_pdf(tmp / name, pages)
        resp = call("POST", "/documents/upload", files={"file": (name, (tmp / name).read_bytes(), "application/pdf")})
        resp.raise_for_status()
        ids[name] = resp.json()["id"]
        print("uploaded ", name)
    print("waiting for processing ...")
    for _ in range(120):
        states = [call("GET", f"/documents/{i}").json()["processing_status"] for i in ids.values()]
        if all(s in ("ready", "failed") for s in states):
            break
        time.sleep(2)
    print("statuses:", sorted(set(states)))

    cats = {c["name"]: c["id"] for c in call("GET", "/categories").json()}
    for name in set(CATEGORY.values()):
        if name not in cats:
            cats[name] = call("POST", "/categories", json={"name": name}).json()["id"]
    colls = {c["name"]: c["id"] for c in call("GET", "/collections", params={"page_size": 100, "scope": "owned"}).json()["items"]}
    for name, (color, icon, desc, files) in COLLECTIONS.items():
        if name not in colls:
            colls[name] = call("POST", "/collections", json={"name": name, "description": desc, "color": color, "icon": icon}).json()["id"]
        call("POST", f"/collections/{colls[name]}/documents", json={"document_ids": [ids[f] for f in files]})
    for name, did in ids.items():
        call("PATCH", f"/documents/{did}/metadata", json={"category_id": cats[CATEGORY[name]], "tags": TAGS[name]})
    print("collections, categories and tags set")

    for name, (days, interval) in REVIEWS.items():
        r = call("PUT", f"/documents/{ids[name]}/review", json={"next_review_date": (date.today() + timedelta(days=days)).isoformat(), "interval_days": interval})
        if r.status_code != 200:
            print("review schedule failed", name, r.text[:120])
    done = call("GET", f"/documents/{ids['api-security-guidelines.pdf']}/review/history").json()["total"]
    if not done:
        call("POST", f"/documents/{ids['api-security-guidelines.pdf']}/review/complete", json={"outcome": "approved", "notes": "Checked against the 2026 security standard."})
    print("review schedules set")

    gid = ids["git-workflow-and-code-review.pdf"]
    if len(call("GET", f"/documents/{gid}/versions").json()) < 2:
        make_pdf(tmp / "git-v2.pdf", NEW_VERSION["git-workflow-and-code-review.pdf"])
        resp = call("POST", f"/documents/{gid}/versions", files={"file": ("git-workflow-and-code-review.pdf", (tmp / "git-v2.pdf").read_bytes(), "application/pdf")}, data={"change_note": "Production repositories now need 3 approvals"})
        print("version 2 uploaded" if resp.status_code == 202 else f"version upload: {resp.status_code} {resp.text[:120]}")
    print("done. Log in as", a.email, "- the Policies collections conflict on password rotation (90 vs 180 days) and log retention (30 vs 90 days).")
    print("To look for conflicts: open security-baseline-2023.pdf -> Analyze for conflicts (needs the AI model running).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
