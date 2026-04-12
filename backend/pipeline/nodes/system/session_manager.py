"""
session_manager node — resets per-turn transient fields at the start of each turn.
Canonical location: backend/pipeline/nodes/system/session_manager.py
"""
from backend.state.schema import AgentState


def session_manager(state: AgentState) -> AgentState:
    turns = len(state.get("memory", []))
    print(f"[session_manager] Session: {state['session_id']} | turns so far: {turns}")
    return {
        "rag_context":       "",
        "tool_result":       {},
        "agent_response":    "",
        "action_taken":      "",
        "resolution_status": "",
        "tool_calls":        [],
    }
