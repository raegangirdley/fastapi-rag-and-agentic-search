# FastAPI Docs Q&A: Agentic Search vs. RAG

A small project comparing two ways of answering questions over a set of open source FastAPI markdown documentation, using a local LLM (Ollama) at $0 cost:

1. **Agentic search:** an LLM agent that uses tools (`list_files`, `grep`, `read_file`) in a loop to find and read the relevant files itself.
2. **RAG baseline:** chunk the docs, embed them, retrieve the top matches, and answer from those chunks.

The evaluation is designed to compare retrieval approaches on the same hand-written questions, measuring answer quality, citations, model calls, tokens, and latency. Current runs compare agentic search with a no-retrieval baseline; RAG is still in progress.

> **Status:** work in progress. The agentic search loop, audit logging, evaluation runner, and eval validator are implemented. The full agent and no-retrieval evaluations are complete; the RAG baseline remains in progress.

## Why this project

RAG is often cheaper per query. I expected agentic search might do better on exact-term and multi-file questions because it can inspect files and search iteratively. This project tests that hypothesis on a real documentation set instead of assuming it.

## Key findings (so far)

The current comparison uses `llama3.1:8b` (Q4_K_M) through Ollama, 17 hand-written questions over 158 FastAPI Markdown files, and one manual reviewer.

- **Manual answer grades:** Agentic search scored 4 correct, 8 partial, and 4 wrong across 16 completed answers, plus one infrastructure timeout. No retrieval scored 4 / 4 / 9 across 17 answers.
- **Automatic scores:** 6/16 (0.38) for agentic search and 5/17 (0.29) for no retrieval. These are keyword/abstention heuristics, not semantic accuracy.
- **Citations:** Only 1 of 16 agent answers passed the strict citation-support check. The baseline produced no citations.
- **Exact terms remain difficult:** Agentic search scored 0/4 on exact-term questions by both automatic score and manual grade. For Q11 it found the right page but chose `response_model_exclude_defaults` instead of `response_model_exclude_unset`; it failed to retrieve the relevant pages for other exact-term questions.
- **Abstention:** The agent correctly abstained on 2/2 completed “not in docs” questions; the baseline scored 0/3.
- **Verifier limits:** The heuristic did not catch the wrong background-task timing (Q2) or wrong response-model option (Q11). Ten of 16 completed agent answers were marked unverified.

**Headline:** Both systems had four correct answers by manual grade. The agent had fewer wrong answers (4 vs. 9) and abstained more often, but its citations rarely held up; the baseline's four correct answers without documentation access show likely training-data contamination in this evaluation.

The agent timed out on Q17 after 304.73 seconds. It is counted as an infrastructure error, not an incorrect answer. Detailed results and grading criteria are in [results/summary.md](./results/summary.md).

## Architecture

```
            question
               |
        +------+------+
        |             |
   Agentic search       RAG baseline (in progress)
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
| `grep` | Case-insensitive keyword search requiring all non-stopword terms; if that finds nothing, retries with a two-term threshold. Returns `file:line: text`, capped at 50 full matches or 15 fallback matches. |
| `read_file` | Reads a line range from one file, with line numbers (capped at 200 lines / 8,000 characters) |

**Safety constraints**
- Read-only: the tools never write or modify files.
- Restricted to the `corpus/` folder. A `safe_path` helper resolves every path and rejects anything outside it, including `../` traversal and absolute paths.
- Output caps protect the model's context window.

## Corpus

Markdown documentation from the [FastAPI repository](https://github.com/fastapi/fastapi) (MIT license), 158 `.md` files copied into `corpus/`, including 24 reference pages.

## Setup

Requirements: Python 3.12, [Ollama](https://ollama.com)

Evaluation hardware: Intel Core i7-13700H (14 cores, 20 logical processors), 31.7 GiB RAM, NVIDIA GeForce RTX 4070 Laptop GPU (8,188 MiB). The evaluation model was `llama3.1:8b` with Q4_K_M quantization.

```bash
git clone https://github.com/raegangirdley/fastapi-rag-and-agentic-search.git
cd fastapi-rag-and-agentic-search
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

## Usage

Start the API after Ollama is running and the model is available:

```bash
python -m uvicorn main:app --reload
```

Send a JSON `POST` request with a `question` field to `http://127.0.0.1:8000/ask`.

Run and grade the evaluations:

```bash
python validate_evals.py
python eval_runner.py --ids 1 2 3
python eval_runner.py
python eval_runner.py --system no_retrieval
python grade.py results\agent-YYYYMMDD-HHMMSS.jsonl
```

