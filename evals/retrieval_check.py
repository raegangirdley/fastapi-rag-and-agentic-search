import json
from pathlib import Path
from src.rag import retrieve

evals = json.loads(
    Path(__file__).with_name("evals.json").read_text(encoding="utf-8")
)
ks = (1, 3, 5, 10)
hits = {k: 0 for k in ks}
n = 0

for q in evals:
    expected = set(q["expected_sources"])
    if not expected:
        continue
    n += 1
    ranked = [h["path"] for h in retrieve(q["question"], k=max(ks))]
    for k in ks:
        if expected & set(ranked[:k]):
            hits[k] += 1
    status = "ok " if expected & set(ranked[:5]) else "MISS"
    print(f"[{q['id']}] {status} expected={sorted(expected)} top3={ranked[:3]}")

print(f"\nHit rate over {n} questions:")
for k in ks:
    print(f"  top-{k}: {hits[k]}/{n}")