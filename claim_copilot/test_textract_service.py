"""Unit tests for TextractService.

AWS calls are mocked so these run fully offline without credentials.
"""
from unittest.mock import MagicMock, patch
import pytest

from textract_service import TextractService


MOCK_RESPONSE = {
    "Blocks": [
        {"BlockType": "LINE", "Text": "Five cartons showed crush damage"},
        {"BlockType": "LINE", "Text": "14 unsellable units"},
        {"BlockType": "WORD", "Text": "ignored"},          # non-LINE block
        {"BlockType": "LINE", "Text": "Inspection fee: $420.00"},
    ]
}


@patch("textract_service.boto3.client")
def test_extract_text_joins_lines(mock_boto_client, tmp_path):
    mock_client = MagicMock()
    mock_client.detect_document_text.return_value = MOCK_RESPONSE
    mock_boto_client.return_value = mock_client

    # Write a dummy file so open() succeeds
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-dummy")

    svc = TextractService()
    result = svc.extract_text(str(pdf))

    assert "Five cartons showed crush damage" in result
    assert "14 unsellable units" in result
    assert "Inspection fee: $420.00" in result
    # WORD blocks must be excluded
    assert "ignored" not in result


@patch("textract_service.boto3.client")
def test_extract_text_empty_response(mock_boto_client, tmp_path):
    mock_client = MagicMock()
    mock_client.detect_document_text.return_value = {"Blocks": []}
    mock_boto_client.return_value = mock_client

    pdf = tmp_path / "empty.pdf"
    pdf.write_bytes(b"%PDF-dummy")

    svc = TextractService()
    assert svc.extract_text(str(pdf)) == ""
