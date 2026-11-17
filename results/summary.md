# Evaluation summary

This is a small development experiment, not a statistically rigorous benchmark.

## Setup

- Language model: Ollama `llama3.1:8b`, Q4_K_M quantization
- Embedding model: Ollama `nomic-embed-text`
- Runtime/model versions: Ollama 0.40.16; `llama3.1:8b` (model ID prefix `46e0c10c039e`, Q4_K_M); `nomic-embed-text:latest` (ID prefix `0a109f422b47`, F16)
- Python: 3.12.0; package versions are pinned in [`requirements.txt`](../requirements.txt)
- Hardware: Intel Core i7-13700H (14 cores, 20 logical processors), 31.7 GiB RAM, NVIDIA GeForce RTX 4070 Laptop GPU (8,188 MiB) and Intel Iris Xe Graphics
- Corpus: 158 Markdown files from FastAPI docs, including 24 files under `corpus/reference/`
- RAG index: 2,449 chunks, 768-dimensional vectors
- Evaluation: 17 hand-written questions; 14 corpus-answer questions and 3 "not in docs" questions
- Manual grading: one human reviewer; answer grade and citation support recorded separately

The reported full RAG metrics use the 17-question run `rag-20261116-220025.jsonl`. The later `rag-20261116-221618.jsonl` file is a three-question smoke run, not a replacement full evaluation.

## Results

| Metric | Agentic search | No retrieval control | RAG |
|---|---:|---:|---:|
| Automatic keyword/abstention score | 6/16 (0.38) | 5/17 (0.29) | 14/17 (0.82) |
| Infrastructure errors | 1 timeout (Q17, 304.73 s) | 0 | 0 |
| Grounded score | 1/14 (0.14) | 0/14 (0.00) | 6/14 (0.43) |
| Cited expected-source recall | 0.50 | 0.00 | 1.00 |
| Full expected-source recall at top 5 | — | — | 14/14 |
| Top-1 source hit rate (at least one expected file) | — | — | 14/14 |
| "Not in docs" phrase score | 2/2 | 0/3 | 3/3 |
| Exact-term automatic score | 0/4 | 2/4 | 4/4 |
| Exact-term manual grades (correct / partial / wrong) | 0 / 0 / 4 | 2 / 1 / 1 | 4 / 0 / 0 |
| Answerable manual grades (correct / partial / wrong; 14 questions) | 2 / 8 / 4 | 4 / 4 / 6 | 11 / 3 / 0 |
| Correct not-in-docs abstentions | 2/2 completed (Q17 timeout) | 0/3 | 3/3 |
| All-completed manual grades (correct / partial / wrong) | 4 / 8 / 4 | 4 / 4 / 9 | 14 / 3 / 0 |
| Citation support on answerable questions | 1/14 | 0/14 | 12/14 |
| Citation support on not-in-docs questions | 0/2 | 0/3 | 0/3 |
| Citation support overall | 1/16 | 0/17 | 12/17 |
| Answers marked unverified by the heuristic | 10/16 | 0/17 | 8/17 |
| Average model calls per question | 4.94 | 1.00 | 2.65 |
| Average tokens per question | 8,653 | 112 | 3,806 |
| Average latency per completed answer | 10.50 s | 1.28 s | 5.86 s |

RAG achieved full expected-source recall at top 5 on 14/14 corpus-answer questions: every expected file appeared in the retrieved top five. The separate `retrieval_check.py` top-1 hit rate was also 14/14, but a hit means only that at least one expected file appeared first, not that every expected file was retrieved at rank one. RAG indexed 2,449 chunks from 158 files. Its latency was measured with the index already built, excluding the one-time index build. RAG had no infrastructure errors.

On the 14 answerable questions, agentic search scored 2 / 8 / 4 and no retrieval scored 4 / 4 / 6 (correct / partial / wrong); RAG scored 11 / 3 / 0. The agent's two completed not-in-docs answers abstained correctly; its Q17 run timed out after 304.73 seconds. No retrieval abstained correctly on 0/3 not-in-docs questions, while RAG did so on 3/3. Overall counts alone are misleading: agentic search and no retrieval each have four correct grades, but two of the agent's four are correct abstentions while all four no-retrieval correct grades are on answerable questions. The RAG total includes its three correct abstentions as well.

The no-retrieval model supplied no citations, so its 0/17 overall means no answer had supporting citations. For the answerable questions, citation support was 1/14 for agentic search, 0/14 for no retrieval, and 12/14 for RAG. For not-in-docs answers, support was 0/2, 0/3, and 0/3. The RAG prompt requires a citation for every claim; this can induce unsupported citations on correct absence claims, as seen in Q15–Q17.

### Blind second pass

A second AI reviewer graded 50 randomly ordered completed answers with system labels withheld; the agent's timed-out Q17 was excluded. Its answer grades were 4 / 5 / 7 for agentic search, 4 / 4 / 9 for no retrieval, and 14 / 3 / 0 for RAG. Against the original grades, exact answer-grade agreement was 43/50 overall: 11/16 agent answers, 15/17 no-retrieval answers, and 17/17 RAG answers. Raw citation-support judgments agreed on 48/50 answers.

The second reviewer marked RAG Q7's citations as supported, but the answer first claims the token URL is `/token`; the cited documentation defines `tokenUrl="token"` as relative. That citation judgment was reviewed against the source and remains unsupported, so the reported RAG citation-support result stays 12/17 (the blind pass alone counted 13/17). The labels were hidden, but answer style and citations can reveal the system; this AI regrade is a consistency check, not independent-human inter-rater reliability.

Citation support is a strict binary judgment: "yes" means every cited line supports the claim it accompanies. The automatic score uses required substrings and phrase-based abstention, not semantic answer correctness. The grounded score is also heuristic.

RAG's 14 fully correct grades include its three correct not-in-docs abstentions. On the 14 answerable questions, it scored 11 correct, 3 partial, and 0 wrong. The partial answers were Q7 (it gave `/token` rather than the documented relative `token` URL), Q8 (it omitted `@pytest.mark.anyio`, `async def`, and the TestClient limitation for async tests), and Q9 (it omitted that a waiting request does not occupy a worker thread). Q3 was manually correct despite failing the exact-phrase automatic score. Q15–Q17 abstained correctly, but their citations did not support the absence claims.

Questions 1–3 were used repeatedly while debugging the agent and as the RAG smoke test, so their results may be optimistic. Questions were written from the source docs and share some vocabulary and phrasing with them, which may make retrieval unusually easy and limits generalization to independently worded queries. Q6 was rewritten after the first wording included its own answer (`--workers 4`). The no-retrieval baseline's four correct answers on answerable questions without document access suggest training-data contamination of this benchmark.

Raw per-question JSONL results and grade files are locally ignored; this report preserves the comparison without publishing generated answer logs.
