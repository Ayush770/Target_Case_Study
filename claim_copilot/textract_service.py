import os
import boto3


AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")


class TextractService:
    def __init__(self):
        try:
            self.client = boto3.client(
                "textract",
                region_name=AWS_REGION,
            )
        except Exception:
            self.client = None

    def extract_text(self, file_path: str) -> str:
        if self.client is None:
            raise RuntimeError(
                "AWS Textract credentials are not configured for this environment. "
                "Set AWS credentials or ensure the AWS profile is available."
            )

        with open(file_path, "rb") as file:
            document_bytes = file.read()

        response = self.client.detect_document_text(
            Document={
                "Bytes": document_bytes,
            }
        )

        lines = [
            block["Text"]
            for block in response["Blocks"]
            if block["BlockType"] == "LINE"
        ]

        return "\n".join(lines)