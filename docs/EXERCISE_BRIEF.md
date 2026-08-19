# Senior AI Engineer Exercise - Freight Claim Copilot

## Background
A company ships a high volume of goods through third-party freight carriers.

Shipments occasionally:
- Arrive damaged
- Are lost
- Arrive with missing items
- Arrive sufficiently late that the goods lose most or all of their commercial value

When this happens, the company may file a freight claim against the carrier to recover the loss.

Most claims are negotiated over email. An internal claims specialist and a carrier representative may go back and forth regarding:
- What was shipped
- What actually arrived
- Shipment value
- Evidence of damage or loss
- Delivery timestamps
- Supporting invoices
- Photos and inspection reports
- Applicable carrier agreements
- What amount the carrier is willing to reimburse

The information required to resolve a claim is spread across multiple systems:
- Email
- Shipment/Transportation Management System
- ERP/order data
- PDFs and scanned documents
- Carrier service agreements
- Historical claims
- Images and supporting evidence

Some carrier relationships have explicit contractual liability terms. For other claims, the outcome is influenced by historical settlements, negotiation, commercial relationships, and judgment.

A claims specialist may currently spend considerable time:
- Understanding the history of a claim
- Locating supporting evidence
- Determining whether required information is missing
- Identifying relevant contractual terms
- Comparing the case against historical claims
- Deciding what position to take
- Drafting correspondence
- Negotiating until the claim is resolved

The business wants to explore how AI and Generative AI could reduce this effort and improve claim outcomes.

## Scenario
Northstar Retail Equipment ships a high volume of goods through third-party freight carriers. Claim **FCL-2026-0147** is a synthetic case involving missing cartons, damaged goods, and a late delivery. The information required to understand the claim is intentionally spread across emails, structured records, PDFs, a scanned document, a carrier agreement, images, and historical claim data.

## Your task
Build a working prototype for **one small AI/GenAI flow of your choice**. The point is not to automate the whole claim lifecycle; pick a narrow, useful flow and make it work end to end.

Possible flows include:
1. Claim intake + structured extraction + evidence-gap detection.
2. Claim history/timeline summarization with source traceability.
3. Carrier contract term retrieval and liability-position support.
4. Similar historical claim retrieval and settlement comparison.
5. Drafting a fact-grounded negotiation response from the case file.
6. A compact claim copilot that combines a few of the above while staying small enough to explain and test.

## What we care about
- Correct grounding in the provided evidence.
- Handling inconsistent or missing information explicitly.
- Clear separation of extracted facts, inferred conclusions, and recommendations.
- Traceability/citations back to the source file or record.
- Sensible use of deterministic logic vs. LLM reasoning.
- A design that could be extended to enterprise systems without assuming perfect data.
- Basic evaluation/testing approach, especially for hallucination and document extraction failure modes.

## Constraints
- All companies, people, values, and records are fictional and created for this exercise.
- You may use any programming language, model, framework, vector store, or local parsing approach.
- Do not assume every source is correct. When sources disagree, surface the disagreement.
- Do not invent missing facts.

## Folder guide
- `01_case_overview.pdf` - concise claim context and initial demand.
- `02_claim_email_thread.eml` - negotiation history.
- `03_claim_snapshot.json` - internal claim-system fields.
- `04_tms_shipment.json` - transportation-management record and EDI events.
- `05_erp_order_invoice.csv` - ERP/order-line data.
- `06_commercial_invoice.pdf` - proof of product value.
- `07_bill_of_lading.pdf` - shipment tender details.
- `08_proof_of_delivery.pdf` - delivery exceptions and signature.
- `09_damage_inspection_report_scanned.pdf` - image-only scanned inspection report.
- `10_carrier_service_agreement.pdf` - governing carrier terms.
- `11_historical_claims.xlsx` / `12_historical_claims.csv` - synthetic prior claims.
- `13_damage_photo_1.png` / `14_damage_photo_2.png` - synthetic evidence images.
- `15_data_dictionary.md` - field notes and record semantics.

The dataset contains a small number of deliberate ambiguities/discrepancies. A strong solution should detect rather than hide them.
