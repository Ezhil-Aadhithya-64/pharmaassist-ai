"use client";
import { useState, useRef, useEffect, FormEvent } from "react";
import type { Message, AgentInfo } from "../page";

const SUGGESTIONS = [
  "Track my order ORD00001",
  "Cancel order ORD00002",
  "What is your refund policy?",
  "Search for Paracetamol 500mg",
  "Escalate to human agent",
];

const INTENT_ICON: Record<string, string> = {
  track_order:"📦", cancel_order:"🚫", request_refund:"💰", modify_order:"✏️",
  drug_search:"💊", check_policy:"📋", escalate:"🚨", account_status:"👤",
  order_history:"🗂️", general_query:"💬",
};

export default function ChatTab({ messages, loading, agentInfo, sessionId, onSend }:
  { messages: Message[]; loading: boolean; agentInfo: AgentInfo; sessionId: string; onSend: (t:string)=>void }) {

  const [input, setInput] = useState("");
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [mediaRec, setMediaRec] = useState<MediaRecorder|null>(null);
  const [summary, setSummary] = useState("");
  const [summaryLoading, setSummaryLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const chunksRef = useRef<Blob[]>([]);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, loading]);

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); }
  }
  function submit() {
    if (!input.trim() || loading) return;
    onSend(input);
    setInput("");
    if (inputRef.current) inputRef.current.style.height = "auto";
  }

  // ── Voice recording ──────────────────────────────────────────────────────
  async function toggleRecording() {
    if (recording) {
      mediaRec?.stop(); setRecording(false); return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream);
      chunksRef.current = [];
      mr.ondataavailable = e => { if (e.data.size > 0) chunksRef.current.push(e.data); };
      mr.onstop = async () => {
        stream.getTracks().forEach(t => t.stop());
        setTranscribing(true);
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        const form = new FormData();
        form.append("audio", blob, "recording.webm");
        try {
          const res = await fetch("/api/transcribe", { method: "POST", body: form });
          const data = await res.json();
          if (data.text && data.text.trim()) {
            setInput(data.text.trim());
            setTimeout(() => inputRef.current?.focus(), 50);
          } else if (data.error) {
            setInput(`[Transcription error: ${data.error}]`);
          }
        } catch {
          setInput("[Could not reach transcription service]");
        } finally {
          setTranscribing(false);
        }
      };
      mr.start(); setMediaRec(mr); setRecording(true);
    } catch { alert("Microphone access denied."); }
  }

  // ── CRM Summary ──────────────────────────────────────────────────────────
  async function generateSummary() {
    if (!messages.length) return;
    setSummaryLoading(true);
    try {
      const res = await fetch("/api/summary", { method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId }) });
      const data = await res.json();
      setSummary(data.summary || "");
    } catch { setSummary("Error generating summary."); }
    finally { setSummaryLoading(false); }
  }

  const hasEscalation = !!agentInfo.escalation_package;
  const hasEntities = agentInfo.entities && Object.values(agentInfo.entities).some(Boolean);
  const conf = agentInfo.confidence ?? 0;
  const confPct = Math.round(conf * 100);
  const confColor = confPct >= 80 ? "#10b981" : confPct >= 50 ? "#f59e0b" : "#ef4444";

  return (
    <div style={{ display: "flex", height: "100%", minWidth: 0 }}>

      {/* ── Chat area ── */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>

        {/* Header */}
        <div style={{ padding: "14px 24px", borderBottom: "1px solid #2f2f2f",
          display: "flex", alignItems: "center", justifyContent: "space-between", flexShrink: 0 }}>
          <div>
            <div style={{ fontWeight: 600, fontSize: 16, color: "#ececec" }}>💊 PharmaAssist AI</div>
            <div style={{ fontSize: 12, color: "#8e8ea0", marginTop: 2 }}>
              Orders · Refunds · Cancellations · Policy · Drug Search
            </div>
          </div>
          {hasEscalation && (
            <div style={{ background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)",
              borderRadius: 8, padding: "6px 12px", fontSize: 12, color: "#f87171" }}>
              🚨 Escalated to human agent
            </div>
          )}
        </div>

        {/* Messages */}
        <div style={{ flex: 1, overflowY: "auto", padding: "24px 0" }}>
          {messages.length === 0 ? (
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center",
              justifyContent: "center", height: "100%", gap: 20, padding: "0 24px" }}>
              <div style={{ textAlign: "center" }}>
                <div style={{ fontSize: 40, marginBottom: 10 }}>💊</div>
                <div style={{ fontSize: 20, fontWeight: 600, color: "#ececec", marginBottom: 8 }}>How can I help you?</div>
                <div style={{ fontSize: 14, color: "#8e8ea0", maxWidth: 380 }}>
                  I can track orders, process refunds, handle cancellations, search medications, and answer policy questions.
                </div>
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8, justifyContent: "center", maxWidth: 500 }}>
                {SUGGESTIONS.map(s => (
                  <button key={s} onClick={() => onSend(s)}
                    style={{ background: "#2f2f2f", border: "1px solid #3f3f3f", borderRadius: 20,
                      padding: "8px 14px", fontSize: 13, color: "#ececec", cursor: "pointer" }}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
          ) : messages.map((msg, i) => (
            <div key={i} className="msg-in"
              style={{ padding: "6px 0", background: msg.role === "assistant" ? "#2a2a2a" : "transparent" }}>
              <div style={{ maxWidth: 720, margin: "0 auto", padding: "10px 24px",
                display: "flex", gap: 14, alignItems: "flex-start" }}>
                <div style={{ width: 30, height: 30, borderRadius: "50%", flexShrink: 0,
                  background: msg.role === "assistant" ? "#10a37f" : "#5436da",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: 14, color: "white", fontWeight: 700 }}>
                  {msg.role === "assistant" ? "P" : "U"}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: "#ececec", marginBottom: 4 }}>
                    {msg.role === "assistant" ? "PharmaAssist" : "You"}
                    <span style={{ fontSize: 11, color: "#8e8ea0", fontWeight: 400, marginLeft: 8 }}>{msg.ts}</span>
                  </div>
                  <div style={{ fontSize: 14, lineHeight: 1.7, color: "#ececec", whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
                    {msg.content}
                  </div>
                </div>
              </div>
            </div>
          ))}

          {loading && (
            <div style={{ background: "#2a2a2a", padding: "6px 0" }}>
              <div style={{ maxWidth: 720, margin: "0 auto", padding: "10px 24px", display: "flex", gap: 14 }}>
                <div style={{ width: 30, height: 30, borderRadius: "50%", background: "#10a37f",
                  display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14, color: "white", fontWeight: 700, flexShrink: 0 }}>P</div>
                <div style={{ display: "flex", gap: 5, alignItems: "center", paddingTop: 6 }}>
                  {[0,1,2].map(i => <span key={i} style={{ width: 7, height: 7, borderRadius: "50%",
                    background: "#8e8ea0", display: "inline-block" }} className={`dot${i+1}`} />)}
                </div>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div style={{ padding: "16px 24px", borderTop: "1px solid #2f2f2f", flexShrink: 0 }}>
          <div style={{ maxWidth: 720, margin: "0 auto" }}>
            <div style={{ background: "#2f2f2f", border: "1px solid #3f3f3f", borderRadius: 12,
              display: "flex", alignItems: "flex-end", gap: 8, padding: "10px 12px" }}>
              {/* Mic button */}
              <button onClick={toggleRecording} disabled={transcribing}
                title={recording ? "Stop recording" : transcribing ? "Transcribing..." : "Start recording"}
                style={{ width: 34, height: 34, borderRadius: 8, border: "none", cursor: transcribing ? "wait" : "pointer",
                  background: recording ? "rgba(239,68,68,0.15)" : transcribing ? "rgba(245,158,11,0.15)" : "transparent",
                  color: recording ? "#ef4444" : transcribing ? "#f59e0b" : "#8e8ea0", fontSize: 16, flexShrink: 0,
                  display: "flex", alignItems: "center", justifyContent: "center", position: "relative" }}>
                {recording && <span style={{ position: "absolute", inset: 0, borderRadius: 8,
                  border: "2px solid #ef4444" }} className="recording-ring" />}
                {transcribing ? "⏳" : "🎤"}
              </button>

              <textarea ref={inputRef} value={input} onChange={e => {
                  setInput(e.target.value);
                  e.target.style.height = "auto";
                  e.target.style.height = Math.min(e.target.scrollHeight, 160) + "px";
                }}
                onKeyDown={handleKey} placeholder="Message PharmaAssist..." rows={1}
                style={{ flex: 1, background: "transparent", border: "none", outline: "none",
                  color: "#ececec", fontSize: 14, resize: "none", lineHeight: 1.5,
                  fontFamily: "inherit", maxHeight: 160, overflowY: "auto", minHeight: 24 }} />

              <button onClick={submit} disabled={!input.trim() || loading}
                style={{ width: 34, height: 34, borderRadius: 8, border: "none", cursor: "pointer",
                  background: input.trim() && !loading ? "#10a37f" : "#3f3f3f",
                  color: "white", fontSize: 16, flexShrink: 0,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  transition: "background 0.2s" }}>↑</button>
            </div>
            <div style={{ fontSize: 11, color: "#8e8ea0", textAlign: "center", marginTop: 6 }}>
              Enter to send · Shift+Enter for new line · 🎤 to record voice
            </div>
          </div>
        </div>
      </div>

      {/* ── Agent Assist panel ── */}
      <div style={{ width: 280, borderLeft: "1px solid #2f2f2f", background: "#171717",
        display: "flex", flexDirection: "column", padding: "16px", gap: 12,
        overflowY: "auto", flexShrink: 0 }}>

        <div style={{ fontSize: 13, fontWeight: 700, color: "#ececec" }}>🤖 Agent Assist</div>

        {/* Intent + confidence */}
        <div style={{ background: "#2f2f2f", borderRadius: 10, padding: 12 }}>
          <div style={{ fontSize: 11, color: "#8e8ea0", marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.06em" }}>Intent</div>
          {agentInfo.intent ? (
            <>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
                <span style={{ fontSize: 18 }}>{INTENT_ICON[agentInfo.intent] ?? "💬"}</span>
                <span style={{ fontSize: 13, fontWeight: 600, color: "#ececec" }}>{agentInfo.intent.replace(/_/g," ")}</span>
              </div>
              <div style={{ fontSize: 11, color: "#8e8ea0", display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                <span>Confidence</span><span style={{ color: confColor }}>{confPct}%</span>
              </div>
              <div style={{ height: 4, background: "#3f3f3f", borderRadius: 4 }}>
                <div style={{ height: 4, borderRadius: 4, background: confColor, width: `${confPct}%`, transition: "width 0.4s" }} />
              </div>
            </>
          ) : <div style={{ fontSize: 12, color: "#8e8ea0" }}>Waiting...</div>}
        </div>

        {/* Entities */}
        {hasEntities && (
          <div style={{ background: "#2f2f2f", borderRadius: 10, padding: 12 }}>
            <div style={{ fontSize: 11, color: "#8e8ea0", marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.06em" }}>Entities</div>
            {Object.entries(agentInfo.entities!).filter(([,v])=>v).map(([k,v]) => (
              <div key={k} style={{ display: "flex", justifyContent: "space-between", marginBottom: 5 }}>
                <span style={{ fontSize: 12, color: "#8e8ea0" }}>{k.replace(/_/g," ")}</span>
                <span style={{ fontSize: 12, fontFamily: "monospace", color: "#10a37f",
                  background: "rgba(16,163,127,0.1)", padding: "1px 6px", borderRadius: 4 }}>
                  {typeof v === 'object' ? JSON.stringify(v) : v}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Action + Resolution */}
        {(agentInfo.action_taken || agentInfo.resolution_status) && (
          <div style={{ background: "#2f2f2f", borderRadius: 10, padding: 12, display: "flex", flexDirection: "column", gap: 8 }}>
            {agentInfo.action_taken && (
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ fontSize: 11, color: "#8e8ea0" }}>Action</span>
                <span style={{ fontSize: 12, color: "#a78bfa", fontWeight: 600 }}>⚡ {agentInfo.action_taken.replace(/_/g," ")}</span>
              </div>
            )}
            {agentInfo.resolution_status && (
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: 11, color: "#8e8ea0" }}>Status</span>
                <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 20, fontWeight: 600,
                  background: agentInfo.resolution_status==="resolved" ? "rgba(16,185,129,0.15)"
                    : agentInfo.resolution_status==="escalated" ? "rgba(239,68,68,0.15)" : "rgba(245,158,11,0.15)",
                  color: agentInfo.resolution_status==="resolved" ? "#10b981"
                    : agentInfo.resolution_status==="escalated" ? "#ef4444" : "#f59e0b" }}>
                  {agentInfo.resolution_status}
                </span>
              </div>
            )}
            {agentInfo.memory_count !== undefined && (
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ fontSize: 11, color: "#8e8ea0" }}>Turns</span>
                <span style={{ fontSize: 12, color: "#ececec" }}>{agentInfo.memory_count}</span>
              </div>
            )}
          </div>
        )}

        {/* Escalation package */}
        {agentInfo.escalation_package && (
          <div style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)",
            borderRadius: 10, padding: 12 }}>
            <div style={{ fontSize: 11, color: "#f87171", fontWeight: 600, marginBottom: 6 }}>🚨 Escalation Package</div>
            <pre style={{ fontSize: 10, color: "#8e8ea0", whiteSpace: "pre-wrap", wordBreak: "break-all",
              maxHeight: 120, overflowY: "auto" }}>
              {JSON.stringify(agentInfo.escalation_package, null, 2)}
            </pre>
          </div>
        )}

        {/* Actions */}
        <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 4 }}>
          <button onClick={generateSummary} disabled={!messages.length || summaryLoading}
            style={{ padding: "8px", background: "#2f2f2f", border: "1px solid #3f3f3f",
              borderRadius: 8, color: "#ececec", fontSize: 12, cursor: "pointer" }}>
            {summaryLoading ? "Generating..." : "🧠 Generate CRM Summary"}
          </button>
        </div>

        {/* CRM Summary */}
        {summary && (
          <div style={{ background: "#2f2f2f", borderRadius: 10, padding: 12 }}>
            <div style={{ fontSize: 11, color: "#8e8ea0", marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.06em" }}>📋 CRM Summary</div>
            <pre style={{ fontSize: 11, color: "#ececec", whiteSpace: "pre-wrap", lineHeight: 1.5,
              maxHeight: 160, overflowY: "auto" }}>{summary}</pre>
          </div>
        )}
      </div>
    </div>
  );
}
