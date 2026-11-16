# FastAPI Docs Q&A: Agentic Search vs. RAG

A small project comparing two ways of answering questions over a set of open source FastAPI markdown documentation, using a local LLM (Ollama) at $0 cost:

1. **Agentic search:** an LLM agent that uses tools (`list_files`, `grep`, `read_file`) in a loop to find and read the relevant files itself.
2. **RAG baseline:** chunk the docs, embed them, retrieve the top matches, and answer from those chunks.

Both systems are scored on the same hand-written evaluation set, measuring accuracy, citations, number of model calls, tokens, and latency.

> **Status:** work in progress. The tool layer and its tests are done. The agent loop, RAG baseline, and evaluation are in progress.

## Why this project

Retrieval is a common design decision for LLM applications. RAG is cheap and fast per query. Agentic search can be more accurate on exact terms and cross-file questions, but costs more calls and time. This project measures that tradeoff on a real documentation set instead of guessing.

## Architecture

```
            question
               |
        +------+------+
        |             |
   Agentic search    RAG baseline
        |             |
   LLM <-> tools     embed -> retrieve top chunks
 (list_files, grep,        |
    read_file)         LLM answers
        |             |
        +------+------+
               |
     cited answer + audit log
               |
        evaluation script
```

## Tools

| Tool | What it does |
|---|---|
| `list_files` | Lists the markdown files under the corpus folder |
| `grep` | Case-insensitive search across files, returning `file:line: text` (capped at 50 matches) |
| `read_file` | Reads a line range from one file, with line numbers (capped at 200 lines / 8,000 characters) |

**Safety constraints**
- Read-only: the tools never write or modify files.
- Restricted to the `corpus/` folder. A `safe_path` helper resolves every path and rejects anything outside it, including `../` traversal and absolute paths.
- Output caps protect the model's context window.

## Corpus

Markdown documentation from the [FastAPI repository](https://github.com/fastapi/fastapi) (MIT license), 158 .md files copied into `corpus/`.

## Setup

Requirements: Python 3.12, [Ollama](https://ollama.com)

```bash
git clone [TODO: repo url]
cd fastapi-rag-and-agentic-search
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt

ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

## Usage

`[TODO]`

## Tests

```bash
python -m pytest
```

Covers the tools, including path-traversal and size-cap behavior. `[TODO]`

## Evaluation

`evals.json` contains 17 hand-written questions, each with an expected answer, key facts to check, and the source files that contain the answer. Question types:

- single-file
- multi-file
- exact-term
- not in the docs (checks whether a system admits it doesn't know)

**Environment:** `[TODO: model name and size, quantization, CPU/GPU, RAM]`

**Results**

| Metric | Agentic search | RAG baseline |
|---|---|---|
| Correct answers | [TODO] | [TODO] |
| Correct source cited | [TODO] | [TODO] |
| "Not in docs" handled correctly | [TODO] | [TODO] |
| Avg. model calls per question | [TODO] | [TODO] |
| Avg. tokens per question | [TODO] | [TODO] |
| Avg. latency (s) | [TODO] | [TODO] |

## What I learned

`[TODO: where each approach won and lost, surprises]`

## Limitations

- FastAPI is widely known, so a model might answer from its training data rather than the retrieved documents. The eval favors specific details and includes "not in docs" questions to reduce this.
- A small local model limits quality, especially for tool calling. Results depend on the model and hardware listed above.
- Small evaluation set, so treat results as indicative, not statistically rigorous.

## Possible next steps

- Swap in a hosted model through the `call_model` wrapper to compare against the local one
- Expose the tools as an MCP server
- Add a rate or step budget per user