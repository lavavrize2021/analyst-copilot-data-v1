# Analyst Copilot

Evidence-first QA chatbot for SEC filings. It ingests an unseen filing, retrieves page-level evidence, answers only after strict validation, and otherwise says **"Not found in this filing."**

## Run from scratch

Python 3.11+; no third-party packages are required.

```powershell
ollama pull qwen2.5:3b   # one-time setup
ollama serve             # keep running in a separate terminal
python scripts/import_filings.py   # optional: preload sample filings
python app.py
```

Open <http://127.0.0.1:8000>. Use **Add filing** for `.htm`, `.html`, or `.txt` SEC filings (up to 80 MB). Status updates live; typical filings process in seconds.

Optional environment variables:

| Variable | Default | Purpose |
|---|---|---|
| `OLLAMA_MODEL` | `qwen2.5:3b` | Local model name |
| `OLLAMA_URL` | `http://127.0.0.1:11434` | Ollama server URL |
| `HOST` | `127.0.0.1` | Bind address |
| `PORT` | `8000` | Listen port |
| `COPILOT_DATA_DIR` | `.copilot_data/` | Filing storage directory |

## How it works

1. **Ingest** — SEC HTML is parsed using CSS `page-break` boundaries as citation units. Table cells are stored with `|` separators for fidelity; these are cleaned to readable prose before the model sees them.
2. **Retrieve** — BM25 ranks all pages at query time. Financial query expansion (e.g. "asset turnover" → adds "average total assets revenues") ensures relevant pages surface. Top 3–4 pages are selected.
3. **Synthesise** — A local Ollama model receives focused 600-char snippets centred on query terms (not raw page heads). Three prompt modes adapt to the question type:
   - **Simple lookup** — answer with units and a short quote
   - **Comparison** — state both values and compute the change
   - **Ratio/calculation** — show explicit arithmetic (X / Y = Z); Python re-executes the division to verify
4. **Gate** — The answer is accepted only if: the cited page was retrieved, every quote word appears in that page's text, and confidence ≥ 0.72. Any failure returns "Not found in this filing."

## Verify

```powershell
python -m unittest discover -v
python scripts/evaluate_retrieval.py
```

The evaluator reports gold-page hit@1 and hit@5 against the FinanceBench evidence set (zero-based indices; the evaluator accounts for the one-based user-facing page numbers).

## Current limitations

- Dependency-free ingestion accepts SEC HTML/text only — scanned PDFs require OCR pre-processing.
- CPU inference with `qwen2.5:3b` takes 30–60 s per question; a GPU or cloud API (e.g. Groq) reduces this to 2–5 s.
- Complex calculations whose inputs span more than one page depend on BM25 surfacing all required pages.
- Production deployment should add authentication, encrypted storage, and rate limiting.

See [APPROACH.md](APPROACH.md) for design decisions and measurement.
