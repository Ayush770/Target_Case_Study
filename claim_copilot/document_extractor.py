from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None


def extract_pdf_text(file_path: str) -> str:
    if PdfReader is None:
        return ""

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