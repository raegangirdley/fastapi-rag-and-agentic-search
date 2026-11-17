# Evaluation summary

This is a small development experiment, not a statistically rigorous benchmark.

## Setup

- Model: Ollama `llama3.1:8b`, Q4_K_M quantization
- Hardware: Intel Core i7-13700H (14 cores, 20 logical processors), 31.7 GiB RAM, NVIDIA GeForce RTX 4070 Laptop GPU (8,188 MiB) and Intel Iris Xe Graphics
- Corpus: 158 Markdown files from FastAPI docs, including 24 files under `corpus/reference/`
- Evaluation: 17 hand-written questions; 14 corpus-answer questions and 3 “not in docs” questions
- Manual grading: one reviewer; answer grade and citation support recorded separately

## Results

| Metric | Agentic search | No retrieval |
|---|---:|---:|
| Automatic keyword/abstention score | 6/16 (0.38) | 5/17 (0.29) |
| Infrastructure errors | 1 timeout (Q17, 304.73 s) | 0 |
| Grounded score | 1/14 (0.14) | 0/14 (0.00) |
| Expected-source recall | 0.50 | 0.00 |
| “Not in docs” phrase score | 2/2 | 0/3 |
| Exact-term automatic score | 0/4 | 2/4 |
| Exact-term manual grades (correct / partial / wrong) | 0 / 0 / 4 | 2 / 1 / 1 |
| Manual grades (correct / partial / wrong) | 4 / 8 / 4 | 4 / 4 / 9 |
| Citation support | 1/16 | 0/17 |
| Answers marked unverified by the heuristic | 10/16 | 0/17 |
| Average model calls per question | 4.94 | 1.00 |
| Average tokens per question | 8,653 | 112 |
| Average latency per completed answer | 10.50 s | 1.28 s |

The agent's Q17 run timed out after 304.73 seconds. It is recorded as an infrastructure error and excluded from accuracy, manual answer grades, and the 10.50-second mean over 16 completed answers. The no-retrieval model supplied no citations, so its 0/17 means no answer had supporting citations.

Citation support is a strict binary judgment: “yes” means every cited line supports the claim it accompanies. The automatic score uses required substrings and phrase-based abstention, not semantic answer correctness. The grounded score is also heuristic.

Questions 1–3 were used repeatedly while debugging the agent, so their results may be optimistic. Q6 was rewritten after the first wording included its own answer (`--workers 4`). The baseline's four manually correct answers without document access suggest training-data contamination of this benchmark.

Raw per-question JSONL results and grade files are locally ignored; this report preserves the comparison without publishing generated answer logs.
