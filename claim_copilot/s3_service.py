import os
import boto3

BUCKET_NAME = os.getenv(
    "S3_BUCKET",
    "candidate-pack-claims-dev-133715233089",
)

AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")


class S3Service:
    def __init__(self):
        try:
            self.client = boto3.client(
                "s3",
                region_name=AWS_REGION,
            )
        except Exception:
            self.client = None

    def upload_file(
        self,
        file_path: str,
        claim_id: str,
        filename: str,
    ) -> str:
        if self.client is None:
            raise RuntimeError(
                "AWS S3 credentials are not configured for this environment. "
                "Set AWS credentials or skip upload calls until they are available."
            )

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
        if self.client is None:
            raise RuntimeError(
                "AWS S3 credentials are not configured for this environment. "
                "Set AWS credentials or skip download calls until they are available."
            )

        self.client.download_file(
            BUCKET_NAME,
            key,
            local_path,
        )