Pass `grade.py` the exact results path printed by the runner. It records an answer grade (correct, partial, wrong) and a separate citation-support judgment. Infrastructure-error rows are skipped.

## Tests

```bash
python -m pytest
```

Tests cover safe file access, path traversal, search behavior and result caps, and evaluator handling of infrastructure errors.

## Evaluation

`evals.json` contains 17 hand-written questions, each with an expected answer, key facts, and expected source files. Fourteen corpus-answer questions have `must_include` terms for automatic keyword scoring; three `not_in_docs` questions use phrase-based abstention scoring. The question types are:

- single-file
- multi-file
- exact-term
- not in the docs (checks whether a system admits it doesn't know)

`correct` is an automatic substring/abstention score, not semantic accuracy. `grounded` additionally requires full expected-source recall and no verifier warnings; it is also heuristic. A citation-support grade is “yes” only when every cited line supports the claim it accompanies. Manual answer grades and citation support are separate judgments.

Each run writes raw per-question JSONL results locally; those files are git-ignored. The tracked [results summary](./results/summary.md) records the current comparison. Agent events are appended to `logs/audit.jsonl`, which is also git-ignored.

### Full evaluation results

The revised 17-question agent run and no-retrieval baseline were run with `llama3.1:8b`. Question 6 now asks what `--workers` configures without including the answer in the question. Automatic scores use the runner's substring and abstention heuristics; manual grades are separate reviewer judgments.

| Metric | Agentic search | No retrieval | RAG baseline |
|---|---|---|---|
| Automatic score (substring/abstention heuristic) | 6/16 (0.38) | 5/17 (0.29) | Pending |
| Grounded score | 1/14 (0.14) | 0/14 (0.00) | Pending |
| Expected-source recall | 0.50 | 0.00 | Pending |
| "Not in docs" phrase score | 2/2 | 0/3 | Pending |
| Infrastructure errors | 1 (question 17) | 0 | Pending |
| Manual answer grades (correct / partial / wrong) | 4 / 8 / 4 | 4 / 4 / 9 | Pending |
| Manual citation support | 1/16 | 0/17* | Pending |
| Avg. model calls per question | 4.94 | 1.00 | Pending |
| Avg. tokens per question | 8,653 | 112 | Pending |
| Avg. latency (s, completed answers) | 10.50 | 1.28 | Pending |

The agent latency mean excludes the 304.73-second Q17 timeout, which is reported separately. The no-retrieval answers contain no citations, so its `0/17` citation-support result means no answer had supporting citations, not that any cited lines were disproven. Q6 was rewritten after the first run exposed that its wording included the answer (`--workers 4`). Questions 1–3 were used repeatedly while debugging the agent, so this is not a clean held-out evaluation. RAG has not been implemented or evaluated. See [results/summary.md](./results/summary.md) for run details.

## What I learned

- A prompt asking a small model to cite sources is a request, not a guarantee. Citation verification and retries did not fix most unsupported answers; the agent averaged 1.76 retries and 8,653 tokens per question.
- Retrieval quality matters: the agent scored 0/4 on exact-term questions, while the no-retrieval baseline's automatic score was 5/17. Embeddings may help with mismatched wording, but the RAG baseline still needs to test that hypothesis.
- Evaluation is harder than keyword matching suggests. A model can answer from memory, so source recall, grounded scoring, and manual answer grades are reported alongside automatic terms. Manual grades here come from one reviewer and should be treated as a development signal, not a benchmark.

## Limitations

- FastAPI is widely known, so a model might answer from its training data rather than the retrieved documents. The eval favors specific details and includes "not in docs" questions to reduce this.
- Questions 1–3 were used repeatedly while debugging the agent, which may make their scores optimistic rather than held out. Q6 was rewritten after its first wording leaked the answer.
- Some generated `corpus/reference/` pages are API stubs with little explanatory prose; `docs_src/` examples referenced by the Markdown includes are not copied into the corpus.
- The verifier is heuristic and cannot reliably detect contradictions or wrong options, as Q2 and Q11 demonstrate.
- One reviewer graded the answers; there is no inter-rater agreement measure.
- The evaluation has only 17 questions, and latency depends on the small model and hardware listed above. Treat the results as indicative, not statistically rigorous.

## Possible next steps

- Implement the embedding-retrieval RAG baseline and compare it on the same questions.
- Run the same evaluation with Qwen3 8B.