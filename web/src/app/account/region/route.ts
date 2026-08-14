import { sql } from "@/lib/db";
import { redirectSeeOther } from "@/lib/http";
import { isPolicyRegion } from "@/lib/regions";
import { getSessionFromCookies } from "@/lib/session";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  const session = await getSessionFromCookies();
  if (!session?.user) {
    return redirectSeeOther("/login");
  }
  if (!sql) {
    return redirectSeeOther("/account");
  }
  const form = await request.formData();
  const region = String(form.get("region") ?? "");
  if (!isPolicyRegion(region)) {
    return redirectSeeOther("/account");
  }
  await sql`
    insert into consumer_profiles (user_id, region, updated_at)
    values (${session.user.id}, ${region}, now())
    on conflict (user_id) do update
      set region = excluded.region, updated_at = now()
  `;
  await sql`
    insert into consent_events (user_id, action)
    values (${session.user.id}, 'region_change')
  `;
  return redirectSeeOther("/account");
}
