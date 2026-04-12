# import fitz

# class PDFLoader:
#     def __init__(self, pdf_path):
#         self.pdf_path = pdf_path

#     def extract_text(self):
#         pages_text = []
#         try:
#             doc = fitz.open(self.pdf_path)
#         except Exception as e:
#             print("Error opening PDF:", e)
#             return []

#         for page_number in range(doc.page_count):
#             page = doc[page_number]
#             text = page.get_text("text").strip()
#             if text:
#                 pages_text.append(text)
#         doc.close()
#         return pages_text

import fitz

class PDFLoader:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path

    def extract_text(self):
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