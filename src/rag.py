import hashlib
import json
import re
import time
import uuid
from pathlib import Path

import numpy as np
import ollama

from src.agent import MAX_RETRIES, call_model, check_answer, repair_citations
from src.audit import log_event
from src.tools.list_files import list_files

EMBEDDING_MODEL = "nomic-embed-text"
INDEX_DIR = Path("index")
TOP_K = 5
MAX_CHUNK_LINES = 25
MAX_CHUNK_CHARS = 1500
MIN_CHUNK_CHARS = 40

FENCE = re.compile(r"^\s*(```|~~~)")
HEADING = re.compile(r"^(#{1,6})\s+(.*)")

RAG_PROMPT = (
    "Answer the question using ONLY the excerpts provided. Each excerpt shows a "
    "file name and numbered lines. Write 3 to 6 sentences in plain text. Cite "
    "every claim as [corpus/<file>.md:<line>] using the exact line number where "
    "the claim appears. Do not copy excerpt text or line-numbered text into your "
    "answer. Never write code that is not in the excerpts. If the excerpts do not "
    "answer the question, say that the corpus does not contain it."
)

### CHUNKING ###

def chunk_file(path: str) -> list[dict]:
    lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    chunks, buf, heading, in_fence = [], [], "", False

    def flush():
        nonlocal buf
        while buf and not buf[0][1].strip():
            buf.pop(0)
        while buf and not buf[-1][1].strip():
            buf.pop()
        body = "\n".join(t for _, t in buf)
        if len(body.strip()) >= MIN_CHUNK_CHARS:
            chunks.append({
                "path": path,
                "heading": heading,
                "start": buf[0][0],
                "end": buf[-1][0],
                "text": "\n".join(f"{n}: {t}" for n, t in buf),
                "embed_text": f"{path} | {heading}\n{body}",
            })
        buf = []

    for number, text in enumerate(lines, start=1):
        if FENCE.match(text):
            in_fence = not in_fence
        m = None if in_fence else HEADING.match(text)
        if m:
            flush()
            heading = m.group(2)
        buf.append((number, text))
        if len(buf) >= MAX_CHUNK_LINES or sum(len(t) for _, t in buf) >= MAX_CHUNK_CHARS:
            flush()
    flush()
    return chunks

### EMBEDDINGS ###

def embed(texts: list[str], prefix: str) -> np.ndarray:
    out = []
    for i in range(0, len(texts), 32):
        batch = [prefix + t for t in texts[i:i + 32]]
        out.extend(ollama.embed(model=EMBEDDING_MODEL, input=batch)["embeddings"])
    arr = np.array(out, dtype="float32")
    arr /= np.linalg.norm(arr, axis=1, keepdims=True) + 1e-9
    return arr

def corpus_hash(files: list[str]) -> str:
    h = hashlib.sha256()
    for f in files:
        h.update(f.encode())
        h.update(Path(f).read_bytes())
    return h.hexdigest()

_INDEX = None

def load_index(rebuild: bool = False):
    global _INDEX
    if _INDEX is not None and not rebuild:
        return _INDEX

    files = list_files("corpus")
    digest = corpus_hash(files)
    meta_path, vec_path = INDEX_DIR / "chunks.json", INDEX_DIR / "vectors.npy"

    if not rebuild and meta_path.exists() and vec_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if meta["hash"] == digest and meta["model"] == EMBEDDING_MODEL:
            _INDEX = (meta["chunks"], np.load(vec_path))
            return _INDEX

    print("Building index (one-time; this can take a few minutes)...")
    chunks = [c for f in files for c in chunk_file(f)]
    vectors = embed([c["embed_text"] for c in chunks], "search_document: ")
    INDEX_DIR.mkdir(exist_ok=True)
    np.save(vec_path, vectors)
    meta_path.write_text(
        json.dumps({"hash": digest, "model": EMBEDDING_MODEL, "chunks": chunks}),
        encoding="utf-8")
    print(f"Indexed {len(chunks)} chunks from {len(files)} files.")
    _INDEX = (chunks, vectors)
    return _INDEX

def retrieve(question: str, k: int = TOP_K) -> list[dict]:
    chunks, vectors = load_index()
    q = embed([question], "search_query: ")[0]
    scores = vectors @ q
    top = np.argsort(-scores)[:k]
    return [{**chunks[i], "score": float(scores[i])} for i in top]

### RAG SYSTEM ###

def run_rag(question: str, question_id: str = "adhoc") -> dict:
    run_id = f"{question_id}-{uuid.uuid4().hex[:6]}"
    start = time.perf_counter()
    m = {"model_calls": 0, "tool_calls": 0, "duplicates": 0, "retries": 0,
         "prompt_tokens": 0, "completion_tokens": 0}

    t = time.perf_counter()
    hits = retrieve(question)
    retrieval_s = round(time.perf_counter() - t, 2)
    labels = [f"{h['path']}:{h['start']}-{h['end']}" for h in hits]
    log_event({"run_id": run_id, "event": "retrieval", "chunks": labels,
               "scores": [round(h["score"], 3) for h in hits],
               "latency_s": retrieval_s})

    tool_texts = [f"File: {h['path']}\n{h['text']}" for h in hits]
    messages = [
        {"role": "system", "content": RAG_PROMPT},
        {"role": "user", "content":
            "Excerpts:\n\n" + "\n\n".join(tool_texts) + f"\n\nQuestion: {question}"},
    ]

    answer, problems = "", []
    for attempt in range(MAX_RETRIES + 1):
        t = time.perf_counter()
        response = call_model(messages, use_tools=False)
        pt = getattr(response, "prompt_eval_count", None) or 0
        ct = getattr(response, "eval_count", None) or 0
        m["model_calls"] += 1
        m["prompt_tokens"] += pt
        m["completion_tokens"] += ct
        log_event({"run_id": run_id, "event": "model_call",
                   "latency_s": round(time.perf_counter() - t, 2),
                   "prompt_tokens": pt, "completion_tokens": ct})

        message = response["message"]
        answer = repair_citations(message.content or "", tool_texts)
        problems = check_answer(answer, tool_texts, set(), require_read=False)
        log_event({"run_id": run_id, "event": "verification", "problems": problems})
        if not problems:
            break
        if attempt < MAX_RETRIES:
            m["retries"] += 1
            messages.append(message)
            messages.append({"role": "user", "content": (
                "Your answer failed verification: " + "; ".join(problems) + ". "
                "Rewrite it using ONLY the excerpts above, in 3 to 6 sentences. "
                "Do not copy excerpt text. Cite each claim as "
                "[corpus/<file>.md:<line>] using the exact line number where the "
                "claim appears.")})

    result = {
        "run_id": run_id,
        "answer": answer,
        "unverified": bool(problems),
        "problems": problems,
        "stopped": False,
        "latency_s": round(time.perf_counter() - start, 2),
        "retrieval_s": retrieval_s,
        "retrieved": labels,
        "retrieved_files": sorted({h["path"] for h in hits}),
        **m,
    }
    log_event({"run_id": run_id, "event": "final",
               **{k: v for k, v in result.items() if k != "answer"}})
    return result