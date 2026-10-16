"""Text comparison of two document versions. Pure functions over extracted text units, so it is reusable and testable
without a database, and no text is ever sent to an LLM.

Units are sentences within paragraph blocks (see pdf_service.extract_units). They are aligned with difflib's
SequenceMatcher (deterministic), so inserting a paragraph or moving text to another page does not mark everything after it
as changed: page numbers are reported but not compared. Replaced units get a word-level diff inside the change."""

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from app.services.pdf_service import TextUnit

MAX_UNITS = 4000  # per version; larger documents are reported as not comparable instead of hanging the server
CONTEXT = 1  # unchanged units kept around a change
NOTICE = (
    "This compares the extracted text only. It does not detect visual or layout changes (images, fonts, tables drawn as "
    "graphics, page design), and text extracted in a different order may appear as a change."
)
_TOKEN = re.compile(r"\s+|[\w'-]+|[^\w\s]")


@dataclass
class Comparison:
    comparable: bool
    reason: str | None
    stats: dict
    blocks: list[dict]


def _key(text: str) -> str:
    return " ".join(text.split())


def _unit(u: TextUnit) -> dict:
    return {"page": u.page_number, "text": u.text}


def _word_diff(old: str, new: str) -> list[dict]:
    a, b = _TOKEN.findall(old), _TOKEN.findall(new)
    out: list[dict] = []

    def push(op: str, tokens: list[str]) -> None:
        text = "".join(tokens)
        if not text:
            return
        if out and out[-1]["op"] == op:
            out[-1]["text"] += text
        else:
            out.append({"op": op, "text": text})

    for tag, i1, i2, j1, j2 in SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == "equal":
            push("equal", a[i1:i2])
        else:
            push("del", a[i1:i2])
            push("ins", b[j1:j2])
    return out


def compare_units(old: list[TextUnit], new: list[TextUnit]) -> Comparison:
    if len(old) > MAX_UNITS or len(new) > MAX_UNITS:
        return Comparison(False, "This document is too large to compare reliably in the browser.", _stats(0, 0, 0, 0), [])
    sm = SequenceMatcher(None, [_key(u.text) for u in old], [_key(u.text) for u in new], autojunk=False)
    ops = sm.get_opcodes()
    blocks: list[dict] = []
    added = removed = changed = unchanged = 0
    last = len(ops) - 1
    for n, (tag, i1, i2, j1, j2) in enumerate(ops):
        if tag == "equal":
            unchanged += i2 - i1
            count = i2 - i1
            head = 0 if n == 0 else CONTEXT
            tail = 0 if n == last else CONTEXT
            if count <= head + tail:
                shown = [(old[i], new[j1 + (i - i1)]) for i in range(i1, i2)]
                skipped = 0
            else:
                shown = [(old[i], new[j1 + (i - i1)]) for i in list(range(i1, i1 + head)) + list(range(i2 - tail, i2))]
                skipped = count - head - tail
            if skipped:
                for o, nw in shown[:head]:
                    blocks.append({"type": "equal", "old": [_unit(o)], "new": [_unit(nw)]})
                blocks.append({"type": "skipped", "count": skipped})
                for o, nw in shown[head:]:
                    blocks.append({"type": "equal", "old": [_unit(o)], "new": [_unit(nw)]})
            else:
                for o, nw in shown:
                    blocks.append({"type": "equal", "old": [_unit(o)], "new": [_unit(nw)]})
        elif tag == "delete":
            removed += i2 - i1
            blocks.append({"type": "removed", "old": [_unit(u) for u in old[i1:i2]], "new": []})
        elif tag == "insert":
            added += j2 - j1
            blocks.append({"type": "added", "old": [], "new": [_unit(u) for u in new[j1:j2]]})
        else:  # replace
            changed += max(i2 - i1, j2 - j1)
            blocks.append(
                {
                    "type": "changed",
                    "old": [_unit(u) for u in old[i1:i2]],
                    "new": [_unit(u) for u in new[j1:j2]],
                    "inline": _word_diff(" ".join(u.text for u in old[i1:i2]), " ".join(u.text for u in new[j1:j2])),
                }
            )
    return Comparison(True, None, _stats(added, removed, changed, unchanged), blocks)


def _stats(added: int, removed: int, changed: int, unchanged: int) -> dict:
    return {"added": added, "removed": removed, "changed": changed, "unchanged": unchanged, "identical": added == removed == changed == 0}
