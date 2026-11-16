import pytest
from tools.read_file import read_file
from tools.list_files import list_files

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