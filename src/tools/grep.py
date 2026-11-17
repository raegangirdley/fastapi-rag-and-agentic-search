from src.tools.list_files import list_files

MAX_RESULTS = 50
FALLBACK_RESULTS = 15
STOP = {"a", "an", "the", "of", "to", "in", "is", "are", "how", "what", "does",
        "do", "for", "and", "or", "it", "its", "that", "this", "with", "on",
        "by", "be", "can", "you", "your", "when", "which"}


def _scan(files, terms, min_hits):
    rows = []
    for file in files:
        with open(file, "r", encoding="utf-8", errors="replace") as f:
            for line_number, line in enumerate(f, start=1):
                low = line.lower()
                hits = sum(term in low for term in terms)
                if hits >= min_hits:
                    rows.append((hits, file, line_number, line.strip()))
    return rows


def grep(pattern: str, folder: str = "corpus") -> str:
    terms = [t for t in pattern.lower().split() if t not in STOP]
    if not terms:
        return "Empty search pattern. Provide a few keywords."

    files = list_files(folder)
    rows = _scan(files, terms, len(terms))
    if rows:
        out = [f"{f}:{n}: {text}" for _, f, n, text in rows[:MAX_RESULTS]]
        if len(rows) >= MAX_RESULTS:
            out.append(f"[stopped at {MAX_RESULTS} matches; narrow your search]")
        return "\n".join(out)

    if len(terms) > 1:
        rows = _scan(files, terms, 2)
        rows.sort(key=lambda r: -r[0])
        if rows:
            out = [f"{f}:{n}: {text}" for _, f, n, text in rows[:FALLBACK_RESULTS]]
            return ("No line contained every term. Closest partial matches:\n"
                    + "\n".join(out))

    return ("No matches found. Try one or two distinctive keywords, such as a "
            "class, function, or option name.")