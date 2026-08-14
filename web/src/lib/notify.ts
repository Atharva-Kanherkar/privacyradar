import { sql } from "@/lib/db";

export type NotifyFrequency = "immediate" | "digest_weekly" | "unsubscribed";

export async function getPreference(userId: string): Promise<{
  frequency: NotifyFrequency;
  muted_company_ids: string[];
}> {
  if (!sql) {
    return { frequency: "immediate", muted_company_ids: [] };
  }
  const rows = await sql<{ frequency: NotifyFrequency; muted_company_ids: string[] }[]>`
    select frequency, muted_company_ids
    from notification_preferences
    where user_id = ${userId}
  `;
  return rows[0] ?? { frequency: "immediate", muted_company_ids: [] };
}
