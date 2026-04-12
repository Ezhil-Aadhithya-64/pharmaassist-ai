"use client";
import { useState, useEffect, useCallback } from "react";

type Metrics = {
  total_sessions: number; resolved: number; escalated: number;
  resolution_rate: number; escalation_rate: number; avg_turns: number;
  top_intents: { intent: string; cnt: number }[];
};
type Row = { session_id: string; intent: string; action_taken: string; resolution_status: string; created_at: string };
type DashData = { metrics: Metrics; recent: Row[]; error?: string };

const STATUS_COLOR: Record<string, string> = {
  resolved: "#10b981", escalated: "#ef4444", pending: "#f59e0b",
};

export default function DashboardTab({ role, customerId }: { role: "admin" | "customer"; customerId?: string }) {
  const [data, setData] = useState<DashData | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const url = role === "admin" ? "/api/dashboard" : `/api/dashboard?customer_id=${customerId}`;
      const res = await fetch(url);
      setData(await res.json());
    } catch { setData({ metrics: {} as Metrics, recent: [], error: "Cannot reach backend" }); }
    finally { setLoading(false); }
  }, [role, customerId]);

  useEffect(() => { load(); }, [load]);

  const m = data?.metrics;
  const maxIntent = m?.top_intents?.length ? Math.max(...m.top_intents.map(i => i.cnt)) : 1;

  return (
    <div style={{ flex: 1, overflowY: "auto", padding: "28px 32px", background: "#212121" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24 }}>
        <div>
          <div style={{ fontSize: 20, fontWeight: 700, color: "#ececec" }}>📊 Supervisor Dashboard</div>
          <div style={{ fontSize: 13, color: "#8e8ea0", marginTop: 4 }}>
            {role === "admin" ? "Aggregated metrics from all completed interactions" : `Showing your session history (${customerId})`}
          </div>
        </div>
        <button onClick={load} disabled={loading}
          style={{ padding: "8px 16px", background: "#2f2f2f", border: "1px solid #3f3f3f",
            borderRadius: 8, color: "#ececec", fontSize: 13, cursor: "pointer" }}>
          {loading ? "Loading..." : "🔄 Refresh"}
        </button>
      </div>

      {data?.error && (
        <div style={{ background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)",
          borderRadius: 10, padding: 16, color: "#f87171", fontSize: 13, marginBottom: 20 }}>
          ⚠️ {data.error}
        </div>
      )}

      {!m || m.total_sessions === 0 ? (
        <div style={{ background: "#2f2f2f", borderRadius: 12, padding: 32, textAlign: "center" }}>
          <div style={{ fontSize: 32, marginBottom: 10 }}>📭</div>
          <div style={{ color: "#8e8ea0", fontSize: 14 }}>No interactions logged yet.</div>
          <div style={{ color: "#8e8ea0", fontSize: 12, marginTop: 4 }}>Complete a chat session and click "Log Session to DB".</div>
        </div>
      ) : (
        <>
          {/* Metric cards */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 12, marginBottom: 24 }}>
            {[
              { label: "Total Sessions", value: m.total_sessions || 0, icon: "🗂️", color: "#a78bfa" },
              { label: "Resolution Rate", value: `${isNaN(m.resolution_rate) ? 0 : m.resolution_rate}%`, icon: "✅", color: "#10b981" },
              { label: "Escalation Rate", value: `${isNaN(m.escalation_rate) ? 0 : m.escalation_rate}%`, icon: "🚨", color: "#ef4444" },
              { label: "Avg Turns (AHT)", value: isNaN(m.avg_turns) ? 0 : m.avg_turns, icon: "🔄", color: "#f59e0b" },
            ].map(c => (
              <div key={c.label} style={{ background: "#2f2f2f", border: "1px solid #3f3f3f",
                borderRadius: 12, padding: "18px 20px" }}>
                <div style={{ fontSize: 22, marginBottom: 8 }}>{c.icon}</div>
                <div style={{ fontSize: 24, fontWeight: 700, color: c.color }}>{c.value}</div>
                <div style={{ fontSize: 12, color: "#8e8ea0", marginTop: 4 }}>{c.label}</div>
              </div>
            ))}
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 24 }}>
            {/* Resolution breakdown */}
            <div style={{ background: "#2f2f2f", border: "1px solid #3f3f3f", borderRadius: 12, padding: 20 }}>
              <div style={{ fontSize: 14, fontWeight: 600, color: "#ececec", marginBottom: 16 }}>Resolution Breakdown</div>
              {[
                { label: "Resolved", value: m.resolved || 0, color: "#10b981" },
                { label: "Escalated", value: m.escalated || 0, color: "#ef4444" },
                { label: "Other", value: Math.max(0, (m.total_sessions || 0) - (m.resolved || 0) - (m.escalated || 0)), color: "#8e8ea0" },
              ].map(r => (
                <div key={r.label} style={{ marginBottom: 12 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                    <span style={{ fontSize: 12, color: "#8e8ea0" }}>{r.label}</span>
                    <span style={{ fontSize: 12, color: r.color, fontWeight: 600 }}>{r.value}</span>
                  </div>
                  <div style={{ height: 6, background: "#3f3f3f", borderRadius: 4 }}>
                    <div style={{ height: 6, borderRadius: 4, background: r.color,
                      width: `${m.total_sessions && !isNaN(r.value) ? (r.value / m.total_sessions) * 100 : 0}%`,
                      transition: "width 0.5s" }} />
                  </div>
                </div>
              ))}
            </div>

            {/* Top intents */}
            <div style={{ background: "#2f2f2f", border: "1px solid #3f3f3f", borderRadius: 12, padding: 20 }}>
              <div style={{ fontSize: 14, fontWeight: 600, color: "#ececec", marginBottom: 16 }}>Top Intents</div>
              {m.top_intents?.length ? m.top_intents.map((ti, i) => (
                <div key={ti.intent} style={{ marginBottom: 10 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                    <span style={{ fontSize: 12, color: "#ececec" }}>{ti.intent.replace(/_/g," ")}</span>
                    <span style={{ fontSize: 12, color: "#8e8ea0" }}>{ti.cnt}</span>
                  </div>
                  <div style={{ height: 5, background: "#3f3f3f", borderRadius: 4 }}>
                    <div style={{ height: 5, borderRadius: 4, background: "#a78bfa",
                      width: `${(ti.cnt / maxIntent) * 100}%`, transition: "width 0.5s" }} />
                  </div>
                </div>
              )) : <div style={{ fontSize: 12, color: "#8e8ea0" }}>No data yet.</div>}
            </div>
          </div>

          {/* Recent interactions table */}
          <div style={{ background: "#2f2f2f", border: "1px solid #3f3f3f", borderRadius: 12, overflow: "hidden" }}>
            <div style={{ padding: "16px 20px", borderBottom: "1px solid #3f3f3f" }}>
              <div style={{ fontSize: 14, fontWeight: 600, color: "#ececec" }}>Recent Interactions</div>
            </div>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ background: "#1a1a1a" }}>
                    {["Session ID","Intent","Action","Status","Time"].map(h => (
                      <th key={h} style={{ padding: "10px 16px", textAlign: "left",
                        fontSize: 11, color: "#8e8ea0", fontWeight: 600,
                        textTransform: "uppercase", letterSpacing: "0.06em" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data?.recent?.map((row, i) => (
                    <tr key={i} style={{ borderTop: "1px solid #3f3f3f" }}>
                      <td style={{ padding: "10px 16px", fontSize: 12, fontFamily: "monospace", color: "#8e8ea0" }}>
                        {row.session_id?.slice(0,12)}…
                      </td>
                      <td style={{ padding: "10px 16px", fontSize: 12, color: "#ececec" }}>
                        {row.intent?.replace(/_/g," ") || "—"}
                      </td>
                      <td style={{ padding: "10px 16px", fontSize: 12, color: "#a78bfa" }}>
                        {row.action_taken?.replace(/_/g," ") || "—"}
                      </td>
                      <td style={{ padding: "10px 16px" }}>
                        <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 20, fontWeight: 600,
                          background: row.resolution_status === "resolved" ? "rgba(16,185,129,0.15)"
                            : row.resolution_status === "escalated" ? "rgba(239,68,68,0.15)" : "rgba(245,158,11,0.15)",
                          color: STATUS_COLOR[row.resolution_status] ?? "#8e8ea0" }}>
                          {row.resolution_status || "—"}
                        </span>
                      </td>
                      <td style={{ padding: "10px 16px", fontSize: 11, color: "#8e8ea0" }}>
                        {row.created_at ? new Date(row.created_at).toLocaleString() : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
