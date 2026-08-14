import { NextRequest, NextResponse } from "next/server";
import { sql } from "@/lib/db";
import { emailHash } from "@/lib/auth-helpers";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

function fixtureInboxEnabled(): boolean {
  if (
    process.env.VERCEL_ENV === "production" ||
    process.env.RAILWAY_ENVIRONMENT_NAME === "production"
  ) {
    return false;
  }
  return process.env.AUTH_DELIVERY === "fixture";
}

export async function GET(request: NextRequest) {
  if (!fixtureInboxEnabled()) {
    return NextResponse.json({ error: "not_found" }, { status: 404 });
  }
  if (!sql) {
    return NextResponse.json({ error: "unavailable" }, { status: 503 });
  }
  const email = request.nextUrl.searchParams.get("email") ?? "";
  if (!email.includes("@")) {
    return NextResponse.json({ error: "invalid" }, { status: 400 });
  }
  const rows = await sql<
    { subject: string; body_text: string; body_html: string }[]
  >`
    select subject, body_text, body_html
    from notification_fixture_inbox
    where email_hash = ${emailHash(email)}
    order by created_at desc
    limit 1
  `;
  const row = rows[0];
  if (!row) {
    return NextResponse.json({ error: "not_found" }, { status: 404 });
  }
  return NextResponse.json(row);
}
