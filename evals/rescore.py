import argparse
import json
from pathlib import Path

from evals.eval_runner import score

EVALS_PATH = Path(__file__).with_name("evals.json")


def rescore(results_path: Path) -> Path:
    evals = {
        str(q["id"]): q
        for q in json.loads(EVALS_PATH.read_text(encoding="utf-8"))
    }
    output_path = results_path.with_name(f"{results_path.stem}-rescored.jsonl")

    with results_path.open(encoding="utf-8") as source, output_path.open(
        "w", encoding="utf-8"
    ) as output:
        for line in source:
            row = json.loads(line)
            if not row.get("errored"):
                row.update(score(evals[str(row["id"])], row))
            output.write(json.dumps(row, ensure_ascii=False) + "\n")

    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Recompute automatic scores in an existing evaluation JSONL."
    )
    parser.add_argument("results", type=Path)
    args = parser.parse_args()
    print("wrote", rescore(args.results))


if __name__ == "__main__":
    main()
