# Approach note

The scoring rule shaped the system: unsupported confidence is worse than silence. I separated retrieval from answering and placed a deterministic evidence gate after the model. The runtime never uses the practice answer key.

**What I tried.** Each rendered filing page is the citation unit. SEC HTML retains page-break CSS, which gives more faithful locations than arbitrary token chunks. Table cells remain in reading order, and BM25 ranks pages. Synthesis produces schema-constrained answer, page, verbatim quote, and confidence. The gate verifies the page was retrieved, the quote occurs exactly there, and confidence exceeds 0.72. Failure becomes “Not found in this filing.” Upload processing is asynchronous and persisted by content hash.

**What I measured.** The 136 practice questions are used only offline. `scripts/evaluate_retrieval.py` reports page hit@1 and hit@5 against gold evidence; unit tests cover page splitting and retrieval. This separates retrieval failures from generation failures. I would tune retrieval depth and confidence on a company-held-out split, optimizing +1/0/−1 utility rather than answer rate.

**What I kept.** Page-level retrieval, visible ingestion status, content-addressed persistence, verbatim quotations, a model-independent post-check, and explicit abstention. With no credentials the app remains useful as a safe evidence finder.

**What I discarded.** Answer-key lookup cannot generalize; fixed-size chunks make citations ambiguous; similarity is not confidence; forced answering is harmful; and table columns or units must never be guessed.

**Trade-offs.** Pages can be long and complex calculations may span pages. The current path supports HTML/text, not scans. Next I would add layout-aware PDF/OCR and multi-page evidence, then calibrate thresholds on held-out companies.
