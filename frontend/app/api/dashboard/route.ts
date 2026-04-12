import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export async function GET(req: NextRequest) {
  try {
    const customerId = req.nextUrl.searchParams.get("customer_id");
    const url = customerId
      ? `${BACKEND_URL}/dashboard?customer_id=${encodeURIComponent(customerId)}`
      : `${BACKEND_URL}/dashboard`;
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) return NextResponse.json({ error: `Backend error: ${res.status}` }, { status: res.status });
    return NextResponse.json(await res.json());
  } catch {
    return NextResponse.json({ error: "Cannot reach backend" }, { status: 502 });
  }
}
