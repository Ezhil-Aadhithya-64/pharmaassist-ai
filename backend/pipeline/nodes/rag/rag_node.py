"""
rag_node — retrieves policy chunks from ChromaDB and stores them in state.
Canonical location: backend/pipeline/nodes/rag/rag_node.py
"""
from backend.state.schema import AgentState


def rag_node(state: AgentState) -> AgentState:
    from backend.agents.rag_agent import retrieve_chunks_only  # collection already cached

    query = state.get("user_input", "")
    print(f"[rag_node] retrieving chunks for: {query}")

    try:
        chunks  = retrieve_chunks_only(query, top_k=3)
        context = "\n\n".join(chunks) if chunks else ""
    except Exception as e:
        print(f"[rag_node] retrieval error: {e}")
        chunks  = []
        context = ""

    state["rag_context"] = context
    state["tool_result"] = {}
    print(f"[rag_node] {len(chunks)} chunks retrieved")
    return state
