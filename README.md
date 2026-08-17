# Freight Claim Copilot

An evidence-led freight claim analysis tool for claim **FCL-2026-0147**. Extracts structured facts from uploaded claim documents stored in AWS S3, reconciles conflicting evidence, applies deterministic contract rules, retrieves comparable historical claims, and generates an approval-required negotiation draft — all traceable to source files.

---

## Quick Start

```bash
git clone https://github.com/Ayush770/Target_Case_Study.git
cd Target_Case_Study/claim_copilot
pip install -r requirements.txt
uvicorn api:app --reload
```

Open **`http://127.0.0.1:8000`**

> The app runs fully without AWS credentials using the built-in fixture documents. AWS credentials are required only for S3 document upload and Textract OCR on scanned PDFs.

---

## AWS Configuration

Set environment variables before starting the server:

```bash
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_REGION=ap-south-1
export S3_BUCKET=candidate-pack-claims-dev-133715233089
```

Or copy and fill `.env.example`:

```bash
cp .env.example .env
source .env
```

If `~/.aws/config` uses a `login_session` provider (custom SSO):

```bash
aws login   # or: aws sso login --profile candidate-pack
```

Verify:

```bash
aws sts get-caller-identity
aws s3 ls s3://candidate-pack-claims-dev-133715233089
```

> Environment variables take priority over any `login_session` profile in `~/.aws/config`.

---

## Architecture and Data Flow

```
Frontend (HTML/CSS/JS)
        │
        ▼
FastAPI  (api.py)
        │
   ┌────┴────────────────────────────┐
   │                                 │
   ▼                                 ▼
POST /claims/{id}/documents    POST /claims/{id}/analyze
        │                                 │
        ▼                                 ▼
   S3Service                      process_claim()
   upload_file()                         │
        │                      _try_s3_documents()
        ▼                                │
   AWS S3 bucket               S3Service.list + download
   claims/{id}/documents/               │
                               ┌────────┴──────────────┐
                               │                       │
                               ▼                       ▼
                         pod_parser            textract_evidence_adapter
                         tms_evidence_adapter  document_extractor
                               │
                               ▼
                         ClaimEvidence (EvidenceFact + EvidenceAnchor)
                               │
                    ┌──────────┼──────────────┐
                    ▼          ▼              ▼
             reconciliation  contract_engine  historical_comparator
                    │          │              │
                    └──────────┴──────────────┘
                               │
                               ▼
                    build_frontend_claim_response()
                               │
                               ▼
                    GET /api/claim/{id}  →  Frontend renders
```

---

## Components

| File | Role |
|---|---|
| `api.py` | FastAPI server — all endpoints, serialization, frontend adapter |
| `app.py` | Fixture evidence builder, `build_case()`, `build_draft()` |
| `claim_processor.py` | Pipeline orchestrator — S3 retrieval, evidence aggregation, analysis |
| `s3_service.py` | AWS S3 client — upload, download, list by claim |
| `textract_service.py` | AWS Textract OCR for scanned PDFs |
| `claim_evidence.py` | `ClaimEvidence` container |
| `evidence.py` | `EvidenceFact` / `EvidenceAnchor` models |
| `pod_parser.py` | POD PDF → evidence facts |
| `tms_evidence_adapter.py` | TMS JSON → evidence facts |
| `textract_evidence_adapter.py` | Inspection OCR text → evidence facts |
| `document_extractor.py` | pypdf text extraction |
| `reconciliation.py` | COUNT_MISMATCH and conflict detection |
| `contract_engine.py` | Cargo cap, inspection, repack, delay rules |
| `historical_comparator.py` | Similarity scoring against historical claims |
| `static/` | Frontend — index.html, app.js, styles.css |

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Frontend workspace |
| `GET` | `/health` | Health check |
| `POST` | `/claims/{claim_id}/documents` | Upload document to S3 |
| `POST` | `/claims/{claim_id}/analyze` | Run full analysis pipeline |
| `GET` | `/api/claim` | Frontend claim data (fixture: FCL-2026-0147) |
| `GET` | `/api/claim/{claim_id}` | Frontend claim data by ID |
| `POST` | `/api/draft` | Generate negotiation draft |
| `GET` | `/evidence/{filename}` | Serve source evidence file |

Interactive docs: `http://127.0.0.1:8000/docs`

---

## Upload → S3 → Analysis Workflow

1. Open `http://127.0.0.1:8000` → **Upload Documents** tab
2. Set Claim ID (default: `FCL-2026-0147`)
3. Upload any of the source documents:
   - `03_claim_snapshot.json` → claim header (demand, carrier, owner)
   - `04_tms_shipment.json` → TMS/EDI events
   - `05_erp_order_invoice.csv` → invoice value, cargo cap
   - `08_proof_of_delivery.pdf` → carton counts, delivery exceptions
   - `09_damage_inspection_report_scanned.pdf` → damage facts (via Textract)
4. Click **Run Claim Analysis**
5. Results load automatically in the **Overview** tab

The pipeline retrieves uploaded documents from S3 by claim ID and uses them in place of fixture files. For any document not uploaded, the pipeline falls back to the corresponding fixture file from the repository.

**Document → role mapping:**

| Filename substring | Evidence role | Parser |
|---|---|---|
| `03_claim_snapshot`, `claim_snapshot` | snapshot | json |
| `04_tms`, `tms`, `shipment` | tms | `tms_evidence_adapter` |
| `05_erp`, `erp`, `invoice` | erp | csv |
| `08_proof`, `proof_of_delivery` | pod | `pod_parser` + pypdf |
| `09_damage`, `inspection` | inspection | `textract_evidence_adapter` + Textract |

---

## Frontend Tabs

