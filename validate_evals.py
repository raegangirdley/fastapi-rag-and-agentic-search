import json
from pathlib import Path

REQUIRED = {"id", "type", "question", "expected_answer", "key_facts",
            "expected_sources"}
TYPES = {"single_file", "multi_file", "exact_term", "not_in_docs"}

evals = json.loads(Path("evals.json").read_text(encoding="utf-8"))
seen_ids = set()
errors = 0

for q in evals:
    qid = q.get("id", "?")
    missing = REQUIRED - q.keys()
    if missing:
        print(f"[{qid}] missing fields: {missing}"); errors += 1
    if qid in seen_ids:
        print(f"[{qid}] duplicate id"); errors += 1
    seen_ids.add(qid)
    if q.get("type") not in TYPES:
        print(f"[{qid}] bad type: {q.get('type')}"); errors += 1

    text = ""
    for src in q.get("expected_sources", []):
        p = Path(src)
        if not p.exists():
            print(f"[{qid}] source not found: {src}"); errors += 1
        else:
            text += p.read_text(encoding="utf-8", errors="replace").lower()

    for term in q.get("must_include", []):
        alternatives = [
            option.strip().lower()
            for option in term.split("|")
            if option.strip()
        ]
        if text and not any(option in text for option in alternatives):
            print(f"[{qid}] '{term}' not found in expected sources "
                  f"(it may only appear in the answer wording)")

    for term in q.get("probe_terms", []):
        hits = [str(f) for f in Path("corpus").rglob("*.md")
                if term.lower() in f.read_text(encoding="utf-8", errors="replace").lower()]
        print(f"[{qid}] probe '{term}': {len(hits)} file(s) {hits[:3]}")

print("OK" if not errors else f"{errors} problem(s)")