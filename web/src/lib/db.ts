import postgres from "postgres";

const url = process.env.DATABASE_URL;

export const sql = url
  ? postgres(url, { max: 4, idle_timeout: 20 })
  : null;

export type ChangeEvent = {
  id: string;
  headline: string;
  summary: string;
  materiality: string;
  published_at: string;
  data_types_added: string[];
  data_types_removed: string[];
  quotes: { text: string; section: string }[];
  slug: string;
  name: string;
};

export type CompanyRow = {
  id: string;
  slug: string;
  name: string;
  website: string;
  category: string;
  privacy_url: string | null;
  last_fetched: string | null;
  last_hash: string | null;
  last_error: string | null;
  data_types: string[];
};

type CompanyQueryRow = Omit<CompanyRow, "data_types"> & {
  practices: { practices?: { data_types?: string[] }[] } | null;
};

function withDataTypes(row: CompanyQueryRow): CompanyRow {
  const { practices, ...rest } = row;
  const types = new Set<string>();
  for (const p of practices?.practices ?? []) {
    for (const t of p.data_types ?? []) types.add(t);
  }
  return { ...rest, data_types: [...types] };
}

export async function listEvents(limit = 40): Promise<ChangeEvent[]> {
  if (!sql) return [];
  try {
    return await sql<ChangeEvent[]>`
      select
        e.id,
        e.headline,
        e.summary,
        e.materiality,
        e.published_at,
        e.data_types_added,
        e.data_types_removed,
        e.quotes,
        c.slug,
        c.name
      from change_events e
      join companies c on c.id = e.company_id
      where e.materiality = 'material'
      order by e.published_at desc
      limit ${limit}
    `;
  } catch {
    return [];
  }
}

export async function listCompanies(): Promise<CompanyRow[]> {
  if (!sql) return [];
  try {
    const rows = await sql<CompanyQueryRow[]>`
      select
        c.id,
        c.slug,
        c.name,
        c.website,
        c.category,
        s.url as privacy_url,
        snap.fetched_at as last_fetched,
        snap.doc_hash as last_hash,
        snap.fetch_error as last_error,
        ext.practices
      from companies c
      left join policy_sources s
        on s.company_id = c.id and s.kind = 'privacy' and s.region = 'global'
      left join lateral (
        select fetched_at, doc_hash, fetch_error, id
        from snapshots
        where source_id = s.id
        order by fetched_at desc
        limit 1
      ) snap on true
      left join lateral (
        select practices
        from extractions
        where snapshot_id = snap.id
        order by created_at desc
        limit 1
      ) ext on true
      order by c.name
    `;
    return rows.map(withDataTypes);
  } catch {
    return [];
  }
}

export async function getCompany(slug: string) {
  if (!sql) return null;
  try {
    const companies = await sql<CompanyQueryRow[]>`
      select
        c.id,
        c.slug,
        c.name,
        c.website,
        c.category,
        s.url as privacy_url,
        snap.fetched_at as last_fetched,
        snap.doc_hash as last_hash,
        snap.fetch_error as last_error,
        ext.practices
      from companies c
      left join policy_sources s
        on s.company_id = c.id and s.kind = 'privacy' and s.region = 'global'
      left join lateral (
        select fetched_at, doc_hash, fetch_error, id
        from snapshots
        where source_id = s.id
        order by fetched_at desc
        limit 1
      ) snap on true
      left join lateral (
        select practices
        from extractions
        where snapshot_id = snap.id
        order by created_at desc
        limit 1
      ) ext on true
      where c.slug = ${slug}
      limit 1
    `;
    const company = companies[0] ? withDataTypes(companies[0]) : null;
    if (!company) return null;

    const events = await sql<ChangeEvent[]>`
      select
        e.id,
        e.headline,
        e.summary,
        e.materiality,
        e.published_at,
        e.data_types_added,
        e.data_types_removed,
        e.quotes,
        c.slug,
        c.name
      from change_events e
      join companies c on c.id = e.company_id
      where c.slug = ${slug}
      order by e.published_at desc
      limit 30
    `;

    const extracts = await sql<
      { practices: unknown; model: string; created_at: string }[]
    >`
      select x.practices, x.model, x.created_at
      from extractions x
      join snapshots snap on snap.id = x.snapshot_id
      join policy_sources s on s.id = snap.source_id
      join companies c on c.id = s.company_id
      where c.slug = ${slug}
      order by x.created_at desc
      limit 1
    `;

    return { company, events, extraction: extracts[0] ?? null };
  } catch {
    return null;
  }
}
