"""Builds DocuMind_AI_User_Guide.pdf from guide_content.py and the screenshots in ./screenshots.

    cd backend && python ../docs/user-guide/build_user_guide.py [output.pdf]

Uses PyMuPDF (already a backend dependency). Every block (heading, paragraph, list item, table row group, picture) is laid out as
its own small HTML+CSS "Story", measured, and placed by this script's own page-flow code. That keeps pictures at full size, repeats
table headers on continuation pages and never splits a block badly. The contents page is built in two passes, so its page numbers
are measured, not guessed. After writing, the script re-reads the PDF and fails if a chapter is not on the page the contents claims,
if a picture was shrunk, or if the text cannot be extracted."""

import html
import io
import sys
import unicodedata
from pathlib import Path

import pymupdf

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import guide_content as G  # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parent.parent / "DocuMind_AI_User_Guide.pdf"
SHOTS = HERE / "screenshots"
PAGE = pymupdf.paper_rect("a4")
LEFT, RIGHT, TOP, BOTTOM = 56, PAGE.width - 56, 60, PAGE.height - 66
WIDTH = RIGHT - LEFT
MAX_IMG_W = int(WIDTH) - 8

CSS = """
body { font-family: sans-serif; font-size: 10.5pt; line-height: 1.35; color: #2b2528; margin: 0; padding: 0; }
h1 { font-size: 20pt; color: #8a1c3c; margin: 0; padding: 0 0 5pt 0; border-bottom: 1.5pt solid #8a1c3c; }
h2 { font-size: 13pt; color: #3b3b44; margin: 0; padding: 0; }
p { margin: 0; padding: 0; }
b { color: #1c181b; }
.item { margin: 0 0 0 16pt; text-indent: -16pt; }
table { width: 100%; border-collapse: collapse; }
td.hd { background-color: #8a1c3c; color: #ffffff; font-weight: bold; text-align: left; font-size: 9.5pt; padding: 4pt 5pt; border: 0.5pt solid #8a1c3c; }
td { font-size: 9.5pt; padding: 4pt 5pt; border: 0.5pt solid #d9d2d4; vertical-align: top; }
.box { padding: 6pt 9pt; font-size: 10pt; }
.note { background-color: #f3f1ef; border-left: 3pt solid #64748b; }
.tip { background-color: #eaf6ee; border-left: 3pt solid #15803d; }
.warn, .important { background-color: #fdf0ef; border-left: 3pt solid #c8281c; }
.figure { text-align: center; }
.caption { font-size: 8.5pt; color: #5d5558; text-align: center; }
.cover-title { font-size: 34pt; color: #8a1c3c; }
.cover-sub { font-size: 14pt; color: #3b3b44; }
.cover-meta { font-size: 10.5pt; color: #5d5558; }
.toc td { border: 0; border-bottom: 0.5pt solid #e6e0e2; font-size: 10.5pt; padding: 4pt 2pt; }
.pg { text-align: right; color: #8a1c3c; }
"""


def inline(s: str) -> str:
    """Content strings may contain <b> and <i> only; everything else is escaped."""
    out = html.escape(s, quote=False)
    for tag in ("b", "i"):
        out = out.replace(f"&lt;{tag}&gt;", f"<{tag}>").replace(f"&lt;/{tag}&gt;", f"</{tag}>")
    return out


def titles() -> dict[str, str]:
    t = {"howto": "Using this guide"}
    t.update({c["id"]: f"{i}. {c['title']}" for i, c in enumerate(G.CHAPTERS, 1)})
    t["appendix"] = "Appendix: about this guide"
    return t


def squash(s: str) -> str:
    return "".join(unicodedata.normalize("NFKC", s).split())  # the PDF font uses ligatures such as "fl"


