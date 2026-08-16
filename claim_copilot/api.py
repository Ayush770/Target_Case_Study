from fastapi import (
    FastAPI,
    File,
    UploadFile,
    HTTPException,
)

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from s3_service import S3Service
from claim_processor import process_claim

from dataclasses import (
    is_dataclass,
    asdict,
)

import tempfile
import os


# =====================================================
# Application
# =====================================================

app = FastAPI(
    title="Freight Claim Copilot",
    version="1.0"
)



# =====================================================
# Services
# =====================================================

s3_service = S3Service()



# =====================================================
# Static Frontend
# =====================================================

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static",
)



@app.get("/")
def home():

    return FileResponse(
        "static/index.html"
    )



# =====================================================
# Health
# =====================================================

@app.get("/health")
def health():

    return {
        "status": "ok",
        "service": "Freight Claim Copilot"
    }



# =====================================================
# Serialization
# =====================================================

def serialize_response(obj):

    if obj is None:

        return None


    if is_dataclass(obj):

        return {
            key: serialize_response(value)
            for key, value in asdict(obj).items()
        }


    if isinstance(obj, list):

        return [
            serialize_response(item)
            for item in obj
        ]


    if isinstance(obj, dict):

        return {
            key: serialize_response(value)
            for key, value in obj.items()
        }


    return obj



# =====================================================
# Document Upload
# =====================================================

@app.post(
    "/claims/{claim_id}/documents"
)
async def upload_document(
    claim_id: str,
    file: UploadFile = File(...),
):

    try:

        suffix = os.path.splitext(
            file.filename or ""
        )[1]


        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix
        ) as temp_file:


            temp_file.write(
                await file.read()
            )


            temp_path = temp_file.name



        try:

            s3_key = s3_service.upload_file(
                file_path=temp_path,
                claim_id=claim_id,
                filename=file.filename or "uploaded_file",
            )


        finally:

            os.unlink(
                temp_path
            )


        return {

            "claim_id": claim_id,

            "filename": file.filename,

            "s3_key": s3_key,

            "status": "uploaded"

        }


    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )



# =====================================================
# Claim Analysis API
# =====================================================

@app.post(
    "/claims/{claim_id}/analyze"
)
def analyze_claim(
    claim_id: str,
):

    try:

        result = process_claim(
            claim_id
        )


        return serialize_response(
            result
        )


    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )



# =====================================================
# Frontend Adapter
# =====================================================

def build_frontend_claim_response(
    claim_id: str
):

    result = process_claim(
        claim_id
    )


    data = serialize_response(
        result
    )


    contract_positions = data.get(
        "contract_position",
        []
    )


    return {

        # -----------------------------
        # Overview
        # -----------------------------

        "claim": {

            "id":
                data.get(
                    "claim_id",
                    claim_id
                ),

            "carrier":
                "BlueLine Freight Systems",

            "owner":
                "Maya Chen",

            "status":
                "NEGOTIATION",

            "demand":
                "$29,920.00",

            "offer":
                "$7,225.00",

            "direct_cargo":
                "$102,000.00",

            "gap_to_direct_cargo":
                "$0.00"

        },



        # -----------------------------
        # Evidence
        # -----------------------------

        "facts":

            data.get(
                "evidence",
                {}
            ).get(
                "facts",
                []
            ),



        # -----------------------------
        # Findings
        # -----------------------------

        "findings":

            [
                data["reconciliation"]
            ]

            if data.get(
                "reconciliation"
            )

            else [],



        # -----------------------------
        # Contract Position
        # -----------------------------

        "position": {


            "direct_cargo": {

                "amount":
                    "$102,000.00",

                "status":
                    "supported"

            },


            "cargo_cap":

                contract_positions[0]

                if len(contract_positions) > 0

                else {},



            "inspection":

                contract_positions[1]

                if len(contract_positions) > 1

                else {},



            "repack":

                contract_positions[2]

                if len(contract_positions) > 2

                else {},



            "delay_markdown":

                contract_positions[3]

                if len(contract_positions) > 3

                else {},



            "freight_refund": {

                "amount":
                    "$0.00",

                "status":
                    "pending"

            }

        },



        # -----------------------------
        # Historical Claims
        # -----------------------------

        "comparators":

            data.get(
                "historical_comparables",
                []
            ),



        # -----------------------------
        # Timeline
        # -----------------------------

        "timeline": []

    }



# =====================================================
# Frontend APIs
# =====================================================

@app.get(
    "/api/claim"
)
def get_default_claim():

    try:

        return build_frontend_claim_response(
            "CLAIM-001"
        )


    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )



@app.get(
    "/api/claim/{claim_id}"
)
def get_claim_by_id(
    claim_id: str
):

    try:

        return build_frontend_claim_response(
            claim_id
        )


    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )



# =====================================================
# Negotiation Draft
# =====================================================

@app.post(
    "/api/draft"
)
def generate_draft():

    return {

        "subject":
            "Claim negotiation draft",


        "body":
            (
                "Draft generation endpoint is connected. "
                "LLM-based negotiation drafting will be integrated here."
            ),


        "validation": {

            "citation_coverage":
                "pending",

            "numeric_consistency":
                "pending",

            "approval_required":
                True

        },


        "citations": []

    }