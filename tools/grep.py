
from tools.list_files import list_files

MAX_RESULTS = 50

def grep(pattern: str, folder: str = "corpus") -> str:
    """Case-insensitive search of markdown files.
    Returns 'file:line: text' for each match, up to MAX_RESULTS matches."""
    needle = pattern.lower()
    matches = []
    files = list_files(folder)
    results = []
    for file in list_files(folder):
        with open(file, "r", encoding="utf-8", errors="replace") as f:
            for line_number, line in enumerate(f, start=1):
                if needle in line.lower():
                    matches.append(f"{file:}:{line_number}: {line.strip()}")
                    if len(matches) >= MAX_RESULTS:
                        return "\n".join(matches) + (
                            f"\n[stopped at {MAX_RESULTS} matches; narrow your search]"
                        )
    return "\n".join(matches) if matches else "No matches found."