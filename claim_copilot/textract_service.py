import os
import boto3


AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")


class TextractService:
    def __init__(self):
        self.client = boto3.client(
            "textract",
            region_name=AWS_REGION,
        )

    def extract_text(self, file_path: str) -> str:
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