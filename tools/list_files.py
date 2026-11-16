import os

from tools.safe_path import safe_path

def list_files(folder: str = "corpus") -> list[str]:
    """List the markdown files under a folder."""
    root_dir = safe_path(folder)
    found = []
    for root, _, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".md"):
                found.append(os.path.relpath(os.path.join(root, file)))
    return sorted(found)