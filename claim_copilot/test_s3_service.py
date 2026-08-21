import os
from s3_service import S3Service


if __name__ == "__main__":
    service = S3Service()

    file_path = "../01_case_overview.pdf"
    claim_id = "TEST-001"
    filename = "01_case_overview.pdf"

    key = service.upload_file(
        file_path=file_path,
        claim_id=claim_id,
        filename=filename,
    )

    print(f"Uploaded successfully: s3://{service.client.meta.region_name}/{key}")
