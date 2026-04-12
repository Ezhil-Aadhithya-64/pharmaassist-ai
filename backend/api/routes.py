"""
FastAPI backend for PharmaAssist AI.
Canonical location: backend/api/routes.py

Run from project root:
    uvicorn backend.api.routes:app --reload --port 8000
"""
import os
import subprocess
import tempfile
from typing import Optional

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator

import backend.core.config as _cfg  # noqa: F401 — ensures .env is loaded
from backend.core.graph import build_graph

# CORS configuration - restrict origins for production
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8501").split(",")

app = FastAPI(title="PharmaAssist AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

_pipeline = None


@app.on_event("startup")
async def startup():
    global _pipeline
    _pipeline = build_graph()
    print("[startup] pipeline ready")
    try:
        import chromadb  # noqa: F401
        from backend.agents.rag_agent import get_rag_collection
        get_rag_collection()
        print("[startup] RAG warmed")
    except ImportError:
        print("[startup] chromadb not installed — RAG disabled on this deployment")


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000, description="User message")
    session_id: Optional[str] = Field(default="default", max_length=100)
    customer_id: Optional[str] = Field(default=None, max_length=50)
    
    @validator('message')
    def sanitize_message(cls, v):
        return v.strip()
    
    @validator('session_id')
    def sanitize_session_id(cls, v):
        if v:
            return v.strip()
        return "default"


class ChatResponse(BaseModel):
    response: str
    intent: Optional[str] = None
    confidence: Optional[float] = None
    entities: Optional[dict] = None
    action_taken: Optional[str] = None
    resolution_status: Optional[str] = None
    tool_status: Optional[str] = None
    summary: Optional[str] = None
    escalation_package: Optional[dict] = None
    memory_count: Optional[int] = None


class SessionRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=100)
    
    @validator('session_id')
    def sanitize_session_id(cls, v):
        return v.strip()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    result = _pipeline.invoke(
        {"user_input": req.message, "session_id": req.session_id, "customer_id": req.customer_id},
        config={"configurable": {"thread_id": req.session_id}},
    )
    tool_result = result.get("tool_result") or {}
    tool_status = tool_result.get("status") if isinstance(tool_result, dict) else None
    memory = result.get("memory") or []
    return ChatResponse(
        response=result.get("agent_response", ""),
        intent=result.get("intent"),
        confidence=result.get("confidence"),
        entities=result.get("entities"),
        action_taken=result.get("action_taken"),
        resolution_status=result.get("resolution_status"),
        tool_status=tool_status,
        summary=result.get("summary"),
        escalation_package=result.get("escalation_package"),
        memory_count=len(memory),
    )


@app.get("/dashboard")
def dashboard(customer_id: Optional[str] = None):
    # Input sanitization
    if customer_id:
        customer_id = customer_id.strip()[:50]
    
    try:
        from backend.tools.db_tools import get_interaction_metrics, ensure_interactions_table, get_conn, release_conn
        import psycopg2.extras
        ensure_interactions_table()
        metrics = get_interaction_metrics(customer_id=customer_id)
        recent = []
        conn = None
        try:
            conn = get_conn()
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                if customer_id:
                    cur.execute("""
                        SELECT * FROM (
                            SELECT DISTINCT ON (session_id) session_id, intent, action_taken, resolution_status,
                                   created_at::text as created_at
                            FROM interactions
                            WHERE session_id LIKE %s
                            ORDER BY session_id, created_at DESC
                        ) t ORDER BY created_at DESC LIMIT 20
                    """, (f"{customer_id}_%",))
                else:
                    cur.execute("""
                        SELECT * FROM (
                            SELECT DISTINCT ON (session_id) session_id, intent, action_taken, resolution_status,
                                   created_at::text as created_at
                            FROM interactions
                            ORDER BY session_id, created_at DESC
                        ) t ORDER BY created_at DESC LIMIT 20
                    """)
                recent = [dict(r) for r in cur.fetchall()]
        finally:
            if conn:
                release_conn(conn)
        return {"metrics": metrics, "recent": recent}
    except Exception as e:
        return {"error": str(e), "metrics": {}, "recent": []}


@app.post("/summary")
def generate_summary_endpoint(req: SessionRequest):
    try:
        state = _pipeline.get_state(
            {"configurable": {"thread_id": req.session_id}}
        ).values
        from backend.agents.summary_agent import generate_summary
        updated = generate_summary(dict(state))
        return {"summary": updated.get("summary", "")}
    except Exception as e:
        return {"error": str(e), "summary": ""}


@app.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    suffix = os.path.splitext(audio.filename or "audio.webm")[1] or ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await audio.read())
        tmp_path = tmp.name

    wav_path = tmp_path
    if suffix.lower() != ".wav":
        wav_path = tmp_path.rsplit(".", 1)[0] + ".wav"
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-i", tmp_path, wav_path],
                check=True, capture_output=True
            )
        except Exception:
            try:
                from pydub import AudioSegment
                AudioSegment.from_file(tmp_path).export(wav_path, format="wav")
            except Exception as e:
                return {"error": f"Audio conversion failed: {e}", "text": ""}

    try:
        from backend.services.stt_service import transcribe_audio
        text = transcribe_audio(wav_path)
        return {"text": text}
    except Exception as e:
        return {"error": str(e), "text": ""}
    finally:
        for p in {tmp_path, wav_path}:
            if os.path.exists(p):
                try:
                    os.unlink(p)
                except Exception:
                    pass


@app.get("/drugs")
def get_drugs(search: str = ""):
    # Input sanitization
    search = search.strip()[:200]  # Limit search length
    
    try:
        from backend.tools.db_tools import get_conn, release_conn
        import psycopg2.extras
        conn = None
        try:
            conn = get_conn()
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                if search:
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
                return {"drugs": [dict(r) for r in cur.fetchall()]}
        finally:
            if conn:
                release_conn(conn)
    except Exception as e:
        return {"error": str(e), "drugs": []}


@app.post("/log-session")
def log_session_endpoint(req: SessionRequest):
    try:
        state = _pipeline.get_state(
            {"configurable": {"thread_id": req.session_id}}
        ).values
        if state.get("session_logged"):
            print(f"[log-session] skipped — already logged for session={req.session_id}")
            return {"logged": True, "skipped": True}
        from backend.agents.summary_agent import log_session_to_db
        log_session_to_db(dict(state))
        return {"logged": True}
    except Exception as e:
        return {"error": str(e), "logged": False}

