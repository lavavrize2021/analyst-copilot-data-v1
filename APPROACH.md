# Approach note

The scoring rule shaped the system: unsupported confidence is worse than silence. Retrieval and synthesis are separate; a deterministic evidence gate sits after the model and is independent of it.

## What I built

**Chunking.** Each SEC HTML filing is split by CSS `page-break-after/before: always` rules rather than arbitrary token windows. This mirrors the document's own pagination, so every answer can cite the exact printed page number. Table cells are stored with `|` delimiters for structural fidelity; they are cleaned to readable prose (`Total revenues $500,343`) before being sent to the model.

**Retrieval.** BM25 with per-page TF dictionaries computed at index time. A query expansion dictionary maps financial shorthand to filing vocabulary — e.g. `"asset turnover"` adds `"average total assets revenues turnover"` to the query — so pages with the right numbers surface even when the user's phrasing differs from the filing's language. Top 8 candidates are retrieved; 3–4 are forwarded to the model (4 for calculation questions, where multiple source pages are often needed).

**Synthesis — three prompt modes.** Question intent is classified at runtime:

- *Ratio mode* (`RATIO_RE`): questions asking for a computed ratio, turnover, or margin. The model is instructed to show explicit arithmetic (`X / Y = Z`). Python parses that expression and re-executes the division, replacing the model's result with the verified value.
- *Comparison mode* (`CALC_RE` but not `RATIO_RE`): questions about change, difference, or multi-year comparison. The model is asked to state both values and compute the change in natural language.
- *Lookup mode*: all other questions. The model returns a concise answer with units and a short verbatim quote.

In all modes, evidence is a 600-character snippet centred on the query terms — not the raw page head — reducing model input by ~7× versus the original design and bringing response time within acceptable range on CPU.

**Evidence gate.** After synthesis, four conditions must all pass or the answer becomes "Not found in this filing.":
1. The cited page number appears in the retrieved set.
2. The quote is non-empty.
3. Every token of the normalised quote is a subset of the tokens of the normalised page text (dollar signs and commas removed). This is looser than exact substring matching, which was fragile when the model added minor connecting words, but still rules out hallucinated quotes.
4. Confidence ≥ 0.72.

**Storage.** Filings are stored by SHA-256 content hash. Re-uploading the same file is instant. Processing is asynchronous with live progress feedback.

## What I measured

`scripts/evaluate_retrieval.py` reports hit@1 and hit@5 against the FinanceBench gold-page evidence set. This isolates retrieval failures from generation failures. The confidence threshold and retrieval depth would be tuned on a company-held-out split, optimising +1/0/−1 utility rather than raw answer rate.

## What I kept

Page-level retrieval, visible ingestion status, content-addressed persistence, verbatim quotations, a model-independent post-check, explicit abstention, and a fully offline default (no API keys required).

## What I discarded

Answer-key lookup cannot generalise. Fixed-size token chunks make citations ambiguous. Similarity scores are not confidence. Forced answering is harmful — the system treats a wrong answer as worse than no answer.

## Trade-offs and next steps

- CPU inference is the main speed bottleneck; switching to Groq's free API or any GPU-backed endpoint resolves it without code changes (set `OLLAMA_URL`).
- Multi-page calculations (where the numerator and denominator live on different pages) depend on BM25 surfacing both; query expansion partially addresses this, but a more robust solution would decompose the question into sub-queries.
- Next steps: layout-aware PDF/OCR ingestion, multi-page evidence aggregation, threshold calibration on held-out companies, authentication and rate limiting for production.
