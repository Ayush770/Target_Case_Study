import tempfile
from pathlib import Path

from s3_service import S3Service
from document_extractor import extract_pdf_text


if __name__ == "__main__":
    service = S3Service()

    s3_key = "claims/CLAIM-001/documents/08_proof_of_delivery.pdf"

    with tempfile.TemporaryDirectory() as temp_dir:
        local_path = Path(temp_dir) / "08_proof_of_delivery.pdf"

        service.download_file(
            key=s3_key,
            local_path=str(local_path),
        )

        text = extract_pdf_text(str(local_path))

        print(text)
