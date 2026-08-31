# Analyst Copilot

Evidence-first QA chatbot for SEC filings. It ingests an unseen filing, retrieves page-level evidence, answers only after strict validation, and otherwise says **“Not found in this filing.”**

## Run from scratch

Python 3.11+; no third-party packages are required.

```powershell
$env:OPENAI_API_KEY="your-key"  # optional; otherwise safe retrieval-only mode
python scripts/import_filings.py # optional: preload supplied filings
python app.py
```

Open <http://127.0.0.1:8000>. Use **Add filing** for `.htm`, `.html`, `.txt`, or `.md`. Status is visible and typical filings process in seconds. Optional settings: `HOST`, `PORT`, `COPILOT_DATA_DIR`, `OPENAI_MODEL`.

## Trust boundary

SEC HTML page breaks become citation boundaries. A BM25 index retrieves pages. With an API key, the Responses API returns schema-constrained answer/page/quote/confidence. The app then verifies that the page was retrieved, the quote occurs verbatim, and confidence is at least 0.72; failure means abstention. Without a key, it safely abstains while showing candidate evidence. Practice answers are never used at runtime.

## Verify

```powershell
python -m unittest discover -v
python scripts/evaluate_retrieval.py
```

The evaluator reports gold-page hit@1 and hit@5. FinanceBench evidence indices are zero-based while user-facing pages are one-based, which the evaluator accounts for.

Current limitation: dependency-free ingestion accepts SEC HTML/text, not scanned PDF. Production should add layout-aware PDF/OCR, authentication, encrypted storage, and rate limiting.

See [APPROACH.md](APPROACH.md) for design decisions and measurement.
