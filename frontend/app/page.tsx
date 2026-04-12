"use client";
import { useState, useCallback, useEffect } from "react";
import ChatTab from "./components/ChatTab";
import DashboardTab from "./components/DashboardTab";
import DrugCatalogue from "./components/DrugCatalogue";

export type Message = {
  role: "user" | "assistant";
  content: string;
  ts: string;
};
export type AgentInfo = {
  intent?: string; confidence?: number; entities?: Record<string, string>;
  action_taken?: string; resolution_status?: string; tool_status?: string;
  summary?: string; escalation_package?: object; memory_count?: number;
};

// Simple credential store — admin has full access, customers see only their own data
const USERS: Record<string, { password: string; role: "admin" | "customer"; customerId?: string; email?: string }> = {
  admin:  { password: "admin123", role: "admin", email: "ezhilaadhi642005@gmail.com" },
  AH0001: { password: "AH0001", role: "customer", customerId: "AH0001" },
  CK0002: { password: "CK0002", role: "customer", customerId: "CK0002" },
  PO0003: { password: "PO0003", role: "customer", customerId: "PO0003" },
  FP0004: { password: "FP0004", role: "customer", customerId: "FP0004" },
  IE0005: { password: "IE0005", role: "customer", customerId: "IE0005" },
};

type AuthUser = { userId: string; role: "admin" | "customer"; customerId?: string };

function LoginPage({ onLogin }: { onLogin: (u: AuthUser) => void }) {
  const [userId, setUserId] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    const user = USERS[userId.trim()];
    if (!user || user.password !== password) {
      setError("Invalid user ID or password.");
      return;
    }
    setError("");
    onLogin({ userId: userId.trim(), role: user.role, customerId: user.customerId });
  }

  return (
    <div style={{ display: "flex", height: "100vh", background: "#212121",
      alignItems: "center", justifyContent: "center" }}>
      <div style={{ background: "#171717", border: "1px solid #2f2f2f", borderRadius: 16,
        padding: "40px 36px", width: 360 }}>
        <div style={{ textAlign: "center", marginBottom: 28 }}>
          <div style={{ fontSize: 36, marginBottom: 8 }}>💊</div>
          <div style={{ fontSize: 20, fontWeight: 700, color: "#ececec" }}>PharmaAssist</div>
          <div style={{ fontSize: 13, color: "#8e8ea0", marginTop: 4 }}>Sign in to continue</div>
        </div>
        <form onSubmit={handleLogin} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div>
            <label style={{ fontSize: 12, color: "#8e8ea0", display: "block", marginBottom: 6 }}>User ID</label>
            <input value={userId} onChange={e => setUserId(e.target.value)}
              placeholder="e.g. AH0001 or admin"
              style={{ width: "100%", background: "#2f2f2f", border: "1px solid #3f3f3f",
                borderRadius: 8, padding: "10px 12px", color: "#ececec", fontSize: 14,
                outline: "none", boxSizing: "border-box" }} />
          </div>
          <div>
            <label style={{ fontSize: 12, color: "#8e8ea0", display: "block", marginBottom: 6 }}>Password</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)}
              placeholder="Enter password"
              style={{ width: "100%", background: "#2f2f2f", border: "1px solid #3f3f3f",
                borderRadius: 8, padding: "10px 12px", color: "#ececec", fontSize: 14,
                outline: "none", boxSizing: "border-box" }} />
          </div>
          {error && <div style={{ fontSize: 12, color: "#ef4444" }}>{error}</div>}
          <button type="submit"
            style={{ padding: "11px", background: "#10a37f", border: "none", borderRadius: 8,
              color: "white", fontSize: 14, fontWeight: 600, cursor: "pointer", marginTop: 4 }}>
            Sign In
          </button>
        </form>
        <div style={{ marginTop: 20, fontSize: 11, color: "#8e8ea0", textAlign: "center" }}>
          Demo: use your customer ID as both username &amp; password, or <br />
          <span style={{ color: "#a78bfa" }}>admin / admin123</span> for full access
        </div>
      </div>
    </div>
  );
}

