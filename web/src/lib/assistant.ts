import { createHash } from "node:crypto";
import {
  listPublishedClaims,
  sql,
  type ChangeEvent,
  type PublishedClaimRow,
} from "@/lib/db";

export const DAILY_LIMIT = 30;

export function hashIdentity(raw: string): string {
  return createHash("sha256").update(raw).digest("hex");
}

/**
 * The assistant is on when a model key is configured. ASSISTANT_ENABLED=false
 * is the kill switch; the legacy product_switches row no longer gates it.
 */
export function assistantEnabled(): boolean {
  if (process.env.ASSISTANT_ENABLED === "false") return false;
  return Boolean(process.env.OPENAI_API_KEY);
}

export type ChatMessage = { role: "user" | "assistant"; content: string };

export type AssistantGate =
  | { ok: true }
  | { ok: false; code: "disabled" | "rate_limited" | "unknown_company"; message: string };

/**
 * Quota key for signed-out users. The leftmost X-Forwarded-For hop is
 * client-controlled, so prefer the platform-set headers and otherwise take
 * the LAST hop, which the trusted proxy appended.
 */
export function clientIdentity(
  headers: Headers,
  userId: string | undefined,
): string {
  if (userId) return hashIdentity(userId);
  const trusted =
    headers.get("x-vercel-forwarded-for") ?? headers.get("x-real-ip");
  if (trusted) return hashIdentity(trusted.split(",")[0].trim());
  const hops = headers.get("x-forwarded-for")?.split(",") ?? [];
  const lastHop = hops[hops.length - 1]?.trim();
  return hashIdentity(lastHop || "anonymous");
}

export async function underRateLimit(identity: string): Promise<boolean> {
  if (!sql) return false;
  const day = new Date().toISOString().slice(0, 10);
  const usage = await sql<{ count: number }[]>`
    select count from assistant_usage
    where identity_hash = ${identity} and day = ${day}::date
  `;
  return (usage[0]?.count ?? 0) < DAILY_LIMIT;
}

/** Count a question only once we actually spend model tokens on it. */
export async function recordUsage(identity: string): Promise<void> {
  if (!sql) return;
  const day = new Date().toISOString().slice(0, 10);
  await sql`
    insert into assistant_usage (identity_hash, day, count)
    values (${identity}, ${day}::date, 1)
    on conflict (identity_hash, day) do update
      set count = assistant_usage.count + 1,
          updated_at = now()
  `;
}

export type Grounding = {
  companyId: string;
  companyName: string;
  claims: PublishedClaimRow[];
  events: Pick<ChangeEvent, "headline" | "summary" | "published_at">[];
};

export async function loadGrounding(slug: string): Promise<Grounding | null> {
  if (!sql) return null;
  const companies = await sql<{ id: string; name: string }[]>`
    select id, name from companies where slug = ${slug} limit 1
  `;
  const company = companies[0];
  if (!company) return null;
  const claims = await listPublishedClaims(company.id);
  const events = await sql<
    Pick<ChangeEvent, "headline" | "summary" | "published_at">[]
  >`
    select headline, summary, published_at
    from change_events
    where company_id = ${company.id}::uuid
      and publication_state in ('published', 'corrected')
    order by published_at desc
    limit 10
  `;
  return {
    companyId: company.id,
    companyName: company.name,
    claims,
    events,
  };
}

function formatClaim(claim: PublishedClaimRow): string {
  const status =
    claim.polarity === "negated"
      ? "the policy states this does NOT happen"
      : claim.polarity === "disclosed"
        ? "disclosed"
        : "unspecified";
  return `- [${claim.category} / ${claim.attribute} — ${status}] Exact policy quote: "${claim.quote}"`;
}

export function buildSystemPrompt(grounding: Grounding): string {
  const claimBlock =
    grounding.claims.length > 0
      ? grounding.claims.map(formatClaim).join("\n")
      : "(No published evidence yet for this company.)";
  const eventBlock =
    grounding.events.length > 0
      ? grounding.events
          .map(
            (event) =>
              `- ${new Date(event.published_at).toISOString().slice(0, 10)}: ${event.headline} — ${event.summary}`,
          )
          .join("\n")
      : "(No published policy changes yet.)";

  return `You are the PrivacyRadar assistant. You help everyday people understand what ${grounding.companyName} says in its privacy policy.

You may ONLY use the published evidence below. It was extracted verbatim from ${grounding.companyName}'s captured privacy policy.

## Published evidence for ${grounding.companyName}
${claimBlock}

## Recent published policy changes
${eventBlock}

## Rules
- Answer in plain, friendly language a non-lawyer understands. Be concise: 2-6 short sentences for most questions.
- When you state a practice, back it with the exact policy quote in quotation marks.
- If the evidence above does not cover the question, say plainly: "PrivacyRadar hasn't published evidence about that yet" — never guess or use outside knowledge about the company.
- "the policy states this does NOT happen" evidence means the company explicitly denies the practice; you can say so, with the quote.
- Only discuss ${grounding.companyName}'s privacy practices. Politely decline anything else (other companies, legal advice, unrelated topics).
- You are not a lawyer and this is not legal advice; only mention this if the user asks for legal advice.
- Do not use markdown formatting (no **, #, or bullet lists). Write plain sentences.`;
}
