import { NextResponse } from "next/server";

const backendBase =
  process.env.BACKEND_INTERNAL_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "http://localhost:8000";

export async function GET() {
  const token = process.env.JTA_ADMIN_TOKEN;
  if (!token) {
    return NextResponse.json({ error: "Admin not configured" }, { status: 503 });
  }
  const upstream = await fetch(`${backendBase}/api/admin/sources`, {
    headers: { "x-jta-admin-token": token },
    cache: "no-store",
  });
  const body = await upstream.json();
  return NextResponse.json(body, { status: upstream.status });
}