export default function Home() {
  const [auth, setAuth] = useState<AuthUser | null>(null);
  const [tab, setTab] = useState<"chat" | "dashboard" | "drugs">("chat");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [agentInfo, setAgentInfo] = useState<AgentInfo>({});
  const [sessionId, setSessionId] = useState("loading");

  useEffect(() => {
    if (auth) {
      setSessionId(`${auth.customerId ?? auth.userId}_${Math.random().toString(36).slice(2, 8)}`);
    }
  }, [auth]);

  const sendMessage = useCallback(async (text: string) => {
    const msg = text.trim();
    if (!msg || loading) return;
    const ts = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    setMessages(p => [...p, { role: "user", content: msg, ts }]);
    setLoading(true);
    try {
      const res = await fetch("/api/chat", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: msg,
          session_id: sessionId,
          customer_id: auth?.customerId ?? null,
        }),
      });
      const data = await res.json();
      const rts = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
      setMessages(p => [...p, { role: "assistant", content: data.response || data.error || "Sorry, couldn't process that.", ts: rts }]);
      const info: AgentInfo = {
        intent: data.intent, confidence: data.confidence, entities: data.entities,
        action_taken: data.action_taken, resolution_status: data.resolution_status,
        tool_status: data.tool_status, summary: data.summary,
        escalation_package: data.escalation_package, memory_count: data.memory_count,
      };
      setAgentInfo(info);
      // Auto-log session to DB after every assistant response
      autoLogSession(sessionId);
    } catch {
      setMessages(p => [...p, { role: "assistant", content: "⚠️ Connection error. Is the backend running?", ts: "—" }]);
    } finally { setLoading(false); }
  }, [loading, sessionId, auth]);

  async function autoLogSession(sid: string) {
    try {
      await fetch("/api/log-session", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sid }),
      });
    } catch { /* silent — logging is best-effort */ }
  }

  const clearChat = () => { setMessages([]); setAgentInfo({}); };

  const handleLogout = () => {
    setAuth(null);
    setMessages([]);
    setAgentInfo({});
    setTab("chat");
    setSessionId("loading");
  };

  if (!auth) return <LoginPage onLogin={setAuth} />;

  return (
    <div style={{ display: "flex", height: "100vh", background: "#212121" }}>
      {/* Sidebar */}
      <nav style={{ width: 260, background: "#171717", borderRight: "1px solid #2f2f2f",
        display: "flex", flexDirection: "column", padding: "12px 8px", gap: 4, flexShrink: 0, overflowY: "auto" }}>

        {/* Logo */}
        <div style={{ padding: "8px 12px 16px", display: "flex", alignItems: "center", gap: 10, flexShrink: 0 }}>
          <span style={{ fontSize: 22 }}>💊</span>
          <div>
            <div style={{ fontWeight: 700, fontSize: 15, color: "#ececec" }}>PharmaAssist</div>
            <div style={{ fontSize: 11, color: "#8e8ea0" }}>AI Customer Service</div>
          </div>
        </div>

        {/* Nav tabs */}
        {[["chat","💬","Customer Chat"],["dashboard","📊","Supervisor Dashboard"],["drugs","💊","Drug Catalogue"]].filter(([id]) => id !== "dashboard" || auth.role === "admin").map(([id,icon,label]) => (
          <button key={id} onClick={() => setTab(id as "chat"|"dashboard"|"drugs")}
            style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 12px",
              borderRadius: 8, border: "none", cursor: "pointer", textAlign: "left", width: "100%",
              background: tab === id ? "#2f2f2f" : "transparent",
              color: tab === id ? "#ececec" : "#8e8ea0", fontSize: 14, fontWeight: tab === id ? 600 : 400,
              transition: "all 0.15s", flexShrink: 0 }}>
            <span>{icon}</span><span>{label}</span>
          </button>
        ))}

        {/* Session + user info + logout */}
        <div style={{ marginTop: "auto", padding: "12px", borderTop: "1px solid #2f2f2f", flexShrink: 0 }}>
          {/* Logged-in user */}
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
            <div style={{ width: 28, height: 28, borderRadius: "50%", flexShrink: 0,
              background: auth.role === "admin" ? "#a78bfa" : "#10a37f",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 12, color: "white", fontWeight: 700 }}>
              {auth.role === "admin" ? "A" : auth.userId[0]}
            </div>
            <div style={{ minWidth: 0 }}>
              <div style={{ fontSize: 12, color: "#ececec", fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {auth.userId}
              </div>
              <div style={{ fontSize: 10, color: auth.role === "admin" ? "#a78bfa" : "#10a37f" }}>
                {auth.role === "admin" ? "Admin" : "Customer"}
              </div>
            </div>
          </div>

          <div style={{ fontSize: 11, color: "#8e8ea0", marginBottom: 4 }}>Session</div>
          <div style={{ fontSize: 11, fontFamily: "monospace", color: "#ececec", wordBreak: "break-all" }}>{sessionId}</div>
          <div style={{ display: "flex", gap: 6, marginTop: 10 }}>
            <button onClick={clearChat} style={{ flex: 1, padding: "7px",
              background: "transparent", border: "1px solid #3f3f3f", borderRadius: 7,
              color: "#8e8ea0", fontSize: 12, cursor: "pointer" }}>
              🗑️ New Chat
            </button>
            <button onClick={handleLogout} style={{ flex: 1, padding: "7px",
              background: "transparent", border: "1px solid #3f3f3f", borderRadius: 7,
              color: "#ef4444", fontSize: 12, cursor: "pointer" }}>
              ⏏ Logout
            </button>
          </div>
        </div>
      </nav>

      {/* Main */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        {tab === "chat"
          ? <ChatTab messages={messages} loading={loading} agentInfo={agentInfo} sessionId={sessionId} onSend={sendMessage} />
          : tab === "dashboard" ? <DashboardTab role={auth.role} customerId={auth.customerId} />
          : <DrugCatalogue />}
      </div>
    </div>
  );
}
