"use client";
import { useState, useEffect } from "react";

type Drug = {
  drug_id: string; drug_name: string; generic_name: string;
  category: string; manufacturer: string; unit_price_inr: number; stock_qty: number;
};

const COLS = ["Drug ID", "Drug Name", "Generic Name", "Category", "Manufacturer", "Price (₹)", "Stock"];

export default function DrugCatalogue() {
  const [drugs, setDrugs] = useState<Drug[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetch(`/api/drugs?search=${encodeURIComponent(search)}`)
      .then(r => r.json())
      .then(d => setDrugs(d.drugs || []))
      .catch(() => setDrugs([]))
      .finally(() => setLoading(false));
  }, [search]);

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", height: "100%", background: "#212121" }}>
      {/* Header */}
      <div style={{ padding: "20px 28px 16px", borderBottom: "1px solid #2f2f2f", flexShrink: 0 }}>
        <div style={{ fontSize: 20, fontWeight: 700, color: "#ececec", marginBottom: 4 }}>💊 Drug Catalogue</div>
        <div style={{ fontSize: 13, color: "#8e8ea0" }}>Browse all available medications, prices and stock levels</div>
        <div style={{ marginTop: 14, display: "flex", alignItems: "center", gap: 12 }}>
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search by name or generic name..."
            style={{
              width: 320, padding: "8px 14px", background: "#2f2f2f",
              border: "1px solid #3f3f3f", borderRadius: 8, color: "#ececec",
              fontSize: 13, outline: "none",
            }}
          />
          {!loading && (
            <span style={{ fontSize: 12, color: "#8e8ea0" }}>{drugs.length} drug{drugs.length !== 1 ? "s" : ""}</span>
          )}
        </div>
      </div>

      {/* Table */}
      <div style={{ flex: 1, overflowY: "auto", padding: "0 28px 24px" }}>
        {loading ? (
          <div style={{ padding: 40, textAlign: "center", color: "#8e8ea0", fontSize: 14 }}>Loading...</div>
        ) : drugs.length === 0 ? (
          <div style={{ padding: 40, textAlign: "center", color: "#8e8ea0", fontSize: 14 }}>No drugs found.</div>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 16 }}>
            <thead>
              <tr style={{ position: "sticky", top: 0, background: "#171717", zIndex: 1 }}>
                {COLS.map(h => (
                  <th key={h} style={{
                    padding: "10px 14px", textAlign: "left", fontSize: 11,
                    color: "#8e8ea0", fontWeight: 600, textTransform: "uppercase",
                    letterSpacing: "0.06em", borderBottom: "1px solid #2f2f2f",
                    whiteSpace: "nowrap",
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {drugs.map((d, i) => (
                <tr key={d.drug_id}
                  style={{ borderBottom: "1px solid #2a2a2a", background: i % 2 === 0 ? "transparent" : "#1e1e1e" }}>
                  <td style={{ padding: "11px 14px", fontSize: 12, fontFamily: "monospace", color: "#8e8ea0", whiteSpace: "nowrap" }}>
                    {d.drug_id}
                  </td>
                  <td style={{ padding: "11px 14px", fontSize: 13, color: "#ececec", fontWeight: 500, whiteSpace: "nowrap" }}>
                    {d.drug_name}
                  </td>
                  <td style={{ padding: "11px 14px", fontSize: 12, color: "#a0a0b0", whiteSpace: "nowrap" }}>
                    {d.generic_name}
                  </td>
                  <td style={{ padding: "11px 14px" }}>
                    <span style={{
                      fontSize: 11, padding: "3px 8px", borderRadius: 20,
                      background: "#2f2f2f", border: "1px solid #3f3f3f", color: "#a78bfa",
                      whiteSpace: "nowrap",
                    }}>{d.category}</span>
                  </td>
                  <td style={{ padding: "11px 14px", fontSize: 12, color: "#a0a0b0", whiteSpace: "nowrap" }}>
                    {d.manufacturer}
                  </td>
                  <td style={{ padding: "11px 14px", fontSize: 13, color: "#10a37f", fontWeight: 600, whiteSpace: "nowrap" }}>
                    ₹{Number(d.unit_price_inr).toFixed(2)}
                  </td>
                  <td style={{ padding: "11px 14px", whiteSpace: "nowrap" }}>
                    <span style={{
                      fontSize: 12, fontWeight: 600,
                      color: d.stock_qty === 0 ? "#ef4444" : d.stock_qty < 20 ? "#f59e0b" : "#10b981",
                    }}>
                      {d.stock_qty === 0 ? "Out of stock" : `${d.stock_qty}`}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
