import argparse
import json
import time
from collections import defaultdict
from pathlib import Path

from agent import CITATION, LANGUAGE_MODEL, call_model, run_agent

ABSTAIN = ("does not", "doesn't", "not specified", "no mention", "not documented",
           "not provide", "not contain", "cannot find", "can't find", "no built-in",
           "not supported by the corpus", "not covered")

def run_no_retrieval(question: str, question_id: str = "adhoc") -> dict:
   # model answers w/o corpus or tools as base
    messages = [
        {"role": "system", "content": "Answer briefly from your own knowledge."},
        {"role": "user", "content": question},
    ]
    t = time.perf_counter()
    response = call_model(messages, use_tools=False)
    return {
        "answer": response["message"].content or "",
        "unverified": False, "problems": [], "stopped": False,
        "latency_s": round(time.perf_counter() - t, 2),
        "model_calls": 1, "tool_calls": 0, "duplicates": 0, "retries": 0,
        "prompt_tokens": getattr(response, "prompt_eval_count", 0) or 0,
        "completion_tokens": getattr(response, "eval_count", 0) or 0,
    }

SYSTEMS = {"agent": run_agent, "no_retrieval": run_no_retrieval}
# TODO: SYSTEMS["rag"] = run_rag

def includes_all(answer: str, terms: list[str]) -> bool:
    # each term must appear
    low = answer.lower()
    return all(any(alt.strip().lower() in low for alt in term.split("|"))
               for term in terms)

def score(q: dict, result: dict) -> dict:
    if result.get("errored"):
        return {
            "correct": None,
            "source_recall": None,
            "needs_review": True,
            "grounded": None,
        }

    answer = result["answer"]
    cited = {m.group(1) for m in CITATION.finditer(answer)}
    expected = set(q["expected_sources"])

    if q["type"] == "not_in_docs":
        abstained = any(p in answer.lower() for p in ABSTAIN)
        return {
            "correct": abstained, 
            "source_recall": None, 
            "needs_review": True,
            "grounded": None,
            }

    terms = q.get("must_include")
    correct = includes_all(answer, terms) if terms else None
    recall = len(expected & cited) / len(expected) if expected else None
    return {
        "correct": correct, 
        "source_recall": recall, 
        "needs_review": False,
        "grounded": bool(correct) and recall == 1.0 and not result["unverified"]
        }

def mean(values):
    values = [v for v in values if v is not None]
    return round(sum(values) / len(values), 2) if values else None

def summarize(rows: list[dict]) -> None:
    groups = defaultdict(list)
    for r in rows:
        groups["ALL"].append(r)
        groups[r["type"]].append(r)

    print("\n| Group | N | Scored | Errors | Correct | Grounded | Source recall | Model calls | Tokens | "
          "Latency (s) | Retries | Unverified |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for name, rs in groups.items():
        scored = [r for r in rs if r["correct"] is not None]
        errors = sum(1 for r in rs if r.get("errored"))
        correct = [1.0 if r["correct"] else 0.0 
                   for r in scored]
        grounded = [
            1.0 if r["grounded"] else 0.0
            for r in scored
            if r["grounded"] is not None
        ]
        print(f"| {name} | {len(rs)} | {len(scored)} | {errors} "
              f"| {mean(correct)} | {mean(grounded)} "
              f"| {mean([r['source_recall'] for r in scored])} "
              f"| {mean([r['model_calls'] for r in rs])} "
              f"| {mean([r['prompt_tokens'] + r['completion_tokens'] for r in rs])} "
              f"| {mean([r['latency_s'] for r in rs])} "
              f"| {mean([r['retries'] for r in rs])} "
              f"| {sum(1 for r in rs if not r.get('errored') and r['unverified'])} |")
    print("\nnot_in_docs rows are auto-scored by phrase matching. Review them by hand.")
    print("Errors are excluded from scored accuracy metrics.")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--system", choices=SYSTEMS, default="agent")
    parser.add_argument("--ids", nargs="*", help="only run these question ids")
    args = parser.parse_args()

    evals = json.loads(Path("evals.json").read_text(encoding="utf-8"))
    if args.ids:
        evals = [q for q in evals if str(q["id"]) in set(args.ids)]

    Path("results").mkdir(exist_ok=True)
    out_path = Path("results") / f"{args.system}-{time.strftime('%Y%m%d-%H%M%S')}.jsonl"
    rows = []

    for q in evals:
        print(f"[{q['id']}] {q['question'][:70]}...")
        started = time.perf_counter()
        errored = False
        try:
            result = SYSTEMS[args.system](q["question"], str(q["id"]))
        except Exception as exc:                   # one bad question shouldn't kill the run
            result = {"answer": f"ERROR: {exc}", "unverified": True, "problems": [str(exc)],
                      "stopped": False,
                      "latency_s": round(time.perf_counter() - started, 2),
                      "model_calls": 0, "tool_calls": 0,
                      "duplicates": 0, "retries": 0, "prompt_tokens": 0,
                      "completion_tokens": 0}
            errored = True
        result["errored"] = errored
        row = {"id": q["id"], "type": q["type"], "model": LANGUAGE_MODEL,
               "system": args.system, **result, **score(q, result)}
        rows.append(row)
        with out_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"    errored={row['errored']} correct={row['correct']} "
              f"source_recall={row['source_recall']} "
              f"calls={row['model_calls']} {row['latency_s']}s")

    print(f"\nSaved to {out_path}")
    summarize(rows)


if __name__ == "__main__":
    main()