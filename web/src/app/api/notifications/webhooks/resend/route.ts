import { NextRequest, NextResponse } from "next/server";
import { sql } from "@/lib/db";
import { emailHash } from "@/lib/auth-helpers";
import { verifySvixSignature } from "@/lib/svix";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

function fixtureWebhook(request: NextRequest): boolean {
  if (
    process.env.VERCEL_ENV === "production" ||
    process.env.RAILWAY_ENVIRONMENT_NAME === "production"
  ) {
    return false;
  }
  return (
    process.env.AUTH_DELIVERY === "fixture" &&
    request.headers.get("x-privacyradar-fixture-webhook") === "1"
  );
}

export async function POST(request: NextRequest) {
  const body = await request.text();
  if (!fixtureWebhook(request)) {
    const secret = process.env.RESEND_WEBHOOK_SECRET || "";
    const ok = verifySvixSignature({
      secret,
      body,
      svixId: request.headers.get("svix-id") ?? "",
      svixTimestamp: request.headers.get("svix-timestamp") ?? "",
      svixSignature: request.headers.get("svix-signature") ?? "",
    });
    if (!ok) {
      return NextResponse.json({ error: "invalid_webhook" }, { status: 400 });
    }
  }
  if (!sql) {
    return NextResponse.json({ error: "unavailable" }, { status: 503 });
  }
  let payload: {
    type?: string;
    data?: { email_id?: string; id?: string; to?: unknown };
  };
  try {
    payload = JSON.parse(body) as typeof payload;
  } catch {
    return NextResponse.json({ error: "invalid_webhook" }, { status: 400 });
  }
  const eventType = String(payload.type ?? "");
  const data = payload.data ?? {};
  const emailId = String(data.email_id ?? data.id ?? "");
  const providerEventId = request.headers.get("svix-id") || emailId;
  if (!providerEventId) {
    return NextResponse.json({ error: "invalid_webhook" }, { status: 400 });
  }
  const existing = await sql<{ n: number }[]>`
    select 1 as n from notification_deliveries
    where provider_event_id = ${providerEventId}
    limit 1
  `;
  if (existing[0]) {
    return NextResponse.json({ error: "webhook_replay" }, { status: 400 });
  }
  let toEmail = "";
  const recipients = data.to;
  if (Array.isArray(recipients) && recipients[0]) {
    const first = recipients[0];
    toEmail = typeof first === "string" ? first : "";
  } else if (typeof recipients === "string") {
    toEmail = recipients;
  }
  let state: "delivered" | "bounced" | "complained" = "delivered";
  let reason: "bounce" | "complaint" | null = null;
  if (eventType.includes("bounce")) {
    state = "bounced";
    reason = "bounce";
  } else if (eventType.includes("complaint")) {
    state = "complained";
    reason = "complaint";
  }
  let outboxId: string | null = null;
  if (emailId) {
    const matched = await sql<{ outbox_id: string | null }[]>`
      select outbox_id from notification_deliveries
      where provider_message_id = ${emailId}
      order by created_at desc
      limit 1
    `;
    outboxId = matched[0]?.outbox_id ?? null;
  }
  await sql`
    insert into notification_deliveries (
      outbox_id, provider, provider_message_id, provider_event_id, state
    )
    values (${outboxId}, 'resend', ${emailId || null}, ${providerEventId}, ${state})
  `;
  if (reason && outboxId) {
    await sql`
      update notification_outbox set state = 'suppressed' where id = ${outboxId}::uuid
    `;
  }
  if (reason && toEmail) {
    await sql`
      insert into notification_suppressions (email_hash, reason)
      values (${emailHash(toEmail)}, ${reason})
      on conflict (email_hash) do update set reason = excluded.reason
    `;
  }
  return NextResponse.json({ ok: true });
}
