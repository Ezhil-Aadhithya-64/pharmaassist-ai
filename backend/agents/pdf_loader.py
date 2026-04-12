"""
PDF text extraction utility.
Canonical location: backend/agents/pdf_loader.py
(Moved from rag/pdf_loader.py — no longer requires sys.path hacks)
"""
import fitz


class PDFLoader:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path

    def extract_text(self) -> list:
        pages_text = []
        try:
            doc = fitz.open(self.pdf_path)
        except Exception as e:
            print("Error opening PDF:", e)
            return []

        for page_number in range(doc.page_count):
            page = doc[page_number]
            text = page.get_text("text").strip()
            if text:
                pages_text.append(text)
        doc.close()
        return pages_text
