import pytest
from tools.read_file import read_file
from tools.list_files import list_files
from tools.grep import grep

def test_list_files_finds_nested_md(tmp_path, monkeypatch):
    monkeypatch.setattr("tools.safe_path.CORPUS_ROOT", tmp_path.resolve())
    (tmp_path / "a.md").write_text("hello")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.md").write_text("world")

    result = list_files(str(tmp_path))

    assert len(result) == 2

def test_read_file_blocks_path_traversal():
    with pytest.raises(ValueError):
        read_file("../secret.txt")

def test_read_file_reads_existing_file(tmp_path, monkeypatch):
    monkeypatch.setattr("tools.safe_path.CORPUS_ROOT", tmp_path.resolve())
    monkeypatch.chdir(tmp_path)
    (tmp_path / "test.md").write_text("hello world")
    content = read_file("test.md")
    assert content == "1: hello world"

def test_read_file_blocks_nonexistent_file(tmp_path, monkeypatch):
    monkeypatch.setattr("tools.safe_path.CORPUS_ROOT", tmp_path.resolve())
    monkeypatch.chdir(tmp_path)
    with pytest.raises(FileNotFoundError):
        read_file("nonexistent.md")

def test_read_file_rejects_absolute_path(tmp_path, monkeypatch):
    monkeypatch.setattr("tools.safe_path.CORPUS_ROOT", tmp_path.resolve())
    with pytest.raises(ValueError):
        read_file(str(tmp_path / "test.md"))

def test_grep_up_to_50(tmp_path, monkeypatch):
    monkeypatch.setattr("tools.safe_path.CORPUS_ROOT", tmp_path.resolve())
    for i in range(1, 60):
        (tmp_path / f"file_{i}.md").write_text(f"Line {i}\n")
    result = grep("Line", str(tmp_path))
    lines = result.splitlines()

    assert len(lines) == 51
    assert lines[-1] == "[stopped at 50 matches; narrow your search]"