# FastAPI Docs Q&A: Agentic Search vs. RAG

## Quickstart (PowerShell)

From the repository root, with the Python 3.12 virtual environment from [Setup](#setup) activated:

```powershell
python -m pip install -r requirements.txt
ollama pull llama3.1:8b; ollama pull nomic-embed-text
python -m uvicorn main:app --reload
```

## Key findings (so far)

The comparison uses `llama3.1:8b` (Q4_K_M) through Ollama, 17 hand-written questions over 158 FastAPI Markdown files, one human reviewer, and a separate anonymized AI regrade.

- **Answerable questions (manual correct / partial / wrong; 14 each):** agentic search scored 2 / 8 / 4, no retrieval 4 / 4 / 6, and RAG 11 / 3 / 0.
- **Not in docs:** RAG abstained correctly on 3/3 questions; agentic search did so on 2/2 completed questions (Q17 timed out); no retrieval did so on 0/3.
- **Citation support:** on answerable questions, agentic search scored 1/14, no retrieval 0/14, and RAG 12/14. For not-in-docs answers, support was 0/2, 0/3, and 0/3, respectively.
- **All completed answers (manual correct / partial / wrong):** agentic search scored 4 / 8 / 4, no retrieval 4 / 4 / 9, and RAG 14 / 3 / 0. These totals include abstentions and have different denominators because the agent timed out once.
- **Automatic scores:** 6/16 (0.38) for agentic search, 5/17 (0.29) for no retrieval, and 14/17 (0.82) for RAG. These are keyword/abstention heuristics, not semantic accuracy; RAG's total includes its three correct abstentions.
- **RAG retrieval:** Full expected-source recall at top 5 was 14/14: every expected file was retrieved for every answerable question. The separate 14/14 top-one hit rate counts a question if any one expected file is ranked first, so it is a more lenient measure, especially for multi-file questions.
- **Memory and contamination:** No retrieval answered 4/14 answerable questions correctly without access to the corpus, suggesting the evaluation can be affected by training-data knowledge.
- **Exact terms:** RAG answered all four exact-term questions correctly by both automatic and manual grading; agentic search scored 0/4 by both.
- **Blind regrade:** A second AI reviewer, given 50 randomly ordered answers without system labels, matched all 17 RAG answer grades (14 / 3 / 0). One RAG citation judgment differed and was checked against the source; Q7 remains unsupported.
- **RAG answer gaps:** Three multi-file answers were partial: Q7 used `/token` instead of the documented relative `token` URL, Q8 omitted `@pytest.mark.anyio`, `async def`, and the TestClient limitation for async tests, and Q9 omitted that waiting does not occupy a worker thread.
- **Verifier limits:** Eight RAG answers were marked unverified. The heuristic also misses citation sentence-boundary cases and cannot establish that an undocumented feature does not exist.

**Headline:** On 14 answerable questions, RAG was fully correct on 11 (3 partial, 0 wrong), versus 2 fully correct for agentic search and 4 for no retrieval. RAG also abstained correctly on all three not-in-docs questions. This is a development evaluation, not a held-out benchmark: questions 1–3 were used during agent debugging and as the RAG smoke test, and the questions share vocabulary with the source docs. Detailed results and grading criteria are in [results/summary.md](./results/summary.md).

This project keeps both answer systems available. **Agentic search** uses an LLM with `list_files`, `grep`, and `read_file` tools; **RAG** chunks and embeds the docs, retrieves relevant passages, and answers from them. The evaluation runner supports `agent`, `rag`, and a `no_retrieval` control. The HTTP `/ask` endpoint currently uses agentic search; RAG remains available through the evaluation runner.

> **Status:** work in progress. The current focus is evaluating and improving RAG while retaining agentic search as a supported approach.

## Why this project

RAG is often cheaper per query. I expected agentic search might do better on exact-term and multi-file questions because it can inspect files and search iteratively. This project tests that hypothesis on a real documentation set instead of assuming it.

## Architecture

```
            question
               |
        +------+------+
        |             |
   Agentic search              RAG
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

The no-retrieval system is an evaluation control, not a replacement for either retrieval approach.

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

Markdown documentation from the [FastAPI repository](https://github.com/fastapi/fastapi) (MIT license), 158 `.md` files copied into `corpus/`, including 24 reference pages. The [NOTICE](./NOTICE) records the upstream attribution and license; the root [LICENSE](./LICENSE) applies to this project's original code, not the copied FastAPI documentation.

## Setup

Requirements: Python 3.12, [Ollama](https://ollama.com)

Evaluation hardware: Intel Core i7-13700H (14 cores, 20 logical processors), 31.7 GiB RAM, NVIDIA GeForce RTX 4070 Laptop GPU (8,188 MiB). The evaluation model was `llama3.1:8b` with Q4_K_M quantization.
The tested environment used Ollama 0.40.16, `llama3.1:8b` (model ID prefix `46e0c10c039e`, Q4_K_M), and `nomic-embed-text:latest` (ID prefix `0a109f422b47`, F16). Python package versions are pinned in `requirements.txt`.

```powershell
git clone https://github.com/raegangirdley/fastapi-rag-and-agentic-search.git
cd fastapi-rag-and-agentic-search
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

## Usage

Start the API after Ollama is running and the model is available:

```bash
python -m uvicorn main:app --reload
```

Send a JSON `POST` request with a `question` field to `http://127.0.0.1:8000/ask`.
The HTTP endpoint currently uses agentic search; RAG is available through the evaluation runner.

Build the RAG index once, check retrieval, then run and grade RAG:

```bash
python -c "from rag import load_index; chunks, vectors = load_index(); print('Chunk count:', len(chunks))"
python retrieval_check.py
python eval_runner.py --system rag --ids 1 2 3
python eval_runner.py --system rag
python grade.py results\rag-YYYYMMDD-HHMMSS.jsonl
```

Run and grade the agentic and no-retrieval evaluations:

```bash
python validate_evals.py
python eval_runner.py --ids 1 2 3
python eval_runner.py
python eval_runner.py --system no_retrieval
python grade.py results\agent-YYYYMMDD-HHMMSS.jsonl
```

Pass `grade.py` the exact results path printed by the runner. It records an answer grade (correct, partial, wrong) and a separate citation-support judgment. Infrastructure-error rows are skipped.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Run tests with the project interpreter so a globally installed `pytest.exe` is not used by mistake. Tests cover safe file access, path traversal, search behavior and result caps, chunking and line numbers, and evaluator handling of infrastructure errors.

## Evaluation

`evals.json` contains 17 hand-written questions, each with an expected answer, key facts, and expected source files. Fourteen corpus-answer questions have `must_include` terms for automatic keyword scoring; three `not_in_docs` questions use phrase-based abstention scoring. The question types are:

- single-file
- multi-file
- exact-term
- not in the docs (checks whether a system admits it doesn't know)

`correct` is an automatic substring/abstention score, not semantic accuracy. `grounded` additionally requires full expected-source recall and no verifier warnings; it is also heuristic. A citation-support grade is "yes" only when every cited line supports the claim it accompanies. Manual answer grades and citation support are separate judgments.

Each run writes raw per-question JSONL results locally; those files are git-ignored. The tracked [results summary](./results/summary.md) records the current comparison. Agent events are appended to `logs/audit.jsonl`, which is also git-ignored.

### Full evaluation results

The 17-question evaluations use `llama3.1:8b`. Question 6 asks what `--workers` configures without including the answer in the question. Automatic scores use the runner's substring and abstention heuristics; manual grades are separate reviewer judgments.

| Metric | Agentic search | No retrieval control | RAG |
|---|---|---|---|
| Automatic score (substring/abstention heuristic) | 6/16 (0.38) | 5/17 (0.29) | 14/17 (0.82) |
| Grounded score | 1/14 (0.14) | 0/14 (0.00) | 6/14 (0.43) |
| Answerable manual grades (correct / partial / wrong; 14 questions) | 2 / 8 / 4 | 4 / 4 / 6 | 11 / 3 / 0 |
| Correct not-in-docs abstentions | 2/2 completed (Q17 timeout) | 0/3 | 3/3 |
| Exact-term automatic score | 0/4 | 2/4 | 4/4 |
| Exact-term manual grades (correct / partial / wrong) | 0 / 0 / 4 | 2 / 1 / 1 | 4 / 0 / 0 |
| Cited expected-source recall | 0.50 | 0.00 | 1.00 |
| Full expected-source recall at top 5 | — | — | 14/14 |
| Top-1 hit rate (at least one expected file) | — | — | 14/14 |
| "Not in docs" phrase score | 2/2 | 0/3 | 3/3 |
| Infrastructure errors | 1 timeout (Q17, 304.73 s) | 0 | 0 |
| All-completed manual grades (correct / partial / wrong) | 4 / 8 / 4 | 4 / 4 / 9 | 14 / 3 / 0 |
| Citation support on answerable questions | 1/14 | 0/14 | 12/14 |
| Citation support on not-in-docs questions | 0/2 | 0/3 | 0/3 |
| Citation support overall | 1/16 | 0/17 | 12/17 |
| Answers marked unverified by heuristic | 10/16 | 0/17 | 8/17 |
| Avg. model calls per question | 4.94 | 1.00 | 2.65 |
| Avg. tokens per question | 8,653 | 112 | 3,806 |
| Avg. latency (s, completed answers) | 10.50 | 1.28 | 5.86 |

RAG indexed 2,449 chunks from 158 Markdown files using `nomic-embed-text`. Its retrieved expected-source recall was 1.00 over the 14 corpus-answer questions. The separate top-1 hit rate counts a question as a hit when any expected file is retrieved; it does not mean every expected file was in rank one. RAG latency was measured with the index already built and excludes the one-time index build. RAG had no infrastructure errors. The agent's Q17 timeout is reported separately and excluded from its completed-answer averages. The no-retrieval answers contain no citations, so its `0/17` citation-support result means no answer had supporting citations, not that any cited lines were disproven.

Q3 was manually correct although the automatic exact-phrase check marked it incorrect. Q7–Q9 were partial despite retrieving the expected files, showing that successful retrieval does not guarantee a complete or exact answer. RAG's Q15–Q17 abstentions were manually correct, but their citations did not support the absence claims. Q6 was rewritten after the first run exposed that its wording included the answer (`--workers 4`). Questions 1–3 were used while debugging the agent and as the RAG smoke test, so this is not a clean held-out evaluation. See [results/summary.md](./results/summary.md) for run details.

## What I learned

- A prompt asking a small model to cite sources is a request, not a guarantee. Citation verification and retries did not fix most unsupported answers; the agent averaged 1.76 retries and 8,653 tokens per question.
- Requiring a citation for every claim can induce unsupported citations when the correct answer is "the docs do not say." RAG abstained correctly on Q15–Q17, but none of those citations supported the absence claims; report citation support on answerable and not-in-docs questions separately.
- Retrieval quality is only part of the result: RAG retrieved all expected files within its top five for these corpus questions, but still gave incomplete answers on Q7–Q9.
- Evaluation is harder than keyword matching suggests. A model can answer from memory, so source recall, grounded scoring, and manual answer grades are reported alongside automatic terms. Grades come from one human reviewer; a blinded AI regrade is a consistency check, not a benchmark.

## Limitations

- FastAPI is widely known, so a model might answer from its training data rather than the retrieved documents. The eval favors specific details and includes "not in docs" questions to reduce this.
- The questions were written from the source docs and share some of their vocabulary and phrasing, which may make retrieval unusually easy. Retrieval performance may be lower on independently written paraphrases.
- Questions 1–3 were used while debugging the agent and as the RAG smoke test, which may make their scores optimistic rather than held out. Q6 was rewritten after its first wording leaked the answer.
- Some generated `corpus/reference/` pages are API stubs with little explanatory prose; `docs_src/` examples referenced by the Markdown includes are not copied into the corpus.
- The verifier is heuristic and cannot reliably detect contradictions or wrong options, as Q2 and Q11 demonstrate.
- The primary grades come from one human reviewer. A separate AI regrade used anonymized, mixed answers, but answer style and citations can hint at the system; this is not independent-human inter-rater agreement.
- The evaluation has only 17 questions, and latency depends on the small model and hardware listed above. Treat the results as indicative, not statistically rigorous.

## Possible next steps

- Expose agentic search and RAG as selectable modes through the HTTP API while keeping both available.
- Improve answer completeness and citation support, then evaluate on 6–8 questions written in my own words without consulting the docs; freeze that set before running either system and report it separately as held out.
- Run the same evaluation with Qwen3 8B.