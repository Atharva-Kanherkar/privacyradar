import { sql } from "@/lib/db";
import { redirectSeeOther } from "@/lib/http";
import { getSessionFromCookies } from "@/lib/session";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const FREQUENCIES = new Set(["immediate", "digest_weekly", "unsubscribed"]);

export async function POST(request: Request) {
  const session = await getSessionFromCookies();
  if (!session?.user) {
    return redirectSeeOther("/login?next=/radar/settings");
  }
  if (!sql) {
    return redirectSeeOther("/radar/settings");
  }
  const form = await request.formData();
  const frequency = String(form.get("frequency") ?? "");
  if (!FREQUENCIES.has(frequency)) {
    return redirectSeeOther("/radar/settings");
  }
  await sql`
    insert into notification_preferences (user_id, channel, frequency)
    values (${session.user.id}, 'email', ${frequency})
    on conflict (user_id) do update
      set frequency = excluded.frequency, updated_at = now()
  `;
  return redirectSeeOther("/radar/settings");
}
