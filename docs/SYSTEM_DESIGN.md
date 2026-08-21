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
  genai_service.py  ← bounded evidence packet → Bedrock → validated draft
        │
        ▼
  FastAPI  (api.py)
        │
        ▼
  Frontend  (React-style SPA)
```

---

## Key Design Decisions

### Deterministic first, GenAI second

Contract rules, reconciliation, and comparator scoring are pure functions on typed inputs. No model call changes a dollar amount or a finding.

The GenAI boundary is strictly isolated in `genai_service.py`:
- It receives a **pre-computed, sanitised evidence packet** — not raw documents
- It produces **negotiation prose only** — no calculations
- Every output is **validated** before being returned: required fields, grounded citations, `approval_required: true`
- Any failure returns the **deterministic fallback** transparently — the server never crashes

This separation means the LLM can be swapped, upgraded, or disabled without touching the evidence pipeline or contract logic.

### Evidence-linked facts

Every extracted value carries `EvidenceAnchor(file, locator, source_role, confidence)`. The frontend opens the original source file at the anchor location. GenAI citations are also grounded to these fact IDs — the validator rejects any citation that references a fact not in the evidence packet.

### Conflicts are first-class outputs

`COUNT_MISMATCH` (EDI 59 vs POD 58) is a `ReconciliationFinding` — not silently resolved, not hidden. The GenAI prompt explicitly instructs the model to acknowledge disputed information rather than paper over it.

### S3-aware pipeline

When source documents are uploaded via the frontend, `_try_s3_documents()` downloads them by claim ID and routes each file to the correct parser by filename. Fixture files are the fallback when nothing is uploaded.

### Prompt injection defence

The system prompt is passed as a separate `system` field (Anthropic) or `system` role message (Mistral/OpenAI-compatible), keeping it structurally separate from the evidence data. The prompt explicitly instructs the model to treat evidence field values as data, not instructions — so injected text in a fact value cannot override the system rules.

---

## AWS Services Used

| Service | Purpose |
|---|---|
| S3 | Document storage per claim (`claims/{id}/documents/`) |
| Textract | OCR for scanned inspection PDF (`detect_document_text`) |
| Bedrock | Negotiation draft generation via `invoke_model` |

**Active model:** `mistral.mistral-large-3-675b-instruct` (ap-south-1)  
**Fallback model:** any model with `BEDROCK_MODEL_ID` env var  
**Disabled by default:** `GENAI_ENABLED=false`

---

## GenAI Layer Detail

### Evidence packet (what is sent to Bedrock)

```
{
  claim: { id, carrier, status, demand, offer, direct_cargo },
  verified_facts: [ { id, label, value, status, anchors } ],
  findings: [ { id, severity, title, detail } ],
  contract_position: { key: { amount, status, clause } },
  historical_comparators: [ top-3 scored matches ]
}
```

Raw document bytes, credentials, application state, and unverified fields are **never** sent to the model.

### Output schema (required from model)

```json
{
  "subject": "string",
  "body": "string",
  "citations": [{ "claim": "string", "fact_ids": ["string"], "rule": "string|null" }],
  "unsupported_claims": ["string"],
  "approval_required": true
}
```

### Validation gates (rejection criteria)

| Check | Action on failure |
|---|---|
| Valid JSON | Fallback |
| Required fields present | Fallback |
| `approval_required === true` | Fallback |
| All cited `fact_ids` exist in packet | Fallback |
| `subject` and `body` non-empty strings | Fallback |
| AWS/Bedrock exception | Fallback |

### Fallback behaviour

When GenAI is disabled or fails, the response includes:
```json
{
  "mode": "deterministic_fallback",
  "validation": "fallback",
  "fallback_reason": "<reason>"
}
```

The frontend receives a usable draft regardless — the user is never blocked.

### Model provider support

`genai_service.py` detects the model family from `BEDROCK_MODEL_ID` and uses the correct request format:

| Model family | Request format |
|---|---|
| `anthropic.*` / `claude.*` | Anthropic Messages API |
| `mistral.*` / others | OpenAI-compatible Messages API |
| `titan.*` | Amazon Titan `inputText` format |

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

Frontend Draft
    → POST /api/draft
    → build_case() → build_draft() [deterministic]
    → genai_service.generate_draft(case, deterministic_fallback)
    → build_evidence_packet() → Bedrock invoke_model
    → _validate(output, packet)
    → return { mode: "bedrock" } or { mode: "deterministic_fallback" }
```

---

## What Is Not Implemented (Known Limits)

- `10_carrier_service_agreement.pdf` is not parsed — contract rules are hardcoded
- `06_commercial_invoice.pdf` and `07_bill_of_lading.pdf` are not parsed — values come from ERP CSV
- Photos (`13_`, `14_`) are not analyzed — no image/vision model
- No authentication, no multi-tenant isolation, single-claim scope
- Anthropic Claude models require USD billing on AWS India accounts — Mistral is used as the active model
