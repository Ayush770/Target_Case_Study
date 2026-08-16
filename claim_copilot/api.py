from fastapi import FastAPI, File, UploadFile, HTTPException
from s3_service import S3Service
import tempfile
import os

app = FastAPI(title="Freight Claim Copilot")

s3_service = S3Service()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/claims/{claim_id}/documents")
async def upload_document(
    claim_id: str,
    file: UploadFile = File(...),
):
    try:
        suffix = os.path.splitext(file.filename or "")[1]

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
            temp.write(await file.read())
            temp_path = temp.name

        try:
            s3_key = s3_service.upload_file(
                file_path=temp_path,
                claim_id=claim_id,
                filename=file.filename or "uploaded_file",
            )
        finally:
            os.unlink(temp_path)

        return {
            "claim_id": claim_id,
            "filename": file.filename,
            "s3_key": s3_key,
            "status": "uploaded",
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )