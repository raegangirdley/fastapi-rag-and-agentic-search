from src.rag import chunk_file

def test_chunk_file_splits_on_headings_and_keeps_line_numbers(tmp_path):
    f = tmp_path / "a.md"
    f.write_text("# Title\nintro text that is long enough to keep here\n"
                 "## Part\nsecond section text that is also long enough\n",
                 encoding="utf-8")
    chunks = chunk_file(str(f))
    assert [c["heading"] for c in chunks] == ["Title", "Part"]
    assert chunks[1]["start"] == 3
    assert chunks[0]["end"] == 2
    assert chunks[1]["end"] == 4

def test_chunk_file_ignores_hash_comments_inside_code_fences(tmp_path):
    f = tmp_path / "b.md"
    f.write_text("# Title\n```bash\n# not a heading\necho hi and more text here\n```\n",
                 encoding="utf-8")
    assert len(chunk_file(str(f))) == 1