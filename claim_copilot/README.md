# Freight Claim Evidence Copilot

A dependency-light local prototype for `FCL-2026-0147`. It demonstrates a source-linked evidence ledger, deterministic reconciliation and contract treatment, explainable historical retrieval, and an approval-required negotiation draft.

## Run

Use the bundled Python runtime because it includes `pypdf` for native-PDF extraction:

```bash
/Users/ayushtrivedi/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 claim_copilot/app.py
```

Open `http://127.0.0.1:8000`.

## Demo flow

1. Start at **Overview** and state the demand, offer, and direct-cargo gap.
2. Open **Evidence & findings** and select the 59 EDI vs 58 signed-POD conflict.
3. Open **Contract position** to show that cargo is below the estimated liability cap but the delay markdown is contractually excluded.
4. Open **Similar claims** to explain the comparator score rather than claiming a settlement prediction.
5. Generate a **review-required draft** and inspect its citations/validation.

## Design choices

* Native structured parsers and deterministic rules are used before any generative reasoning.
* The scanned inspection report is represented as a reviewed OCR extraction. In a production system, the OCR worker creates this record and consequential low-confidence fields are routed for review.
* The current draft provider is deterministic so the application works without secrets. `build_draft` is the intentionally isolated provider boundary for a schema-constrained LLM integration. Any provider must return source fact IDs and pass the same numeric/citation validation.
* No document can send email or settle the claim. The visible draft is approval-required.

## Tests

```bash
/Users/ayushtrivedi/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 claim_copilot/test_app.py
```
