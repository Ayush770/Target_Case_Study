# Data dictionary and source notes

## Identifiers
- `claim_id`: internal claim identifier. Primary case is `FCL-2026-0147`.
- `pro_number`: carrier tracking/freight bill identifier. Primary PRO is `BLF-77209115`.
- `bol_number`: bill of lading identifier. Primary BOL is `BOL-884219`.
- `sales_order` / `invoice`: ERP references.

## Important semantics
- TMS `pieces_tendered` and EDI `pieces` are carrier/TMS operational counts. The final EDI event is not a consignee-signed receiving record.
- The signed POD is the consignee's documented receiving exception at delivery.
- `service.guaranteed=false` means no guaranteed-service accessorial is recorded in TMS.
- `claim_amount_usd` in the claim snapshot is the shipper's demand, not an adjudicated recoverable amount.
- Historical `settlement_pct` is settlement divided by claimed amount; it should not be treated as a contractual entitlement.

## Evidence caveats deliberately present in the case
- The TMS final EDI event reports 59 pieces delivered; the signed POD reports 58 cartons received.
- The claim folder contains two warehouse photos even though five damaged cartons are identified by POD/inspection.
- The email asks for a vendor packaging specification; it is not included in the case pack.
- The inspection report is an image-only scanned PDF rather than a text-native PDF.
- The contract distinguishes Standard LTL from a purchased Guaranteed Appointment service.

These caveats are not errors in the exercise. They are meant to test evidence reconciliation and uncertainty handling.