| Tab | Content |
|---|---|
| **Upload Documents** | Upload to S3, trigger analysis |
| **Overview** | Demand, offer, direct cargo gap, evidence findings, timeline |
| **Evidence & Findings** | Source-linked fact ledger with anchors |
| **Contract Position** | Deterministic contract rule outputs with formulas |
| **Similar Claims** | Ranked historical comparators with match reasoning |
| **Negotiation Draft** | Approval-required draft with citation grounding |

---

## Running Tests

```bash
cd claim_copilot

# Unit tests (no AWS required)
python3 -m pytest test_app.py -v
python3 test_reconciliation.py
python3 test_contract_engine.py
python3 test_claim_evidence.py
python3 test_evidence.py
python3 test_pod_parser.py
python3 test_historical_comparator.py
python3 test_document_extractor.py

# End-to-end integration test (AWS credentials required)
python3 -m pytest test_e2e_integration.py -v
```

---

## Integration Test Results

The end-to-end regression test (`test_e2e_integration.py`) was executed and verified against the live AWS environment:

**Result: 15/15 PASSED**

| Test | Status |
|---|---|
| `/health` returns ok | ✅ |
| `/` serves HTML | ✅ |
| Upload all 5 source documents to S3 | ✅ |
| Uploaded S3 keys verified via `list_objects_v2` | ✅ |
| Analysis returns 200 with claim_id | ✅ |
| Analysis uses S3 documents (not fixture fallback) | ✅ |
| Evidence facts have source anchors | ✅ |
| COUNT_MISMATCH reconciliation produced | ✅ |
| CARGO_LIABILITY contract position produced | ✅ |
| Historical comparables produced | ✅ |
| Frontend response schema complete | ✅ |
| Demand traces to uploaded claim_snapshot | ✅ |
| No 4xx/5xx on any endpoint | ✅ |
| Re-analysis is idempotent | ✅ |
| Fixture claim unaffected by test uploads | ✅ |

AWS services called during test: **S3** (`PutObject`, `ListObjectsV2`, `GetObject`), **Textract** (`DetectDocumentText`)

---

## Demo Workflow

1. Start server: `cd claim_copilot && uvicorn api:app --reload`
2. Open `http://127.0.0.1:8000`
3. **Overview** — review $29,920 demand, $7,225 offer, $9,350 direct cargo, $2,125 gap
4. **Evidence & Findings** — inspect COUNT_MISMATCH (EDI 59 vs POD 58), photo coverage gap, missing packaging spec
5. **Contract Position** — cargo below estimated cap; delay markdown contractually excluded on Standard LTL
6. **Similar Claims** — explainable similarity scores, settlement context for negotiation
7. **Negotiation Draft** — approval-required draft with citation grounding

---

## Design Principles

- **Deterministic first** — reconciliation, contract rules, and comparator scoring run without any LLM
- **Evidence-linked** — every fact traces to a source file, page, and locator
- **Conflicts surfaced** — COUNT_MISMATCH and evidence gaps are first-class outputs
- **Human approval gate** — the negotiation draft cannot be sent; specialist review required
- **Graceful degradation** — app runs fully offline; AWS services enhance it when available

---

## Known Limitations

- **No LLM/Bedrock** — `build_draft()` in `app.py` is a deterministic template. It is explicitly designed as the LLM provider boundary; a schema-constrained model call can replace it without touching the rest of the pipeline.
- **Textract OCR** — `09_damage_inspection_report_scanned.pdf` is image-only. Without Textract credentials the inspection facts are absent from the pipeline (not an error — the system falls back cleanly).
- **Carrier offer** — parsed from `02_claim_email_thread.eml` by `build_case()` in `app.py`. This file is not part of the S3 upload flow; the offer value always comes from the fixture email thread.
- **Single-claim scope** — the implementation processes one claim at a time. No multi-tenant isolation, authentication, or persistent database.
- **S3 bucket** — `candidate-pack-claims-dev-133715233089` is the default. Override with `S3_BUCKET` env var.
- **Historical dataset** — 30 synthetic cases. The comparator is framed as retrieval context, not a predictive settlement model.

---

## Project Structure

```
Target_Case_Study/
├── 03_claim_snapshot.json        Claim metadata
├── 04_tms_shipment.json          TMS / EDI events
├── 05_erp_order_invoice.csv      ERP order lines
├── 08_proof_of_delivery.pdf      Signed POD
├── 09_damage_inspection_report_scanned.pdf
├── 12_historical_claims.csv      30 prior claims
├── SYSTEM_DESIGN.md              Full architecture design document
└── claim_copilot/
    ├── api.py                    FastAPI server (entry point)
    ├── app.py                    Fixture builder + draft generator
    ├── claim_processor.py        Pipeline orchestrator
    ├── s3_service.py             AWS S3 client
    ├── textract_service.py       AWS Textract client
    ├── claim_evidence.py         Evidence container
    ├── evidence.py               EvidenceFact / EvidenceAnchor models
    ├── reconciliation.py         Conflict detection
    ├── contract_engine.py        Contract rule evaluation
    ├── historical_comparator.py  Similarity scoring
    ├── pod_parser.py             POD PDF parser
    ├── tms_evidence_adapter.py   TMS/EDI adapter
    ├── textract_evidence_adapter.py  Inspection OCR adapter
    ├── document_extractor.py     PDF text extraction (pypdf)
    ├── requirements.txt
    ├── .env.example              AWS credential template
    ├── test_e2e_integration.py   End-to-end regression test (AWS)
    ├── test_app.py               Gold-case fixture tests
    ├── test_*.py                 Unit tests per module
    └── static/
        ├── index.html
        ├── app.js
        └── styles.css
```
