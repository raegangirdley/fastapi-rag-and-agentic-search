import json
import time
from pathlib import Path

LOG_PATH = Path("logs") / "audit.jsonl"

def log_event(event:dict) -> None:
    LOG_PATH.parent.mkdir(exist_ok=True)
    event = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), **event}
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")