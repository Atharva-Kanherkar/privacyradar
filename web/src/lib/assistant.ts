import { createHash } from "node:crypto";
import { listPublishedClaims, sql } from "@/lib/db";

const DAILY_LIMIT = 10;
const OUT_OF_SCOPE = /\b(weather|stock|sue|illegal|lawyer|other company|competitor)\b/i;

export function hashIdentity(raw: string): string {
  return createHash("sha256").update(raw).digest("hex");
}

export async function assistantEnabled(): Promise<boolean> {
  if (!sql) return false;
  const rows = await sql<{ enabled: boolean }[]>`
    select enabled from product_switches where key = 'assistant' limit 1
  `;
  return Boolean(rows[0]?.enabled);
}

function tokens(question: string): string[] {
  return (question.toLowerCase().match(/[a-z0-9]{3,}/g) ?? []).filter(
    (part, index, all) => all.indexOf(part) === index,
  );
}

export async function askCompany(
  slug: string,
  question: string,
  identity: string,
): Promise<{ status: string; reason: string | null; text: string; citations: { claim_key: string; quote: string }[] }> {
  if (!(await assistantEnabled())) {
    return { status: "disabled", reason: "assistant_off", text: "", citations: [] };
  }
  if ((process.env.ASSISTANT_PROVIDER ?? "fake") !== "fake") {
    return { status: "disabled", reason: "provider_not_allowed", text: "", citations: [] };
  }
  if (!sql) return { status: "disabled", reason: "assistant_off", text: "", citations: [] };
  const companies = await sql<{ id: string }[]>`
    select id from companies where slug = ${slug} limit 1
  `;
  const companyId = companies[0]?.id;
  if (!companyId) {
    return { status: "refused", reason: "unknown_company", text: "", citations: [] };
  }
  const day = new Date().toISOString().slice(0, 10);
  await sql`
    insert into assistant_usage (identity_hash, day, count)
    values (${identity}, ${day}::date, 1)
    on conflict (identity_hash, day) do update
      set count = assistant_usage.count + 1,
          updated_at = now()
  `;
  const usage = await sql<{ count: number }[]>`
    select count from assistant_usage
    where identity_hash = ${identity} and day = ${day}::date
  `;
  if ((usage[0]?.count ?? 0) > DAILY_LIMIT) {
    return { status: "rate_limited", reason: "daily_limit", text: "", citations: [] };
  }
  if (OUT_OF_SCOPE.test(question)) {
    return { status: "refused", reason: "out_of_scope", text: "", citations: [] };
  }
  const claims = await listPublishedClaims(companyId);
  const needle = tokens(question);
  const retrieved = claims.filter((claim) => {
    const blob = `${claim.category} ${claim.attribute} ${claim.quote}`.toLowerCase();
    return needle.some((token) => new RegExp(`\\b${token}\\b`).test(blob));
  });
  const top = retrieved[0];
  if (!top) {
    return { status: "refused", reason: "insufficient_evidence", text: "", citations: [] };
  }
  return {
    status: "answered",
    reason: null,
    text: `We found published evidence: ${top.quote}`,
    citations: [{ claim_key: top.claim_key, quote: top.quote }],
  };
}
