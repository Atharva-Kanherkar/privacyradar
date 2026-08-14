import { sql } from "@/lib/db";
import { emailHash } from "@/lib/auth-helpers";
import { redirectSeeOther } from "@/lib/http";
import { verifyUnsubToken } from "@/lib/unsub-token";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  const form = await request.formData();
  const token = String(form.get("token") ?? "");
  const parsed = verifyUnsubToken(token);
  if (!parsed || !sql) {
    return redirectSeeOther("/unsubscribe");
  }
  if (parsed.purpose.startsWith("mute:")) {
    const companyId = parsed.purpose.slice("mute:".length);
    if (
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(
        companyId,
      )
    ) {
      await sql`
        insert into notification_preferences (user_id, channel, frequency, muted_company_ids)
        values (${parsed.userId}, 'email', 'immediate', array[${companyId}::uuid])
        on conflict (user_id) do update
          set muted_company_ids = (
            select array_agg(distinct x)
            from unnest(
              notification_preferences.muted_company_ids || excluded.muted_company_ids
            ) as x
          ),
          updated_at = now()
      `;
    }
    return redirectSeeOther("/unsubscribe/done");
  }
  const users = await sql<{ email: string }[]>`
    select email from auth_users where id = ${parsed.userId}
  `;
  await sql`
    insert into notification_preferences (user_id, channel, frequency)
    values (${parsed.userId}, 'email', 'unsubscribed')
    on conflict (user_id) do update
      set frequency = 'unsubscribed', updated_at = now()
  `;
  const email = users[0]?.email;
  if (email) {
    await sql`
      insert into notification_suppressions (email_hash, reason)
      values (${emailHash(email)}, 'unsubscribe')
      on conflict (email_hash) do nothing
    `;
  }
  return redirectSeeOther("/unsubscribe/done");
}
