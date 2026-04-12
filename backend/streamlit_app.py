"""
PharmaAssist AI — Customer chat + Agent Assist panel + Supervisor Dashboard.
Run from project root: streamlit run backend/streamlit_app.py
"""
import tempfile
import uuid
import os

from backend.core.graph import build_graph
from backend.services.stt_service import transcribe_audio
from backend.agents.summary_agent import generate_summary, log_session_to_db

import streamlit as st

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False

st.set_page_config(
    page_title="PharmaAssist AI",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── User store (in real system this would be a DB table) ─────────────────────
# Passwords are hashed for security
import hashlib

def hash_password(password: str) -> str:
    """Simple password hashing for demo purposes."""
    return hashlib.sha256(password.encode()).hexdigest()

USERS = {
    "admin":  {"password": hash_password("admin123"),  "role": "admin",    "customer_id": None},
    "AH0001": {"password": hash_password("pass1234"),  "role": "customer", "customer_id": "AH0001"},
    "AH0002": {"password": hash_password("pass1234"),  "role": "customer", "customer_id": "AH0002"},
    "AH0003": {"password": hash_password("pass1234"),  "role": "customer", "customer_id": "AH0003"},
}

# Demo credentials for documentation
DEMO_CREDENTIALS = {
    "admin": "admin123",
    "AH0001": "pass1234",
}

# ── Login gate ────────────────────────────────────────────────────────────────
if "logged_in" not in st.session_state:
    st.session_state.logged_in   = False
    st.session_state.username    = ""
    st.session_state.role        = ""
    st.session_state.customer_id = None

if not st.session_state.logged_in:
    st.markdown(
        """
        <div style='max-width:400px;margin:80px auto 0;text-align:center'>
            <h1>💊 PharmaAssist AI</h1>
            <p style='color:gray'>AI-powered pharmacy customer service</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        st.markdown("#### Sign In")
        username = st.text_input("Username", placeholder="e.g. AH0001 or admin")
        password = st.text_input("Password", type="password")
        if st.button("Login", use_container_width=True, type="primary"):
            user = USERS.get(username)
            if user and user["password"] == hash_password(password):
                st.session_state.logged_in   = True
                st.session_state.username    = username
                st.session_state.role        = user["role"]
                st.session_state.customer_id = user["customer_id"]
                st.rerun()
            else:
                st.error("Invalid username or password.")
        st.caption("Demo accounts: `AH0001 / pass1234` · `admin / admin123`")
    st.stop()

# ── Logout helper in sidebar ──────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"👤 **{st.session_state.username}**")
    st.caption(f"Role: `{st.session_state.role}`")
    if st.button("🚪 Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# ── Pipeline init ─────────────────────────────────────────────────────────────
_pipeline_defaults = {
    "pipeline":     None,
    "thread_id":    f"user_{uuid.uuid4().hex[:8]}",
    "chat_history": [],
    "audio_key":    0,
    "show_mic":     False,
    "input_value":  "",
    "input_key":    0,
    "action_log":   [],
    "last_state":   {},
}
for k, v in _pipeline_defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

if st.session_state.pipeline is None:
    with st.spinner("Loading pipeline..."):
        st.session_state.pipeline = build_graph()


@st.cache_resource(show_spinner="Loading knowledge base...")
def _init_rag():
    from backend.agents.rag_agent import get_rag_collection
    return get_rag_collection()


_init_rag()


# ── Helpers ───────────────────────────────────────────────────────────────────
def _config():
    return {"configurable": {"thread_id": st.session_state.thread_id}}


def _inject_customer_context(text: str) -> str:
    cid = st.session_state.customer_id
    if cid and st.session_state.role == "customer":
        return f"[My customer ID is {cid}] {text}"
    return text


def run_turn(text: str):
    text = text.strip()
    if not text:
        return

    st.session_state.action_log = []
    enriched = _inject_customer_context(text)

    result = st.session_state.pipeline.invoke(
        {"user_input": enriched, "session_id": st.session_state.thread_id},
        config=_config(),
    )
    st.session_state.last_state = result

    if st.session_state.role == "customer":
        entities = result.get("entities", {}) or {}
        extracted_cid = entities.get("customer_id")
        own_cid = st.session_state.customer_id
        if extracted_cid and extracted_cid != own_cid:
            st.session_state.chat_history.append({"role": "user", "content": text})
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": "⚠️ Access denied. You can only view your own account and orders."
            })
            return

    log = []
    log.append(f"🎯 Intent: **{result.get('intent')}** (confidence: {result.get('confidence', 0):.0%})")
    entities = result.get("entities", {})
    if any(v for v in entities.values() if v):
        log.append(f"🔍 Entities: {entities}")
    tr = result.get("tool_result", {})
    if tr:
        log.append(f"🗄️ DB: `{tr.get('status')}` — {str(tr.get('data', ''))[:80]}")
    if result.get("action_taken"):
        log.append(f"⚡ Action: `{result.get('action_taken')}`")
    if result.get("resolution_status"):
        log.append(f"✅ Resolution: `{result.get('resolution_status')}`")
    if result.get("escalation_package"):
        log.append("🚨 Escalation package prepared for human agent")
    st.session_state.action_log = log

    st.session_state.chat_history.append({"role": "user",      "content": text})
    st.session_state.chat_history.append({"role": "assistant", "content": result.get("agent_response", "")})

    try:
        log_session_to_db(dict(result))
    except Exception as e:
        print(f"[streamlit] auto-log error: {e}")

    if result.get("escalation_package") and not result.get("summary"):
        try:
            snap = generate_summary(dict(result))
            st.session_state.last_state = {**result, **snap}
        except Exception as e:
            print(f"[streamlit] auto-summary error: {e}")


def audio_to_text(source) -> str:
    name = getattr(source, "name", "audio.wav")
    ext  = ("." + name.rsplit(".", 1)[-1]) if "." in name else ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(source.read())
        tmp_path = tmp.name
    wav_path = tmp_path
    if ext != ".wav" and PYDUB_AVAILABLE:
        wav_path = tmp_path.rsplit(".", 1)[0] + ".wav"
        AudioSegment.from_file(tmp_path).export(wav_path, format="wav")
    try:
        return transcribe_audio(wav_path)
    finally:
        for p in {tmp_path, wav_path}:
            if os.path.exists(p):
                try:
                    os.unlink(p)
                except Exception:
                    pass


# ── Tabs ──────────────────────────────────────────────────────────────────────
if st.session_state.role == "admin":
    tab_chat, tab_dashboard, tab_drugs = st.tabs(["💬 Customer Chat", "📊 Supervisor Dashboard", "💊 Drug Catalogue"])
else:
    tab_chat, tab_drugs = st.tabs(["💬 Customer Chat", "💊 Drug Catalogue"])
    tab_dashboard = None

# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — Customer Chat
# ════════════════════════════════════════════════════════════════════════════
with tab_chat:
    chat_col, assist_col = st.columns([3, 1], gap="large")

    with chat_col:
        st.markdown("### 💊 PharmaAssist AI")
        if st.session_state.role == "customer":
            st.caption(f"Welcome, **{st.session_state.username}** — ask about your orders, refunds, or pharmacy policy.")
        else:
            st.caption("Admin view — full access to all customer data.")
        st.divider()

        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if st.session_state.last_state.get("escalation_package"):
            st.warning("🚨 This conversation has been escalated to a human agent.")

        col_mic, col_text, col_send = st.columns([1, 8, 1])

        with col_mic:
            mic_icon = "🔴" if st.session_state.show_mic else "🎤"
            if st.button(mic_icon, help="Voice input", use_container_width=True):
                st.session_state.show_mic = not st.session_state.show_mic
                st.rerun()

        with col_text:
            user_input = st.text_input(
                label="msg",
                value=st.session_state.input_value,
                placeholder="Message PharmaAssist...",
                label_visibility="collapsed",
                key=f"input_{st.session_state.input_key}",
            )

        with col_send:
            send_clicked = st.button("➤", use_container_width=True)

        if st.session_state.show_mic:
            recorded = st.audio_input("🎙️ Record, then click Stop", key=f"mic_{st.session_state.audio_key}")
            if recorded:
                with st.spinner("Transcribing..."):
                    try:
                        transcribed = audio_to_text(recorded)
                        st.session_state.input_value = transcribed
                        st.session_state.input_key  += 1
                        st.session_state.audio_key  += 1
                        st.session_state.show_mic    = False
                        st.rerun()
                    except Exception as e:
                        st.error(f"Transcription failed: {e}")

        submitted = user_input.strip()
        if send_clicked and submitted:
            st.session_state.input_value = ""
            st.session_state.input_key  += 1
            with st.chat_message("user"):
                st.markdown(submitted)
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    run_turn(submitted)
                st.markdown(st.session_state.last_state.get("agent_response", ""))
            st.rerun()

    with assist_col:
        st.markdown("### 🤖 Agent Assist")
        st.caption("Real-time AI activity")
        st.divider()

        if st.session_state.action_log:
            st.markdown("**Last turn:**")
            for entry in st.session_state.action_log:
                st.markdown(entry)
        else:
            st.caption("Waiting for first message...")

        st.divider()

        if st.button("🧠 Generate CRM Summary", use_container_width=True):
            if not st.session_state.chat_history:
                st.warning("No conversation yet.")
            else:
                with st.spinner("Generating..."):
                    state = st.session_state.pipeline.get_state(_config()).values
                    updated = generate_summary(dict(state))
                    st.session_state.last_state = {**dict(state), **updated}
                st.rerun()

        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.thread_id    = f"user_{uuid.uuid4().hex[:8]}"
            st.session_state.chat_history = []
            st.session_state.action_log   = []
            st.session_state.last_state   = {}
            st.session_state.input_value  = ""
            st.rerun()

        summary = st.session_state.last_state.get("summary", "")
        if summary:
            st.divider()
            with st.expander("📋 CRM Summary Record", expanded=True):
                st.text(summary)

        ep = st.session_state.last_state.get("escalation_package")
        if ep:
            st.divider()
            with st.expander("🚨 Escalation Handoff Package", expanded=True):
                st.json(ep)

        st.divider()
        memory = st.session_state.last_state.get("memory", [])
        st.caption(f"Turns: {len(memory)}")
        intent = st.session_state.last_state.get("intent")
        if intent:
            st.caption(f"Last intent: `{intent}`")
            conf = st.session_state.last_state.get("confidence", 0)
            st.progress(conf, text=f"Confidence: {conf:.0%}")

# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — Supervisor Dashboard (admin only)
# ════════════════════════════════════════════════════════════════════════════
if tab_dashboard is not None:
    with tab_dashboard:
        st.markdown("### 📊 Supervisor Dashboard")
        st.caption("Aggregated metrics from all completed interactions.")

        if st.button("🔄 Refresh Metrics"):
            st.rerun()

        try:
            from backend.tools.db_tools import get_interaction_metrics, ensure_interactions_table
            ensure_interactions_table()
            metrics = get_interaction_metrics()

            if not metrics or metrics.get("total_sessions", 0) == 0:
                st.info("No interactions logged yet.")
            else:
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Total Sessions",  metrics["total_sessions"])
                col2.metric("Resolution Rate", f"{metrics['resolution_rate']}%")
                col3.metric("Escalation Rate", f"{metrics['escalation_rate']}%")
                col4.metric("Avg Turns (AHT)", metrics["avg_turns"])

                st.divider()
                col_l, col_r = st.columns(2)

                with col_l:
                    st.markdown("**Resolution Breakdown**")
                    st.bar_chart({
                        "Resolved":  metrics["resolved"],
                        "Escalated": metrics["escalated"],
                        "Other":     max(0, metrics["total_sessions"] - metrics["resolved"] - metrics["escalated"]),
                    })

                with col_r:
                    st.markdown("**Top Intents**")
                    if metrics.get("top_intents"):
                        import pandas as pd
                        df = pd.DataFrame(metrics["top_intents"])
                        df.columns = ["Intent", "Count"]
                        st.dataframe(df, use_container_width=True, hide_index=True)
                    else:
                        st.caption("No intent data yet.")

                st.divider()
                st.markdown("**Recent Interactions**")
                try:
                    import psycopg2
                    import psycopg2.extras
                    import pandas as pd
                    from backend.tools.db_tools import get_conn
                    with get_conn() as conn:
                        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                            cur.execute("""
                                SELECT session_id, intent, action_taken, resolution_status, created_at
                                FROM interactions ORDER BY created_at DESC LIMIT 20
                            """)
                            rows = cur.fetchall()
                    if rows:
                        st.dataframe(pd.DataFrame([dict(r) for r in rows]), use_container_width=True, hide_index=True)
                    else:
                        st.caption("No rows yet.")
                except Exception as e:
                    st.warning(f"Could not load recent interactions: {e}")

        except Exception as e:
            st.error(f"Dashboard error: {e}")

# ════════════════════════════════════════════════════════════════════════════
# TAB 3 — Drug Catalogue
# ════════════════════════════════════════════════════════════════════════════
with tab_drugs:
    st.markdown("### 💊 Drug Catalogue")
    st.caption("Browse all available drugs, prices, and stock levels.")

    search = st.text_input("🔍 Search by name or generic name", placeholder="e.g. Paracetamol, Ibuprofen...")

    try:
        import psycopg2
        import psycopg2.extras
        import pandas as pd
        from backend.tools.db_tools import get_conn

        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                if search.strip():
                    cur.execute("""
                        SELECT drug_id, drug_name, generic_name, category,
                               manufacturer, unit_price_inr, stock_qty
                        FROM drugs
                        WHERE drug_name ILIKE %s OR generic_name ILIKE %s
                        ORDER BY drug_name
                    """, (f"%{search}%", f"%{search}%"))
                else:
                    cur.execute("""
                        SELECT drug_id, drug_name, generic_name, category,
                               manufacturer, unit_price_inr, stock_qty
                        FROM drugs ORDER BY drug_name
                    """)
                rows = cur.fetchall()

        if rows:
            df = pd.DataFrame([dict(r) for r in rows])
            df.columns = ["Drug ID", "Drug Name", "Generic Name", "Category", "Manufacturer", "Price (₹)", "Stock"]
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No drugs found matching your search.")

    except Exception as e:
        st.error(f"Could not load drug catalogue: {e}")
