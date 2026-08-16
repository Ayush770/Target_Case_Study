from pathlib import Path

from textract_service import TextractService


PDF_PATH = Path("../09_damage_inspection_report_scanned.pdf")


service = TextractService()

text = service.extract_text(
    str(PDF_PATH)
)

print(text)

assert text.strip(), "Textract returned no text."

print("\nTextract test passed.")