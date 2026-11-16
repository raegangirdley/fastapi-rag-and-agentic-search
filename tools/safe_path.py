from pathlib import Path

CORPUS_ROOT = Path("corpus").resolve()

def safe_path(user_path: str) -> Path:
    """Resolve a path and make sure it stays inside corpus folder."""
    p = Path(user_path).resolve()
    if not p.is_relative_to(CORPUS_ROOT):
        raise ValueError(f"Path is outside corpus folder: {user_path}")
    return p