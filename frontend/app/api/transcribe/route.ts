import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export async function POST(req: NextRequest) {
  try {
    const form = await req.formData();
    const res = await fetch(`${BACKEND_URL}/transcribe`, {
      method: "POST",
      body: form,
    });
    if (!res.ok) return NextResponse.json({ error: `Backend error: ${res.status}` }, { status: res.status });
    return NextResponse.json(await res.json());
  } catch {
    return NextResponse.json({ error: "Cannot reach backend" }, { status: 502 });
  }
}