class Flow:
    """Places measured HTML fragments onto A4 pages."""

    def __init__(self):
        self.buf = io.BytesIO()
        self.writer = pymupdf.DocumentWriter(self.buf)
        self.dev = None
        self.page_no = 0
        self.y = TOP
        self.archive = pymupdf.Archive(str(SHOTS))
        self.image_widths: list[tuple[str, float]] = []

    # -- page handling
    def new_page(self):
        if self.dev is not None:
            self.writer.end_page()
        self.dev = self.writer.begin_page(PAGE)
        self.page_no += 1
        self.y = TOP

    def finish(self) -> bytes:
        if self.dev is not None:
            self.writer.end_page()
        self.writer.close()
        return self.buf.getvalue()

    # -- measuring / drawing
    def _story(self, frag: str) -> pymupdf.Story:
        return pymupdf.Story(html=frag, user_css=CSS, em=11, archive=self.archive)

    def height(self, frag: str) -> float:
        more, filled = self._story(frag).place(pymupdf.Rect(LEFT, 0, RIGHT, 5000))
        return filled[3] if not more else 5000

    def put(self, frag: str, gap_before: float = 0, gap_after: float = 0, keep: float = 0) -> None:
        """Draw `frag` at the current position; start a new page first if it (plus `keep` points that must follow) does not fit."""
        h = self.height(frag)
        if self.dev is None or self.y + gap_before + h + keep > BOTTOM:
            self.new_page()
            gap_before = 0
        self.y += gap_before
        story = self._story(frag)
        story.place(pymupdf.Rect(LEFT, self.y, RIGHT, self.y + h + 2))
        story.draw(self.dev)
        self.y += h + gap_after

    def need(self, points: float) -> None:
        if self.dev is None or self.y + points > BOTTOM:
            self.new_page()

    def table(self, head, rows, widths, gap_before=4, gap_after=9) -> None:
        def frag(rs):
            ths = "".join(f'<td class="hd" width="{w}%">{inline(h)}</td>' for h, w in zip(head, widths))
            trs = "".join("<tr>" + "".join(f'<td width="{w}%">{inline(c)}</td>' for c, w in zip(r, widths)) + "</tr>" for r in rs)
            return f"<table><tr>{ths}</tr>{trs}</table>"

        i = 0
        first = True
        while i < len(rows):
            room = BOTTOM - self.y - (gap_before if first else 0)
            n = 0
            while i + n < len(rows) and self.height(frag(rows[i : i + n + 1])) <= room:
                n += 1
            if n == 0:
                if self.y > TOP + 1:
                    self.new_page()
                    first = False
                    continue
                n = 1  # a single row taller than a page cannot happen with this content; avoid an endless loop anyway
            self.put(frag(rows[i : i + n]), gap_before if first else 0)
            i += n
            first = False
            if i < len(rows):
                self.new_page()
        self.y += gap_after

    def picture(self, name: str, caption: str, width: int) -> None:
        w = min(width, MAX_IMG_W)
        frag = f'<div class="figure"><img src="{name}" width="{w}"/><p class="caption">{inline(caption)}</p></div>'
        self.put(frag, gap_before=6, gap_after=10)
        self.image_widths.append((name, w))


def render(pages: dict[str, int] | None) -> tuple[bytes, dict[str, int]]:
    f = Flow()
    heads: dict[str, int] = {}
    # cover
    f.new_page()
    f.y = 190
    f.put(f'<p class="cover-title">{inline(G.TITLE)}</p>', gap_after=6)
    f.put('<p class="cover-sub">Search, ask, share, version and review your PDF knowledge</p>', gap_after=26)
    f.put(f'<p class="cover-meta"><b>Version {G.VERSION}</b></p>', gap_after=3)
    f.put(f'<p class="cover-meta">{inline(G.DATE)}</p>', gap_after=3)
    f.put('<p class="cover-meta">For people who use DocuMind AI every day. No technical knowledge is needed.</p>')
    # contents
    f.new_page()
    f.put('<h1>Contents</h1>', gap_after=10)
    rows = ""
    for key, title in titles().items():
        n = pages.get(key, 0) if pages else 0
        rows += f'<tr><td>{inline(title)}</td><td class="pg" width="10%">{n:02d}</td></tr>'
    f.put(f'<table class="toc">{rows}</table>')

    def chapter(key: str, title: str, blocks) -> None:
        f.new_page()
        heads[key] = f.page_no
        f.put(f"<h1>{inline(title)}</h1>", gap_after=10)
        for b in blocks:
            kind = b[0]
            if kind == "p":
                f.put(f"<p>{inline(b[1])}</p>", gap_after=7)
            elif kind == "h2":
                f.need(70)
                f.put(f"<h2>{inline(b[1])}</h2>", gap_before=8, gap_after=5, keep=34)
            elif kind in ("steps", "bullets"):
                for n, item in enumerate(b[1], 1):
                    mark = f"{n}." if kind == "steps" else "&#8226;"
                    f.put(f'<p class="item">{mark}&nbsp;&nbsp;{inline(item)}</p>', gap_after=3)
                f.y += 5
            elif kind in ("note", "tip", "warn", "important"):
                label = {"note": "Note", "tip": "Tip", "warn": "Important", "important": "Important"}[kind]
                f.put(f'<div class="box {kind}"><b>{label}:</b> {inline(b[1])}</div>', gap_before=3, gap_after=10)
            elif kind == "table":
                f.table(b[1], b[2], b[3])
            elif kind == "img":
                if not (SHOTS / b[1]).is_file():
                    raise FileNotFoundError(f"screenshot missing: {b[1]}")
                f.picture(b[1], b[2], b[3])
            else:
                raise ValueError(kind)

    chapter("howto", "Using this guide", G.INTRO_HOW_TO_USE)
    for i, c in enumerate(G.CHAPTERS, 1):
        chapter(c["id"], f"{i}. {c['title']}", c["blocks"])
    chapter("appendix", "Appendix: about this guide", G.APPENDIX)
    return f.finish(), heads


