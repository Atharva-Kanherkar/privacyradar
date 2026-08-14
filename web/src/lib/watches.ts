import { sql } from "@/lib/db";

const SOURCES = ["company_page", "radar_onboarding", "resume"] as const;
export type WatchSource = (typeof SOURCES)[number];

export function isWatchSource(value: string): value is WatchSource {
  return (SOURCES as readonly string[]).includes(value);
}

export async function followCompany(
  userId: string,
  companyId: string,
  source: WatchSource,
): Promise<void> {
  if (!sql) throw new Error("database unconfigured");
  await sql`
    insert into watches (user_id, company_id, status, source)
    values (${userId}, ${companyId}::uuid, 'active', ${source})
    on conflict (user_id, company_id) do update
      set status = 'active',
          source = excluded.source,
          updated_at = now()
  `;
  await sql`
    insert into product_events (user_id, name, company_id)
    values (${userId}, 'follow', ${companyId}::uuid)
  `;
}

export async function unfollowCompany(userId: string, companyId: string): Promise<void> {
  if (!sql) throw new Error("database unconfigured");
  await sql`
    update watches
    set status = 'unwatched', updated_at = now()
    where user_id = ${userId} and company_id = ${companyId}::uuid
  `;
  await sql`
    insert into product_events (user_id, name, company_id)
    values (${userId}, 'unfollow', ${companyId}::uuid)
  `;
}

export async function companyIdForSlug(slug: string): Promise<string | null> {
  if (!sql) return null;
  const rows = await sql<{ id: string }[]>`
    select id from companies where slug = ${slug} limit 1
  `;
  return rows[0]?.id ?? null;
}

export async function isWatching(userId: string, companyId: string): Promise<boolean> {
  if (!sql) return false;
  const rows = await sql<{ status: string }[]>`
    select status from watches
    where user_id = ${userId} and company_id = ${companyId}::uuid
    limit 1
  `;
  return rows[0]?.status === "active";
}

export type RadarEvent = {
  id: string;
  headline: string;
  summary: string;
  materiality: string;
  published_at: string;
  slug: string;
  name: string;
};

export type WatchedCompany = {
  slug: string;
  name: string;
  category: string;
};

export async function listRadarEvents(userId: string, limit = 40): Promise<RadarEvent[]> {
  if (!sql) return [];
  return sql<RadarEvent[]>`
    select
      e.id,
      e.headline,
      e.summary,
      e.materiality,
      e.published_at,
      c.slug,
      c.name
    from change_events e
    join companies c on c.id = e.company_id
    join watches w on w.company_id = c.id
    where w.user_id = ${userId}
      and w.status = 'active'
      and e.publication_state = 'published'
      and e.materiality = 'material'
    order by e.published_at desc, e.id desc
    limit ${limit}
  `;
}

export async function listWatchedCompanies(userId: string): Promise<WatchedCompany[]> {
  if (!sql) return [];
  return sql<WatchedCompany[]>`
    select c.slug, c.name, c.category
    from watches w
    join companies c on c.id = w.company_id
    where w.user_id = ${userId} and w.status = 'active'
    order by c.name
  `;
}

export async function recordRadarView(userId: string): Promise<void> {
  if (!sql) return;
  await sql`
    insert into product_events (user_id, name)
    values (${userId}, 'radar_view')
  `;
}

export async function catalogSuggestions(): Promise<WatchedCompany[]> {
  if (!sql) return [];
  return sql<WatchedCompany[]>`
    select slug, name, category
    from companies
    order by category, name
    limit 24
  `;
}
