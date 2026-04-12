# Legacy RAG Service

This was the original standalone FastAPI RAG microservice.

It has been **superseded** by `backend/agents/rag_agent.py`, which integrates
ChromaDB retrieval directly into the LangGraph pipeline.

`pdf_loader.py` was copied to `backend/agents/pdf_loader.py` and is the
canonical version going forward.

Do NOT import from this directory in new code.
