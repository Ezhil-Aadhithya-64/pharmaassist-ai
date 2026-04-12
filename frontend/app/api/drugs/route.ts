import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export async function GET(req: NextRequest) {
  try {
    const search = req.nextUrl.searchParams.get("search") || "";
    const res = await fetch(`${BACKEND_URL}/drugs?search=${encodeURIComponent(search)}`, { cache: "no-store" });
    if (!res.ok) return NextResponse.json({ drugs: [], error: `Backend error: ${res.status}` }, { status: res.status });
    return NextResponse.json(await res.json());
  } catch {
    return NextResponse.json({ drugs: [], error: "Cannot reach backend" }, { status: 502 });
  }
}
