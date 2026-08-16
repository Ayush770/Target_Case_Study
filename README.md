# Freight Claim Copilot 🚚🤖

An AI-assisted freight claim analysis platform that automates evidence extraction, claim reconciliation, contractual evaluation, and historical claim comparison to support faster and more explainable freight claim decisions.

The system combines deterministic business rules with evidence-backed analysis to create an auditable claim review workflow.

---

# Overview

Freight claims typically require manual review across multiple disconnected sources:

- Proof of Delivery (POD)
- Carrier EDI/TMS events
- Commercial invoices
- Inspection reports
- Carrier agreements
- Historical claims

Freight Claim Copilot creates a unified analysis pipeline that:

1. Extracts evidence from multiple sources
2. Normalizes evidence into structured facts
3. Identifies inconsistencies
4. Applies contractual rules
5. Retrieves similar historical claims
6. Exposes results through APIs and a web interface

---

# Architecture

```
                    User
                     |
                     |
              Web Frontend
          (HTML + CSS + JavaScript)
                     |
                     |
                FastAPI Layer
                     |
        --------------------------------
        |              |               |
        |              |               |
 Evidence Engine   Contract Engine   Comparator
        |              |               |
        |              |               |
 POD Parser       Contract Rules   Historical Claims
 TMS Adapter
 Textract Adapter
        |
        |
 Claim Evidence Model
        |
        |
 Claim Decision Output
```

---

# Core Workflow

## 1. Evidence Collection

The system processes claim supporting documents:

### Sources

- Proof of Delivery PDF
- TMS Shipment JSON
- Commercial Invoice CSV
- Inspection Report PDF
- Claim Snapshot JSON
- Historical Claims Dataset


Example evidence facts:

```
POD received cartons:
58

POD tendered cartons:
60

Short cartons:
2

EDI delivered pieces:
59

Inspection damage:
5 cartons
```

---

# 2. Evidence Normalization

All extracted information is converted into a common evidence model.

Example:

```python
EvidenceFact(
    id="fact.pod_received_cartons",
    label="Cartons received",
    value="58",
    status="verified"
)
```

Each fact maintains:

- Value
- Source document
- Location
- Confidence
- Evidence anchor

This enables explainable claim decisions.

---

# 3. Reconciliation Engine

The reconciliation layer compares evidence sources.

Example:

```
Carrier EDI:
59 pieces delivered

Signed POD:
58 cartons received
```

The system identifies:

```
Finding:
COUNT_MISMATCH

Severity:
HIGH

Status:
OPEN
```

---

# 4. Contract Evaluation Engine

The contract engine applies deterministic rules.

Examples:

## Cargo Liability

Rule:

```
Maximum payable amount =
minimum(
    invoice value,
    contractual liability limit
)
```

Output:

```
Supported cargo value:
$102,000
```

---

## Delay Evaluation

Commercial damages such as:

- Lost promotion value
- Lost profits
- Consequential damages

are evaluated separately according to contract rules.

---

# 5. Historical Claim Comparison

The system compares the current claim against historical claims.

Ranking considers:

- Carrier similarity
- Service level similarity
- Claim amount similarity
- Issue type similarity
- Evidence availability

Example output:

```
HC-2024-0202
Similarity: 63.1%

HC-2025-0142
Similarity: 62.2%
```

---

# Technology Stack

## Backend

- Python
- FastAPI
- Dataclasses
- Pandas
- Boto3
- AWS S3
- AWS Textract integration

## Frontend

- HTML
- CSS
- Vanilla JavaScript

## Data Processing

- PDF extraction
- OCR-based extraction
- JSON parsing
- CSV processing

---

# Project Structure

```
claim_copilot/

│
├── api.py
│   └── FastAPI application
│
├── claim_processor.py
│   └── Main claim processing orchestration
│
├── claim_evidence.py
│   └── Evidence container model
│
├── evidence.py
│   └── Evidence fact models
│
├── reconciliation.py
│   └── Evidence conflict detection
│
├── contract_engine.py
│   └── Contract rule evaluation
│
├── historical_comparator.py
│   └── Historical claim ranking
│
├── tms_evidence_adapter.py
│   └── TMS/EDI evidence extraction
│
├── textract_evidence_adapter.py
│   └── Inspection document extraction
│
├── document_extractor.py
│   └── PDF extraction utilities
│
├── s3_service.py
│   └── AWS S3 integration
│
├── static/
│   |
│   ├── index.html
│   ├── app.js
│   └── styles.css
│
├── requirements.txt
│
└── README.md
```

---

# Running the Application

## 1. Clone Repository

```bash
git clone <repository-url>

cd claim_copilot
```

---

# 2. Create Virtual Environment

```bash
python3 -m venv .venv
```

Activate:

### macOS/Linux

```bash
source .venv/bin/activate
```

---

# 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

# 4. Configure AWS Credentials

The project uses AWS services for document processing.

Configure AWS CLI:

```bash
aws configure
```

or use:

```bash
export AWS_PROFILE=<profile-name>
```

---

# 5. Start FastAPI Server

Run:

```bash
uvicorn api:app --reload
```

Expected:

```
Uvicorn running on:

http://127.0.0.1:8000
```

---

# 6. Open Frontend

Navigate to:

```
http://127.0.0.1:8000
```

---

# API Endpoints

## Health Check

```
GET /health
```

Response:

```json
{
  "status": "ok",
  "service": "Freight Claim Copilot"
}
```

---

## Upload Claim Documents

```
POST /claims/{claim_id}/documents
```

Uploads claim supporting documents.

---

## Analyze Claim

```
POST /claims/{claim_id}/analyze
```

Runs the complete claim analysis pipeline.

Output includes:

- Evidence facts
- Reconciliation findings
- Contract position
- Historical comparables

---

## Frontend Claim Workspace

```
GET /api/claim
```

Returns frontend-compatible claim workspace data.

Includes:

- Claim overview
- Evidence
- Findings
- Contract position
- Similar claims

---

## Dynamic Claim Workspace

```
GET /api/claim/{claim_id}
```

Supports analysis of specific claims.

Example:

```
GET /api/claim/CLAIM-001
```

---

## Negotiation Draft Endpoint

```
POST /api/draft
```

Endpoint prepared for negotiation draft generation.

---

# Example Analysis Output

## Evidence

```
Cartons received:
58

Cartons tendered:
60

Damaged cartons:
5
```

---

## Reconciliation

```
Finding:

COUNT_MISMATCH

Carrier EDI:
59

POD:
58
```

---

## Contract Position

```
Cargo Liability:
$102,000

Inspection:
$420

Repack Labor:
$300
```

---

## Historical Comparables

Example:

```
HC-2024-0202
Similarity: 63.1%

HC-2025-0142
Similarity: 62.2%
```

---

# Design Principles

## Evidence First

Every decision should be traceable back to source evidence.

---

## Explainability

The system separates:

- Facts
- Rules
- Recommendations

The model does not directly override contractual logic.

---

## Human Approval

The system assists analysts.

Final claim decisions remain human-controlled.

---

# Future Enhancements

Planned improvements:

- Dynamic claim selection UI
- Automated negotiation draft generation
- LLM-based claim summaries
- Production AWS deployment
- Authentication and authorization
- Workflow management
- Human approval workflows

---

# License

This project is intended for demonstration and evaluation purposes.
