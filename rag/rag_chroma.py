# # from sentence_transformers import SentenceTransformer
# import chromadb
# from chromadb.utils import embedding_functions
# from config import PDF_PATH, VECTOR_DB_PATH, CHUNK_SIZE, CHUNK_OVERLAP, TOP_K
# # from pdf_loader import PDFLoader

# # 1️⃣ Load PDF & split into chunks
# def chunk_text(pages, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
#     chunks = []
#     for page in pages:
#         start = 0
#         while start < len(page):
#             end = min(start + chunk_size, len(page))
#             chunks.append(page[start:end])
#             start += chunk_size - overlap
#     return chunks

# # 2️⃣ Initialize Chroma DB & embeddings
# client = chromadb.Client()
# embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
#     model_name="sentence-transformers/all-MiniLM-L6-v2"
# )
# collection = client.get_or_create_collection(name="pdf_collection", embedding_function=embedding_function)

# def build_vector_store(chunks):
#     for i, chunk in enumerate(chunks):
#         collection.add(
#             documents=[chunk],
#             metadatas=[{"source": f"Page {i+1}"}],
#             ids=[str(i)]
#         )

# # 3️⃣ Retrieve top-k chunks
# def retrieve_chunks(query, k=TOP_K):
#     results = collection.query(
#         query_texts=[query],
#         n_results=k
#     )
#     return [doc for doc in results['documents'][0]]

import chromadb
from chromadb.utils import embedding_functions
from config import CHUNK_SIZE, CHUNK_OVERLAP, TOP_K, EMBEDDING_MODEL

# 1️⃣ Split text into chunks
def chunk_text(pages, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    chunks = []
    for page in pages:
        start = 0
        while start < len(page):
            end = min(start + chunk_size, len(page))
            chunks.append(page[start:end])
            start += chunk_size - overlap
    return chunks

# 2️⃣ Initialize Chroma DB & embeddings
client = chromadb.Client()
embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name=EMBEDDING_MODEL
)
collection = client.get_or_create_collection(
    name="pdf_collection",
    embedding_function=embedding_function
)

def build_vector_store(chunks):
    for i, chunk in enumerate(chunks):
        collection.add(
            documents=[chunk],
            metadatas=[{"source": f"Page {i+1}"}],
            ids=[str(i)]
        )

# 3️⃣ Retrieve top-k chunks from vector DB
def retrieve_chunks(query, k=TOP_K):
    results = collection.query(
        query_texts=[query],
        n_results=k
    )
    return [doc for doc in results['documents'][0]]