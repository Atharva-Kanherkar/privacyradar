import { sql } from "@/lib/db";
import { redirectSeeOther } from "@/lib/http";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function hostOf(raw: string): string | null {
  const trimmed = raw.trim();
  const withScheme = trimmed.includes("://") ? trimmed : `https://${trimmed}`;
  try {
    const host = new URL(withScheme).hostname.toLowerCase().replace(/^www\./, "");
    if (!host || host === "localhost" || host.endsWith(".local")) return null;
    if (host === "127.0.0.1" || host === "::1" || host.includes(":")) return null;
    if (/^\d{1,3}(?:\.\d{1,3}){3}$/.test(host)) return null;
    return host;
  } catch {
    return null;
  }
}

export async function POST(request: Request) {
  const form = await request.formData();
  const name = String(form.get("name") ?? "").slice(0, 120);
  const website = String(form.get("website") ?? "");
  const category = String(form.get("category") ?? "consumer").slice(0, 40);
  const host = hostOf(website);
  if (!sql || !name || !host) {
    return redirectSeeOther("/companies/request");
  }
  const companies = await sql<{ id: string; website: string }[]>`
    select id, website from companies
  `;
  const prior = await sql<{ id: string; website: string }[]>`
    select id, website from company_requests
    where status in ('requested', 'accepted')
  `;
  const duplicateOf =
    companies.find((row) => hostOf(row.website) === host)?.id ??
    prior.find((row) => hostOf(row.website) === host)?.id ??
    null;
  const status = duplicateOf ? "duplicate" : "requested";
  await sql`
    insert into company_requests (name, website, category, status, duplicate_of)
    values (${name}, ${"https://" + host}, ${category}, ${status}, ${duplicateOf})
  `;
  return redirectSeeOther(
    status === "duplicate"
      ? "/companies/request?status=duplicate"
      : "/companies/request?status=received",
  );
}
