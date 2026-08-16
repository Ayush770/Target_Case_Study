import os
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from pathlib import Path

BUCKET_NAME = os.getenv(
    "S3_BUCKET",
    "candidate-pack-claims-dev-133715233089",
)

AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")


class S3Service:
    def __init__(self):
        # Build client — raises immediately if no valid credentials exist.
        # Callers should catch BotoCoreError / ClientError.
        self.client = boto3.client(
            "s3",
            region_name=AWS_REGION,
        )

    def upload_file(
        self,
        file_path: str,
        claim_id: str,
        filename: str,
    ) -> str:
        key = f"claims/{claim_id}/documents/{filename}"

        self.client.upload_file(
            file_path,
            BUCKET_NAME,
            key,
        )

        return key

    def download_file(
        self,
        key: str,
        local_path: str,
    ) -> None:
        self.client.download_file(
            BUCKET_NAME,
            key,
            local_path,
        )

    def list_claim_documents(
        self,
        claim_id: str,
    ) -> list[str]:
        """
        Return the S3 keys of all documents uploaded for a claim.
        Keys follow the pattern: claims/{claim_id}/documents/{filename}
        """
        prefix = f"claims/{claim_id}/documents/"
        response = self.client.list_objects_v2(
            Bucket=BUCKET_NAME,
            Prefix=prefix,
        )
        return [
            obj["Key"]
            for obj in response.get("Contents", [])
        ]