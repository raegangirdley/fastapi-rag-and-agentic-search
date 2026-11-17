import json

from evals.rescore import rescore


def test_rescore_updates_completed_rows_and_preserves_errors(tmp_path):
    results_path = tmp_path / "run.jsonl"
    rows = [
        {
            "id": "1",
            "answer": "UploadFile uses a spooled file; filename and content_type are attributes.",
            "errored": False,
            "unverified": False,
            "retrieved_files": ["corpus/tutorial/request-files.md"],
        },
        {
            "id": "17",
            "answer": "ERROR: timed out",
            "errored": True,
            "correct": None,
            "source_recall": None,
        },
    ]
    results_path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )

    output_path = rescore(results_path)
    rescored = [
        json.loads(line)
        for line in output_path.read_text(encoding="utf-8").splitlines()
    ]

    assert output_path.name == "run-rescored.jsonl"
    assert rescored[0]["correct"] is True
    assert rescored[1] == rows[1]
