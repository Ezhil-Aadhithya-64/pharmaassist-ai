import os
from dotenv import load_dotenv

load_dotenv()

# PDF path: set PDF_PATH in .env or defaults to the file in this directory
PDF_PATH       = os.getenv("PDF_PATH", os.path.join(os.path.dirname(__file__), "Pharmacy E-Commerce FAQ.pdf"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
VECTOR_DB_PATH  = os.getenv("VECTOR_DB_PATH",  os.path.join(os.path.dirname(__file__), "vector_store", "chroma_db"))
HF_TOKEN        = os.getenv("HF_TOKEN", "")
CHUNK_SIZE      = int(os.getenv("CHUNK_SIZE", 1000))
CHUNK_OVERLAP   = int(os.getenv("CHUNK_OVERLAP", 200))
TOP_K           = int(os.getenv("TOP_K", 3))
