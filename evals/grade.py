import json
import sys
from collections import Counter
from pathlib import Path

from src.agent import CITATION

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

results_path = Path(sys.argv[1])
evals = {str(q["id"]): q
         for q in json.loads(
             Path(__file__).with_name("evals.json").read_text(encoding="utf-8")
         )}
grades_path = results_path.with_suffix(".grades.jsonl")

done = set()
if grades_path.exists():
    done = {json.loads(l)["id"] for l in grades_path.open(encoding="utf-8")}

for line in results_path.open(encoding="utf-8"):
    row = json.loads(line)
    if row.get("errored"):
        print(f"\n[{row['id']}] Skipping manual grading for infrastructure error.")
        continue
    if row["id"] in done:
        continue
    q = evals[str(row["id"])]
    print("\n" + "=" * 70)
    print(f"[{row['id']}] {q['type']}: {q['question']}")
    print(f"\nEXPECTED: {q['expected_answer']}")
    print(f"\nANSWER:   {row['answer']}\n")
    for m in CITATION.finditer(row["answer"]):
        path, n = m.group(1), int(m.group(2))
        try:
            text = Path(path).read_text(encoding="utf-8",
                                        errors="replace").splitlines()[n - 1]
        except Exception:
            text = "(missing file or line)"
        print(f"  cited {path}:{n} -> {text[:150]}")
    grade = ""
    while grade not in ("c", "p", "w"):
        grade = input("\nGrade: (c)orrect, (p)artial, (w)rong: ").strip().lower()
        cites_ok = ""
    while cites_ok not in ("y", "n"):
        cites_ok = input("Do the cited lines support the claims? (y/n): ").strip().lower()
    note = input("Note (optional): ").strip()
    with grades_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"id": row["id"], "type": q["type"],
                            "grade": grade,
                            "citations_ok": cites_ok == "y",
                            "note": note}) + "\n")
if not grades_path.exists():
    print("No gradable rows (all were infra errors or skipped)")
    sys.exit(0)
    
grades = [json.loads(l) for l in grades_path.open(encoding="utf-8")]
print("\nGrades:", dict(Counter(g["grade"] for g in grades)))
print(f"Citations supported: "
      f"{sum(g.get('citations_ok', False) for g in grades)}/{len(grades)}")