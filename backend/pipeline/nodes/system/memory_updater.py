"""
memory_updater node — appends turn to memory, auto-triggers CRM summary + DB log.
Canonical location: backend/pipeline/nodes/system/memory_updater.py
"""
from backend.state.schema import AgentState


def memory_updater(state: AgentState) -> AgentState:
    """
    Appends current turn to memory.
    Auto-triggers CRM summary + DB log on escalation.
    Logs all resolved sessions to DB automatically.
    """
    new_entry = {"user": state["user_input"], "agent": state["agent_response"]}
    turns_after = len(state.get("memory", [])) + 1
    print(f"[memory_updater] {turns_after} turns")

    updates = {"memory": [new_entry]}

    is_escalated = state.get("escalation_package") or state.get("resolution_status") == "escalated"
    is_resolved  = state.get("resolution_status") == "resolved"

    if is_escalated:
        print("[memory_updater] escalation detected — auto-generating CRM summary")
        try:
            from backend.agents.summary_agent import generate_summary, log_session_to_db
            snap = dict(state)
            snap["memory"] = list(state.get("memory", [])) + [new_entry]
            snap = generate_summary(snap)
            updates["summary"] = snap.get("summary", "")
            log_session_to_db(snap)
            updates["session_logged"] = True
        except Exception as e:
            print(f"[memory_updater] summary/log error: {e}")

    elif is_resolved and state.get("action_taken"):
        print(f"[memory_updater] resolved action '{state.get('action_taken')}' — logging to DB")
        try:
            from backend.agents.summary_agent import log_session_to_db
            snap = dict(state)
            snap["memory"] = list(state.get("memory", [])) + [new_entry]
            log_session_to_db(snap)
            updates["session_logged"] = True
        except Exception as e:
            print(f"[memory_updater] DB log error: {e}")

    return updates
