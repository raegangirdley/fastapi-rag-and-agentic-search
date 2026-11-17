import pytest
from src.tools.read_file import read_file
from src.tools.list_files import list_files
from src.tools.grep import grep

### list_files tests ###

def test_list_files_finds_nested_md(tmp_path, monkeypatch):
    monkeypatch.setattr("src.tools.safe_path.CORPUS_ROOT", tmp_path.resolve())
    (tmp_path / "a.md").write_text("hello")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.md").write_text("world")

    result = list_files(str(tmp_path))

    assert len(result) == 2

def test_list_files_rejects_nonmarkdown(tmp_path, monkeypatch):
    monkeypatch.setattr("src.tools.safe_path.CORPUS_ROOT", tmp_path.resolve())
    (tmp_path / "a.txt").write_text("hello")
    result = list_files(str(tmp_path))
    assert len(result) == 0

### read_files tests ###

def test_read_file_blocks_path_traversal():
    with pytest.raises(ValueError):
        read_file("../secret.txt")

def test_read_file_reads_existing_file(tmp_path, monkeypatch):
    monkeypatch.setattr("src.tools.safe_path.CORPUS_ROOT", tmp_path.resolve())
    monkeypatch.chdir(tmp_path)
    (tmp_path / "test.md").write_text("hello world")
    content = read_file("test.md")
    assert content == "1: hello world"

def test_read_file_blocks_nonexistent_file(tmp_path, monkeypatch):
    monkeypatch.setattr("src.tools.safe_path.CORPUS_ROOT", tmp_path.resolve())
    monkeypatch.chdir(tmp_path)
    with pytest.raises(FileNotFoundError):
        read_file("nonexistent.md")

def test_read_file_rejects_absolute_path_outside_corpus(tmp_path, monkeypatch):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    secret = tmp_path / "secret.md"
    secret.write_text("top secret")
    monkeypatch.setattr("src.tools.safe_path.CORPUS_ROOT", corpus.resolve())
    with pytest.raises(ValueError, match="outside the corpus"):
        read_file(str(secret))

def test_read_gets_requested_range(tmp_path, monkeypatch):
    monkeypatch.setattr("src.tools.safe_path.CORPUS_ROOT", tmp_path.resolve())
    monkeypatch.chdir(tmp_path)
    (tmp_path / "test.md").write_text("\n".join(f"Line {i}" for i in range(1, 21)))
    content = read_file("test.md", start_line=5, end_line=10)
    expected = "\n".join(f"{i}: Line {i}" for i in range(5,11))
    assert content == expected

def test_read_rejects_nonmarkdown_file(tmp_path, monkeypatch):
    monkeypatch.setattr("src.tools.safe_path.CORPUS_ROOT", tmp_path.resolve())
    monkeypatch.chdir(tmp_path)
    (tmp_path / "test.txt").write_text("hello world")
    with pytest.raises(ValueError, match="not a markdown file"):
        read_file("test.txt")

### grep tests ###

def test_grep_caps_at_50(tmp_path, monkeypatch):
    monkeypatch.setattr("src.tools.safe_path.CORPUS_ROOT", tmp_path.resolve())
    for i in range(1, 60):
        (tmp_path / f"file_{i}.md").write_text(f"Line {i}\n")
    result = grep("Line", str(tmp_path))
    lines = result.splitlines()
    assert len(lines) == 51
    assert lines[-1] == "[stopped at 50 matches; narrow your search]"

def test_grep_right_line_numbers(tmp_path, monkeypatch):
    monkeypatch.setattr("src.tools.safe_path.CORPUS_ROOT", tmp_path.resolve())
    (tmp_path / "file.md").write_text("First line\nSecond line\nThird line\n")
    result = grep("Third", str(tmp_path))
    assert result.endswith(":3: Third line")

def test_grep_is_case_insensitive(tmp_path, monkeypatch):
    monkeypatch.setattr("src.tools.safe_path.CORPUS_ROOT", tmp_path.resolve())
    (tmp_path / "file.md").write_text("Hello World\n")
    result = grep("hello", str(tmp_path))
    assert result.endswith(":1: Hello World")

def test_grep_no_matches(tmp_path, monkeypatch):
    monkeypatch.setattr("src.tools.safe_path.CORPUS_ROOT", tmp_path.resolve())
    (tmp_path / "file.md").write_text("Hello World\n")
    result = grep("nonexistent", str(tmp_path))
    assert result.startswith("No matches found.")
    assert "distinctive keywords" in result