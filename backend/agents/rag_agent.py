"""
RAG agent: retrieves relevant chunks from the pharmacy FAQ PDF via ChromaDB.
Canonical location: backend/agents/rag_agent.py

The vector store and embedding model are loaded ONCE at process start via
get_rag_collection(), which is decorated with @st.cache_resource so Streamlit
never reloads it on page refresh.

For non-Streamlit contexts (main.py CLI), the same function falls back to a
module-level singleton so it still only loads once per process.
"""
import os

import backend.core.config as _cfg  # noqa: F401 — ensures .env is loaded

from backend.agents.pdf_loader import PDFLoader

# ── collection singleton (used outside Streamlit) ─────────────────────────────
_collection = None


def _build_collection():
    """Build and return the ChromaDB collection. Called once per process."""
    import chromadb
    from chromadb.utils import embedding_functions

    pdf_path = os.getenv("PDF_PATH", os.path.join(
        os.path.dirname(__file__), "..", "..", "rag", "Pharmacy E-Commerce FAQ.pdf"
    ))

    pages  = PDFLoader(pdf_path).extract_text()
    chunks = _chunk_text(pages)

    chroma_client = chromadb.Client()
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
    collection = chroma_client.get_or_create_collection(
        name="pharma_faq", embedding_function=ef
    )

    if collection.count() == 0:
        for i, chunk in enumerate(chunks):
            collection.add(
                documents=[chunk],
                metadatas=[{"source": f"chunk_{i}"}],
                ids=[str(i)],
            )
        print(f"[rag_agent] Vector store built: {len(chunks)} chunks")
    else:
        print(f"[rag_agent] Vector store reused: {collection.count()} chunks already loaded")

    return collection


def _chunk_text(pages: list, chunk_size: int = 1000, overlap: int = 200) -> list:
    chunks = []
    for page in pages:
        start = 0
        while start < len(page):
            chunks.append(page[start: start + chunk_size])
            start += chunk_size - overlap
    return chunks


def get_rag_collection():
    """
    Returns the ChromaDB collection.
    When called from Streamlit, uses @st.cache_resource so it loads once
    and survives page refreshes. Falls back to module-level singleton otherwise.
    """
    global _collection
    try:
        import streamlit as st

        @st.cache_resource(show_spinner="Loading knowledge base...")
        def _cached_collection():
            return _build_collection()

        return _cached_collection()

    except Exception:
        # Non-Streamlit context (CLI / tests)
        if _collection is None:
            _collection = _build_collection()
        return _collection


# ── Public API ────────────────────────────────────────────────────────────────

def retrieve_chunks_only(query: str, top_k: int = 3) -> list:
    """Returns raw retrieved chunks. Used by rag_node."""
    try:
        collection = get_rag_collection()
        results = collection.query(query_texts=[query], n_results=top_k)
        return results["documents"][0]
    except Exception as e:
        print(f"[rag_agent] Retrieval error: {e}")
        return []


def retrieve_and_answer(query: str, top_k: int = 3) -> str:
    """Full RAG pipeline — retrieve + answer. Kept for compatibility."""
    from groq import Groq
    chunks  = retrieve_chunks_only(query, top_k)
    context = "\n\n".join(chunks)

    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    if context:
        system      = (
            "You are a pharmacy ecommerce assistant. "
            "Answer the user's question strictly based on the provided policy context. "
            "Do not add information not present in the context."
        )
        user_prompt = f"Policy Context:\n{context}\n\nUser Question: {query}\n\nAnswer:"
    else:
        system      = "You are a helpful pharmacy ecommerce assistant."
        user_prompt = query

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[rag_agent] LLM error: {e}")
        return "I couldn't retrieve the policy information right now. Please try again."
