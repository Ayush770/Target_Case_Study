# System Design — Freight Claim Copilot

## Problem

Freight claims require a specialist to manually collect evidence from emails, PDFs, TMS systems, ERP records, and inspection reports before they can negotiate with a carrier. The goal is to automate the evidence assembly and position-calculation steps so the specialist can focus on negotiation.

---

## Architecture

```
Uploaded Documents (S3)
        │
        ▼
 claim_processor.py  ← orchestrates the pipeline
        │
   ┌────┼────────────────────┐
   ▼    ▼                    ▼
 POD   TMS/EDI        Inspection (Textract OCR)
parser  adapter            adapter
   └────┼────────────────────┘
        │
        ▼
  ClaimEvidence
  (EvidenceFact + EvidenceAnchor)
        │
   ┌────┼────────────┐
   ▼    ▼            ▼
Recon  Contract   Historical
Engine  Rules     Comparator
   └────┼────────────┘
        │
        ▼
  FastAPI  (api.py)
        │
        ▼
  Frontend  (React-style SPA)
```

---

## Key Design Decisions

**Deterministic first, LLM second.**
Contract rules, reconciliation, and comparator scoring are pure functions on typed inputs. No model call changes a dollar amount or a finding. The LLM boundary is isolated in `build_draft()` — it can be swapped for any schema-constrained model without touching the pipeline.

**Evidence-linked facts.**
Every extracted value carries `EvidenceAnchor(file, locator, source_role, confidence)`. The frontend opens the original source file at the anchor location.

**Conflicts are first-class outputs.**
`COUNT_MISMATCH` (EDI 59 vs POD 58) is a `ReconciliationFinding` — not silently resolved, not hidden. Same for photo coverage gaps and missing packaging spec.

**S3-aware pipeline.**
When source documents are uploaded via the frontend, `_try_s3_documents()` downloads them by claim ID and routes each file to the correct parser by filename. Fixture files are the fallback when nothing is uploaded.

---

## AWS Services Used

| Service | Purpose |
|---|---|
| S3 | Document storage per claim (`claims/{id}/documents/`) |
| Textract | OCR for scanned inspection PDF (`detect_document_text`) |

---

## Data Flow (Upload Path)

```
Frontend Upload
    → POST /claims/{id}/documents
    → S3Service.upload_file()
    → S3: claims/{id}/documents/{filename}

Frontend Analyze
    → POST /claims/{id}/analyze
    → _try_s3_documents(claim_id) downloads from S3
    → evidence extraction → reconciliation → contract → comparators
    → GET /api/claim/{id} → frontend renders
```

---

## What Is Not Implemented (Known Limits)

- `build_draft()` returns a deterministic template — no live LLM call
- `10_carrier_service_agreement.pdf` is not parsed — contract rules are hardcoded
- `06_commercial_invoice.pdf` and `07_bill_of_lading.pdf` are not parsed — values come from ERP CSV
- Photos (`13_`, `14_`) are not analyzed — no image/vision model
- No authentication, no multi-tenant isolation, single-claim scope
