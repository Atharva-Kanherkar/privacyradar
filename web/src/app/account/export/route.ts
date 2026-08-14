import { NextResponse } from "next/server";
import { sql } from "@/lib/db";
import { getSessionFromCookies } from "@/lib/session";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  const session = await getSessionFromCookies();
  if (!session?.user) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }
  if (!sql) {
    return NextResponse.json({ error: "unavailable" }, { status: 503 });
  }

  const profiles = await sql<
    { region: string; created_at: string; updated_at: string }[]
  >`
    select region, created_at, updated_at
    from consumer_profiles
    where user_id = ${session.user.id}
  `;
  const consents = await sql<{ action: string; created_at: string }[]>`
    select action, created_at
    from consent_events
    where user_id = ${session.user.id}
    order by created_at asc
  `;
  const sessions = await sql<
    {
      id: string;
      created_at: string;
      expires_at: string;
      user_agent: string | null;
    }[]
  >`
    select id, created_at, expires_at, user_agent
    from auth_sessions
    where user_id = ${session.user.id}
    order by created_at desc
  `;

  const watches = await sql<{ slug: string; status: string }[]>`
    select c.slug, w.status
    from watches w
    join companies c on c.id = w.company_id
    where w.user_id = ${session.user.id}
    order by c.slug
  `;

  await sql`
    insert into consent_events (user_id, action)
    values (${session.user.id}, 'export')
  `;

  return NextResponse.json(
    {
      user: {
        id: session.user.id,
        email: session.user.email,
      },
      profile: profiles[0] ?? { region: "unspecified" },
      consent_events: consents,
      watches,
      sessions: sessions.map((row) => ({
        id: row.id,
        created_at: row.created_at,
        expires_at: row.expires_at,
        user_agent: row.user_agent,
      })),
    },
    {
      headers: {
        "Content-Disposition": "attachment; filename=privacyradar-export.json",
      },
    },
  );
}
