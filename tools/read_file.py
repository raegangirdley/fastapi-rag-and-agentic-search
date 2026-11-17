from pathlib import Path
import difflib
from tools.safe_path import safe_path
from tools.list_files import list_files

MAX_LINES = 200
MAX_CHARS = 8000

def read_file(path: str, start_line: int = 1, end_line: int = 200) -> str:
    """Read lines start_line to end_line of one markdown file,
    with line numbers."""
    p = safe_path(path)
    if not p.exists():
        msg = f"no such file: {path}."
        try:
            candidates = list_files("corpus")
            name = Path(path).name
            hints = [c for c in candidates if Path(c).name == name] \
                or difflib.get_close_matches(path, candidates, n=3, cutoff=0.4)
        except Exception:
            hints = []
        msg += (" Did you mean: " + ", ".join(hints) + "?") if hints else \
            " Use grep or list_files to find the exact path."
        raise FileNotFoundError(msg)
    if not p.is_file() or p.suffix != ".md":
        raise ValueError(f"not a markdown file: {path}")

    start = max(1, start_line)
    end = min(end_line, start + MAX_LINES - 1)

    lines = []

    with open(p, "r", encoding="utf-8", errors="replace") as f:
        for line_number, line in enumerate(f, start=1):
            if line_number < start:
                continue
            if line_number > end:
                break
            lines.append(f"{line_number}: {line.rstrip()}")

    text = "\n".join(lines)
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS] + "\n[truncated]"
    return text or "No lines in that range."