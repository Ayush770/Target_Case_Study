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


app = FastAPI(
    title="Freight Claim Copilot",
    version="1.0"
)


# -----------------------------
# Services
# -----------------------------

s3_service = S3Service()


# -----------------------------
# Static Frontend
# -----------------------------

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


# -----------------------------
# Health Check
# -----------------------------

@app.get("/health")
def health():

    return {
        "status": "ok",
        "service": "Freight Claim Copilot"
    }


# -----------------------------
# Serialization Layer
# -----------------------------

def serialize_response(obj):

    """
    Converts backend dataclasses
    into JSON serializable objects.
    """

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



# -----------------------------
# Document Upload API
# -----------------------------

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

            "status": "uploaded",

        }


    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )



# -----------------------------
# Claim Analysis API
# Backend API
# -----------------------------

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



# -----------------------------
# Frontend Compatibility Adapter
# Used by existing app.js
# -----------------------------

@app.get(
    "/api/claim"
)
def get_frontend_claim():

    try:

        result = process_claim(
            "CLAIM-001"
        )


        data = serialize_response(
            result
        )


        contract_positions = (
            data.get(
                "contract_position",
                []
            )
        )


        return {

            # -----------------
            # Overview section
            # -----------------

            "claim": {

                "id": data.get(
                    "claim_id",
                    "CLAIM-001"
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


            # -----------------
            # Evidence section
            # -----------------

            "facts":
                data.get(
                    "evidence",
                    {}
                ).get(
                    "facts",
                    []
                ),


            # -----------------
            # Findings section
            # -----------------

            "findings": [

                data["reconciliation"]

            ] if data.get(
                "reconciliation"
            ) else [],



            # -----------------
            # Contract position
            # -----------------

            "position": {

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
                    else {}

            },


            # -----------------
            # Historical claims
            # -----------------

            "comparators":
                data.get(
                    "historical_comparables",
                    []
                ),


            # -----------------
            # Timeline
            # -----------------

            "timeline": []

        }


    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )