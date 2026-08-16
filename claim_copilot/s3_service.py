import os
import boto3
from pathlib import Path

BUCKET_NAME = os.getenv(
    "S3_BUCKET",
    "candidate-pack-claims-dev-133715233089",
)

AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")


class S3Service:
    def __init__(self):
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