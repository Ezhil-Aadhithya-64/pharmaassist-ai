"""
Entry point — runs the pipeline in a session-based conversation loop.
Run from project root: python -m backend.main
"""
import uuid
from backend.core.graph import build_graph
from backend.agents.summary_agent import generate_summary, log_session_to_db

pipeline = build_graph()


def run_session():
    session_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": session_id}}

    print(f"\n=== PharmaAssist AI started | Session: {session_id} ===")
    print("Type 'exit' to quit, 'summary' to see conversation summary.\n")

    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() == "exit":
            state = pipeline.get_state(config).values
            state = generate_summary(dict(state))
            log_session_to_db(state)
            print("\n=== Session ended ===")
            print(f"Summary:\n{state.get('summary', '')}")
            break
        if user_input.lower() == "summary":
            state = pipeline.get_state(config).values
            state = generate_summary(dict(state))
            print(f"\n--- Summary ---\n{state.get('summary', 'No turns yet.')}\n")
            continue

        result = pipeline.invoke(
            {"user_input": user_input, "session_id": session_id},
            config=config,
        )
        print(f"Agent: {result['agent_response']}\n")


if __name__ == "__main__":
    run_session()