def main() -> None:
    _, pages = render(None)  # pass 1: measure on which page each chapter starts
    data, pages2 = render(pages)  # pass 2: same layout with the real page numbers
    if pages2 != pages:
        raise SystemExit(f"table of contents unstable between passes: {pages} vs {pages2}")
    T = titles()

    doc = pymupdf.open(stream=data, filetype="pdf")
    total = doc.page_count
    doc.set_toc([[1, T[k], p] for k, p in pages2.items()])
    for pno in range(1, total):  # footer on every page except the cover
        page = doc[pno]
        r = page.rect
        page.draw_line((LEFT, r.height - 46), (RIGHT, r.height - 46), color=(0.85, 0.82, 0.83), width=0.5)
        page.insert_text((LEFT, r.height - 32), f"{G.TITLE}  |  Version {G.VERSION}  |  {G.DATE}", fontsize=8, color=(0.4, 0.37, 0.39))
        label = f"Page {pno + 1} of {total}"
        page.insert_text((RIGHT - pymupdf.get_text_length(label, fontsize=8), r.height - 32), label, fontsize=8, color=(0.4, 0.37, 0.39))
    doc.set_metadata({
        "title": G.TITLE, "author": "DocuMind AI", "subject": "End-user manual", "keywords": "DocuMind AI, user guide, search, versions, reviews, conflicts",
        "creator": "docs/user-guide/build_user_guide.py (PyMuPDF)",
    })
    doc.save(OUT, garbage=4, deflate=True)
    doc.close()

    # ---- verification
    check = pymupdf.open(OUT)
    problems = []
    for key, pno in pages2.items():
        if squash(T[key])[:34] not in squash(check[pno - 1].get_text()):
            problems.append(f"'{T[key]}' is not on page {pno}")
    toc_text = check[1].get_text()
    for key, pno in pages2.items():
        if f"{pno:02d}" not in toc_text:
            problems.append(f"contents lacks page number {pno:02d} for '{T[key]}'")
    if list(pages2) != list(T):
        problems.append("chapters missing or out of order")
    wanted = [b for c in G.CHAPTERS for b in c["blocks"] if b[0] == "img"]
    sizes = [(i["bbox"][2] - i["bbox"][0]) for pg in check for i in pg.get_image_info()]
    if len(sizes) != len(wanted):
        problems.append(f"expected {len(wanted)} pictures, found {len(sizes)}")
    for (_k, name, _c, width), got in zip(wanted, sizes):
        if got < 0.9 * min(width, MAX_IMG_W):
            problems.append(f"picture {name} was shrunk to {got:.0f}pt (wanted {min(width, MAX_IMG_W)}pt)")
    for pg in check:  # body text must not run into the footer area
        for x0, y0, x1, y1, text, *_ in pg.get_text("blocks"):
            if y1 > pg.rect.height - 48 and y0 < pg.rect.height - 48 and "Page " not in text and "User Guide" not in text:
                problems.append(f"page {pg.number + 1}: text runs into the footer area")
    if len(check.get_toc()) != len(T):
        problems.append("bookmarks missing")
    if problems:
        raise SystemExit("VERIFICATION FAILED:\n  " + "\n  ".join(problems))
    print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB, {check.page_count} pages, {len(G.CHAPTERS)} chapters + intro + appendix); contents, pictures and margins verified")


if __name__ == "__main__":
    main()
