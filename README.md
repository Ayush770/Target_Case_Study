# Freight Claim Copilot

Evidence-led freight claim analysis tool for claim **FCL-2026-0147**.

Uploads claim documents to S3, extracts structured evidence, reconciles conflicting data, applies contract rules, retrieves historical comparables, and generates an approval-required negotiation draft — all traceable to source files.

→ **[System Design](docs/SYSTEM_DESIGN.md)** | **[Exercise Brief](docs/EXERCISE_BRIEF.md)**

---

## Quick Start

```bash
git clone https://github.com/Ayush770/Target_Case_Study.git
cd Target_Case_Study/claim_copilot
pip install -r requirements.txt
uvicorn api:app --reload
```

Open **`http://127.0.0.1:8000`**

> Runs fully without AWS credentials using built-in fixture documents. AWS is required only for S3 upload and Textract OCR.

---

## AWS Setuppip install -r requirements.txt

```bash
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_REGION=ap-south-1
export S3_BUCKET=candidate-pack-claims-dev-133715233089
```

Copy `.env.example` → `.env` and `source .env` as an alternative.

If `~/.aws/config` uses a `login_session` provider: `aws login` then restart the server.

---

## Application Flow

```
Upload Documents tab → POST /claims/{id}/documents → S3
Run Analysis button  → POST /claims/{id}/analyze   → pipeline
Overview tab         → GET  /api/claim/{id}         → results
```

**Document → evidence role mapping:**

| Upload filename contains | Parsed as |
|---|---|
| `03_claim_snapshot` | Claim header (demand, carrier, owner) |
| `04_tms_shipment` | TMS/EDI events |
| `05_erp_order_invoice` | Invoice value, cargo cap |
| `08_proof_of_delivery` | Carton counts, delivery exceptions |
| `09_damage_inspection` | Damage facts (via Textract OCR) |

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/` | Frontend |
| GET | `/health` | Health check |
| POST | `/claims/{id}/documents` | Upload to S3 |
| POST | `/claims/{id}/analyze` | Run analysis pipeline |
| GET | `/api/claim` | Default claim workspace |
| GET | `/api/claim/{id}` | Claim workspace by ID |
| POST | `/api/draft` | Negotiation draft |
| GET | `/evidence/{filename}` | Serve source file |

Interactive docs: `http://127.0.0.1:8000/docs`

---

## Frontend Tabs

| Tab | Shows |
|---|---|
| Upload Documents | Upload files to S3, trigger analysis |
| Overview | Demand, offer, gap, findings, timeline |
| Evidence & Findings | Source-linked fact ledger |
| Contract Position | Rule outputs with formulas |
| Similar Claims | Ranked historical comparators |
| Negotiation Draft | Approval-required draft with citations |

---

## Running Tests

```bash
cd claim_copilot

# Unit tests (no AWS needed)
python3 -m pytest test_app.py -v
python3 test_reconciliation.py
python3 test_contract_engine.py

# End-to-end integration test (AWS credentials required)
python3 -m pytest test_e2e_integration.py -v
```

**Integration test result: 15/15 PASSED** (S3 upload → analysis → frontend verified)

---

## Project Structure

```
Target_Case_Study/
│
├── README.md                     ← you are here
├── docs/
│   ├── SYSTEM_DESIGN.md          ← architecture and design decisions
│   └── EXERCISE_BRIEF.md         ← original Target exercise brief
│
├── claim_copilot/                ← the application
│   ├── api.py                    FastAPI server (entry point)
│   ├── app.py                    Fixture builder + draft generator
│   ├── claim_processor.py        Pipeline orchestrator
│   ├── s3_service.py             AWS S3 client
│   ├── textract_service.py       AWS Textract client
│   ├── reconciliation.py         Conflict detection
│   ├── contract_engine.py        Contract rule evaluation
│   ├── historical_comparator.py  Similarity scoring
│   ├── requirements.txt
│   ├── .env.example
│   ├── test_e2e_integration.py   End-to-end regression (AWS)
│   ├── test_*.py                 Unit tests
│   └── static/                  Frontend (HTML/CSS/JS)
│
├── 03_claim_snapshot.json        }
├── 04_tms_shipment.json          }  Target-provided case
├── 05_erp_order_invoice.csv      }  documents — used directly
├── 08_proof_of_delivery.pdf      }  as pipeline inputs
├── 09_damage_inspection_report_scanned.pdf
├── 12_historical_claims.csv
└── 01_case_overview.pdf … 15_data_dictionary.md
```

---

## Known Limitations

- `10_carrier_service_agreement.pdf` not parsed — contract rules are hardcoded
- Photos not analyzed — no image/vision model
- No authentication or multi-tenant isolation

---

## GenAI Layer — Amazon Bedrock

The deterministic pipeline calculates **all claim values and contract positions**.  
Bedrock is used **only** to draft grounded negotiation prose from the pre-built evidence packet.

### How it works

1. Deterministic code computes direct cargo loss, contract positions, and reconciliation findings.
2. A bounded evidence packet (facts, positions, comparators — no raw documents or credentials) is sent to Bedrock.
3. Bedrock drafts a negotiation message citing only facts and rules present in the packet.
4. The response is validated: required fields, grounded citations, `approval_required: true`.
5. Human approval is required before the draft is sent.
6. Any failure — disabled, missing model ID, invalid JSON, AWS error, failed validation — returns the deterministic fallback transparently.

### Enabling GenAI

```bash
export GENAI_ENABLED=true
export AWS_REGION=ap-south-1
export BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
uvicorn api:app --reload
```

Without `GENAI_ENABLED=true`, the `/api/draft` endpoint returns the deterministic fallback draft with `"mode": "deterministic_fallback"`.

### What the model cannot do

- Recalculate claim values or contract liability
- Resolve evidence conflicts (EDI vs POD)
- Invent facts, amounts, dates, or citations
- Set `approval_required` to anything other than `true`
