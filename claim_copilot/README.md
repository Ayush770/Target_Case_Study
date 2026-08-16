# Freight Claim Evidence Copilot

A source-linked evidence and negotiation workspace for claim `FCL-2026-0147`.

## Run

```bash
pip install -r requirements.txt
uvicorn api:app --reload
```

Open `http://127.0.0.1:8000`.

## Demo flow

1. **Upload** — use the Upload tab to register claim documents (requires AWS S3).
2. **Overview** — review demand, carrier offer, direct-cargo gap, findings, and timeline.
3. **Evidence & findings** — inspect the fact ledger and the 59 EDI vs 58 signed-POD conflict.
4. **Contract position** — cargo is below the liability cap; delay markdown is contractually excluded.
5. **Similar claims** — explainable comparator scores, not a settlement prediction.
6. **Negotiation draft** — approval-required draft with citation grounding.

## Design choices

- Deterministic parsers and contract rules run before any generative reasoning.
- The scanned inspection report uses AWS Textract for OCR; falls back gracefully when credentials are absent.
- `build_draft` in `app.py` is the intentionally isolated LLM provider boundary — swap it for any schema-constrained model.
- No action (upload, draft send) happens without explicit user initiation.

## Tests

```bash
python3 -m pytest test_*.py -v
```
