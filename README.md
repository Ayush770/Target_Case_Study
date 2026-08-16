# Freight Claim Copilot

An evidence-led freight claim analysis tool built for claim **FCL-2026-0147**. It extracts facts from structured and scanned documents, reconciles conflicting evidence, applies deterministic contract rules, retrieves comparable historical claims, and produces an approval-required negotiation draft — all traceable back to source files.

---

## Quick Start

### 1. Clone

```bash
git clone https://github.com/Ayush770/Target_Case_Study.git
cd Target_Case_Study
```

### 2. Install dependencies

```bash
cd claim_copilot
pip install -r requirements.txt
```

### 3. Start the server

```bash
uvicorn api:app --reload
```

### 4. Open the application

```
http://127.0.0.1:8000
```

> The application runs fully without AWS credentials. Inspection report OCR via AWS Textract is attempted and gracefully skipped if credentials are absent — all other evidence sources (POD PDF, TMS JSON, ERP CSV) are processed locally.

---

## AWS Setup (optional — enables Textract OCR and S3 document upload)

The application runs fully without AWS credentials using the built-in fixture files.
To enable document upload and Textract OCR, configure credentials **before** starting the server.

```bash
# Option 1 — environment variables (recommended, bypasses any custom credential providers)
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_REGION=ap-south-1
export S3_BUCKET=candidate-pack-claims-dev-133715233089

# Option 2 — copy and fill in .env.example
cp claim_copilot/.env.example claim_copilot/.env
# edit claim_copilot/.env, then:
source claim_copilot/.env

# Option 3 — re-authenticate if ~/.aws/config uses a login_session provider
aws login   # or: aws sso login --profile candidate-pack
```

After setting credentials, verify with:
```bash
aws sts get-caller-identity
aws s3 ls s3://candidate-pack-claims-dev-133715233089
```

> **Note:** If `~/.aws/config` contains a `login_session` field (custom credential provider),
> environment variables take priority and will bypass it. Set `AWS_ACCESS_KEY_ID` and
> `AWS_SECRET_ACCESS_KEY` to use standard IAM credentials regardless of the config file.

---

## Application Flow

```
Frontend Upload Panel
        ↓
POST /claims/{claim_id}/documents  →  AWS S3
        ↓
POST /claims/{claim_id}/analyze
        ↓
  Evidence Pipeline
  ├── POD PDF      → pod_parser.py
  ├── TMS JSON     → tms_evidence_adapter.py
  └── Inspection   → textract_evidence_adapter.py (+ AWS Textract)
        ↓
  Reconciliation   → reconciliation.py
        ↓
  Contract Rules   → contract_engine.py
        ↓
  Historical Match → historical_comparator.py
        ↓
GET /api/claim  →  Frontend Workspace
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Frontend workspace |
| `GET` | `/health` | Health check |
| `POST` | `/claims/{claim_id}/documents` | Upload document to S3 |
| `POST` | `/claims/{claim_id}/analyze` | Run full claim analysis pipeline |
| `GET` | `/api/claim` | Frontend claim data (default: FCL-2026-0147) |
| `GET` | `/api/claim/{claim_id}` | Frontend claim data by ID |
| `POST` | `/api/draft` | Generate negotiation draft |
| `GET` | `/evidence/{filename}` | Serve source evidence file |

Interactive API docs: `http://127.0.0.1:8000/docs`

---

## Frontend Tabs

| Tab | What it shows |
|-----|---------------|
| **Upload** | Upload claim documents to S3; trigger analysis |
| **Overview** | Demand, offer, direct cargo gap, findings, timeline |
| **Evidence & Findings** | Source-linked fact ledger with evidence anchors |
| **Contract Position** | Deterministic contract rule outputs with formulas |
| **Similar Claims** | Ranked historical comparators with match reasoning |
| **Negotiation Draft** | Approval-required draft with citation grounding |

---

## Project Structure

```
Target_Case_Study/
├── 03_claim_snapshot.json        # Claim metadata
├── 04_tms_shipment.json          # TMS / EDI events
├── 05_erp_order_invoice.csv      # ERP order lines
├── 08_proof_of_delivery.pdf      # Signed POD
├── 09_damage_inspection_report_scanned.pdf
├── 12_historical_claims.csv      # 30 prior claims
└── claim_copilot/
    ├── api.py                    # FastAPI server (entry point)
    ├── app.py                    # Evidence fixture + draft builder
    ├── claim_processor.py        # Pipeline orchestrator
    ├── claim_evidence.py         # Evidence container
    ├── evidence.py               # EvidenceFact / EvidenceAnchor models
    ├── reconciliation.py         # Conflict detection
    ├── contract_engine.py        # Contract rule evaluation
    ├── historical_comparator.py  # Similarity scoring
    ├── pod_parser.py             # POD PDF parser
    ├── tms_evidence_adapter.py   # TMS/EDI adapter
    ├── textract_evidence_adapter.py  # Inspection OCR adapter
    ├── document_extractor.py     # PDF text extraction
    ├── textract_service.py       # AWS Textract client
    ├── s3_service.py             # AWS S3 client
    ├── requirements.txt
    └── static/
        ├── index.html
        ├── app.js
        └── styles.css
```

---

## Design Principles

- **Deterministic first** — contract rules and reconciliation run without LLM calls
- **Evidence-linked** — every displayed fact traces back to a source file and location
- **Conflicts surfaced** — COUNT_MISMATCH and evidence gaps are first-class outputs, not hidden
- **Human approval gate** — the draft cannot be sent; it requires specialist review
- **Graceful degradation** — app runs fully offline; AWS services enhance it when available

---

## Running Tests

```bash
cd claim_copilot
python3 -m pytest test_*.py -v
```
