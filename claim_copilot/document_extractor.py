from pathlib import Path

from pypdf import PdfReader


def extract_pdf_text(file_path: str) -> str:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Document not found: {path}")

    reader = PdfReader(path)

    pages = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""

        pages.append(
            f"[PAGE {page_number}]\n{text.strip()}"
        )

    return "\n\n".join(pages)