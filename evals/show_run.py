import json, sys
run = sys.argv[1]
for line in open("logs/audit.jsonl", encoding="utf-8"):
    e = json.loads(line)
    if e["run_id"].startswith(run) and e["event"] in ("tool_call", "verification"):
        print(e)