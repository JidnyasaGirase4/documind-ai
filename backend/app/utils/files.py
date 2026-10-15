import re
from pathlib import PurePosixPath, PureWindowsPath


def display_filename(raw: str | None) -> str:
    """The name shown to users: no directories, no control characters, at most 255 chars."""
    name = (raw or "").strip()
    name = PureWindowsPath(PurePosixPath(name).name).name  # strip both / and \ prefixes
    name = re.sub(r"[\x00-\x1f\x7f]", "", name).strip()
    return (name or "document.pdf")[:255]
