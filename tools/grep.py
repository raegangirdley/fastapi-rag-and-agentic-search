
from tools.list_files import list_files

MAX_RESULTS = 50

def grep(pattern: str, folder: str = "corpus") -> str:
    """Case-insensitive AND search. Every space-separated term must appear on 
    the same line, in any order. Returns 'file:line: text' matches, up to 
    MAX_RESULTS."""
    terms = pattern.lower().split()
    if not terms:
        return "Empty search pattern. Provide a few keywords."
    matches = []
    for file in list_files(folder):
        with open(file, "r", encoding="utf-8", errors="replace") as f:
            for line_number, line in enumerate(f, start=1):
                lower_line = line.lower()
                if all(term in lower_line for term in terms):
                    matches.append(f"{file:}:{line_number}: {line.strip()}")
                    if len(matches) >= MAX_RESULTS:
                        return "\n".join(matches) + (
                            f"\n[stopped at {MAX_RESULTS} matches; narrow your search]"
                        )
    return "\n".join(matches) if matches else "No matches found."