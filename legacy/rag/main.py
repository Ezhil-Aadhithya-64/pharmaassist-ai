# from fastapi import FastAPI, Request
# from config import PDF_PATH
# from pdf_loader import PDFLoader
# from rag_chroma import chunk_text, build_vector_store, retrieve_chunks
# from llm_client import llm

# # Initialize PDF -> Chroma
# pdf_loader = PDFLoader(PDF_PATH)
# pages = pdf_loader.extract_text()
# chunks = chunk_text(pages)
# build_vector_store(chunks)

# app = FastAPI(title="Pharma PDF QA Bot")

# @app.post("/query")
# async def query_pdf(request: Request):
#     data = await request.json()
#     query = data.get("query")
#     if not query:
#         return {"status": "error", "message": "Query missing"}

#     top_chunks = retrieve_chunks(query)
#     context_text = "\n".join(top_chunks)
#     prompt = f"Answer the user query strictly based on the following text:\n{context_text}\n\nQuery: {query}\nAnswer:"

#     answer = llm(prompt)
#     return {
#         "status": "success",
#         "data": {
#             "answer": answer,
#             "eligibility": True,
#             "reason": "Answer retrieved from PDF content",
#             "source": ", ".join([f"Page {i+1}" for i, _ in enumerate(top_chunks)])
#         }
#     }

from fastapi import FastAPI, Request
from pdf_loader import PDFLoader
from rag_chroma import chunk_text, build_vector_store, retrieve_chunks
from llm_client import llm
from config import PDF_PATH

# 1️⃣ Load PDF and prepare chunks
pdf_loader = PDFLoader(PDF_PATH)
pages = pdf_loader.extract_text()
chunks = chunk_text(pages)
build_vector_store(chunks)

# 2️⃣ FastAPI setup
app = FastAPI(title="Pharma PDF QA Bot")

@app.post("/query")
async def query_pdf(request: Request):
    data = await request.json()
    query = data.get("query")
    if not query:
        return {"status": "error", "message": "Query missing"}

    top_chunks = retrieve_chunks(query)
    context_text = "\n".join(top_chunks)

    prompt = f"Answer the user query strictly based on the following text:\n{context_text}\n\nQuery: {query}\nAnswer:"

    answer = llm(prompt)

    return {
        "status": "success",
        "data": {
            "answer": answer,
            "eligibility": True,
            "reason": "Answer retrieved from PDF content",
            "source": ", ".join([f"Page {i+1}" for i, _ in enumerate(top_chunks)])
        }
    }