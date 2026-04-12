"""
summary_agent — Post-interaction CRM summary generator.
Canonical location: backend/agents/summary_agent.py

Auto-triggered from memory_updater on escalation.
Also callable directly (e.g. from Streamlit button or session end).
"""
import os

import backend.core.config as _cfg  # noqa: F401 — ensures .env is loaded
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
SUMMARY_MODEL = "llama-3.1-8b-instant"


def generate_summary(state: dict) -> dict:
    """
    Generate a structured CRM summary from AgentState.
    Returns updated state dict with 'summary' key set.
    """
    memory = state.get("memory", [])
    if not memory:
        state["summary"] = "No conversation to summarise."
        return state

    transcript = "\n".join(
        f"Customer: {t['user']}\nAgent: {t['agent']}" for t in memory
    )

    resolution = "Escalated" if state.get("escalation_package") else (
        state.get("resolution_status", "").capitalize() or "Resolved"
    )

    prompt = (
        "You are a CRM system. Generate a concise post-interaction summary record "
        "based on the conversation transcript below.\n\n"
        "Include:\n"
        "- Issue raised by customer\n"
        "- Actions taken by agent\n"
        f"- Resolution status: {resolution}\n"
        "- Any follow-up required\n\n"
        f"Transcript:\n{transcript}\n\n"
        "CRM Summary:"
    )

    try:
        response = client.chat.completions.create(
            model=SUMMARY_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        llm_summary = response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[summary_agent] LLM error: {e}")
        llm_summary = transcript

    crm_record = (
        f"=== POST-INTERACTION CRM SUMMARY ===\n"
        f"Session ID      : {state.get('session_id', 'N/A')}\n"
        f"Total Turns     : {len(memory)}\n"
        f"Last Intent     : {state.get('intent', 'N/A')}\n"
        f"Action Taken    : {state.get('action_taken', 'N/A')}\n"
        f"Entities        : {state.get('entities', {})}\n"
        f"Resolution      : {resolution}\n"
        f"\n--- AI-Generated Summary ---\n{llm_summary}\n"
        f"\n--- Full Transcript ---\n{transcript}"
    )

    state["summary"] = crm_record
    print(f"[summary_agent] CRM record generated ({len(memory)} turns, resolution={resolution})")
    return state


def log_session_to_db(state: dict):
    """
    Persist the interaction to the interactions table.
    Called at session end or escalation.
    """
    import json
    from backend.tools.db_tools import log_interaction

    memory = state.get("memory", [])
    if not memory:
        return

    transcript = "\n".join(
        f"Customer: {t['user']}\nAgent: {t['agent']}" for t in memory
    )
    entities_str = json.dumps(state.get("entities", {}))
    resolution   = "escalated" if state.get("escalation_package") else (
        state.get("resolution_status", "resolved") or "resolved"
    )

    try:
        log_interaction.invoke({
            "session_id":        state.get("session_id", "unknown"),
            "intent":            state.get("intent", "unknown"),
            "entities":          entities_str,
            "action_taken":      state.get("action_taken", ""),
            "resolution_status": resolution,
            "transcript":        transcript,
        })
        print(f"[summary_agent] interaction logged to DB — session={state.get('session_id')}")
    except Exception as e:
        print(f"[summary_agent] DB log error: {e}")
