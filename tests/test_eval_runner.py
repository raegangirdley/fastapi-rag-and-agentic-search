from evals.eval_runner import score, summarize


def test_score_excludes_infrastructure_errors():
    question = {
        "type": "single_file",
        "expected_sources": ["corpus/tutorial/testing.md"],
    }
    result = {
        "answer": "ERROR: timed out",
        "errored": True,
        "unverified": True,
    }

    scored = score(question, result)

    assert scored["correct"] is None
    assert scored["grounded"] is None
    assert scored["source_recall"] is None


def test_score_reports_zero_retrieval_recall_for_empty_retrieval():
    question = {
        "type": "single_file",
        "expected_sources": ["corpus/tutorial/testing.md"],
    }
    result = {
        "answer": "The answer.",
        "retrieved_files": [],
        "unverified": False,
    }

    scored = score(question, result)

    assert scored["retrieval_recall"] == 0.0


def test_summary_reports_and_excludes_errors(capsys):
    rows = [
        {
            "type": "single_file",
            "errored": False,
            "correct": True,
            "grounded": True,
            "source_recall": 1.0,
            "model_calls": 1,
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "latency_s": 1.0,
            "retries": 0,
            "unverified": False,
        },
        {
            "type": "single_file",
            "errored": True,
            "correct": None,
            "grounded": None,
            "source_recall": None,
            "model_calls": 99,
            "prompt_tokens": 1000,
            "completion_tokens": 1000,
            "latency_s": 200.0,
            "retries": 99,
            "unverified": True,
        },
    ]

    summarize(rows)

    output = capsys.readouterr().out
    assert "| ALL | 1 | 1 | 1 | 1.0 | 1.0 | 1.0 | 1.0 | 15.0 | 1.0 | 0.0 | 0 |" in output
    assert "N counts completed rows; errors are reported separately and excluded from averages." in output
