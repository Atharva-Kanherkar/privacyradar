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
  region: string | null;
  source_health: "pending" | "healthy" | "degraded" | "quarantined" | null;
  last_verified_at: string | null;
  last_fetched: string | null;
  last_hash: string | null;
  current_snapshot_id: string | null;
  current_observation_id: string | null;
  normalizer_version: string | null;
  data_types: string[];
};

export type DocumentChangeRow = {
  id: string;
  company_slug: string;
  from_snapshot_id: string | null;
  to_snapshot_id: string;
  added_sections: string[];
  removed_sections: string[];
  modified_sections: string[];
  normalizer_version: string;
  created_at: string;
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
        and e.publication_state = 'published'
      order by e.published_at desc
      limit ${limit}
    `;
  } catch {
    return [];
  }
}

export async function queryCompanies(q?: string): Promise<CompanyRow[]> {
  if (!sql) {
    throw new Error("database unconfigured");
  }
  const needle = (q ?? "").trim().slice(0, 120);
  const rows = needle
    ? await sql<CompanyQueryRow[]>`
      select
        c.id,
        c.slug,
        c.name,
        c.website,
        c.category,
        s.url as privacy_url,
        s.region,
        s.health_status as source_health,
        s.last_success_at as last_verified_at,
        s.current_snapshot_id,
        s.current_observation_id,
        snap.fetched_at as last_fetched,
        snap.doc_hash as last_hash,
        snap.normalizer_version,
        ext.practices
      from companies c
      left join policy_sources s
        on s.company_id = c.id and s.kind = 'privacy' and s.region = 'global'
      left join snapshots snap on snap.id = s.current_snapshot_id
      left join lateral (
        select practices
        from extractions
        where snapshot_id = snap.id
        order by created_at desc
        limit 1
      ) ext on true
      where c.name ilike ${"%" + needle + "%"}
         or c.slug ilike ${"%" + needle + "%"}
      order by c.name
      limit 100
    `
    : await sql<CompanyQueryRow[]>`
      select
        c.id,
        c.slug,
        c.name,
        c.website,
        c.category,
        s.url as privacy_url,
        s.region,
        s.health_status as source_health,
        s.last_success_at as last_verified_at,
        s.current_snapshot_id,
        s.current_observation_id,
        snap.fetched_at as last_fetched,
        snap.doc_hash as last_hash,
        snap.normalizer_version,
        ext.practices
      from companies c
      left join policy_sources s
        on s.company_id = c.id and s.kind = 'privacy' and s.region = 'global'
      left join snapshots snap on snap.id = s.current_snapshot_id
      left join lateral (
        select practices
        from extractions
        where snapshot_id = snap.id
        order by created_at desc
        limit 1
      ) ext on true
      order by c.name
      limit 100
    `;
  return rows.map(withDataTypes);
}

export async function queryCompany(
  slug: string,
): Promise<{
  company: CompanyRow;
  events: ChangeEvent[];
  extraction: { practices: unknown; model: string; created_at: string } | null;
  document_changes: DocumentChangeRow[];
} | null> {
  if (!sql) {
    throw new Error("database unconfigured");
  }
  const companies = await sql<CompanyQueryRow[]>`
      select
        c.id,
        c.slug,
        c.name,
        c.website,
        c.category,
        s.url as privacy_url,
        s.region,
        s.health_status as source_health,
        s.last_success_at as last_verified_at,
        s.current_snapshot_id,
        s.current_observation_id,
        snap.fetched_at as last_fetched,
        snap.doc_hash as last_hash,
        snap.normalizer_version,
        ext.practices
      from companies c
      left join policy_sources s
        on s.company_id = c.id and s.kind = 'privacy' and s.region = 'global'
      left join snapshots snap on snap.id = s.current_snapshot_id
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
        and e.publication_state in ('published', 'corrected')
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

  const document_changes = await sql<DocumentChangeRow[]>`
      select
        dc.id,
        c.slug as company_slug,
        dc.from_snapshot_id,
        dc.to_snapshot_id,
        dc.added_sections,
        dc.removed_sections,
        dc.modified_sections,
        dc.normalizer_version,
        dc.created_at
      from document_changes dc
      join companies c on c.id = dc.company_id
      where c.slug = ${slug}
      order by dc.created_at desc
      limit 20
  `;

  return {
    company,
    events,
    extraction: extracts[0] ?? null,
    document_changes,
  };
}

export async function queryDocumentChange(
  id: string,
): Promise<DocumentChangeRow | null> {
  if (!sql) {
    throw new Error("database unconfigured");
  }
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id)) {
    return null;
  }
  const rows = await sql<DocumentChangeRow[]>`
      select
        dc.id,
        c.slug as company_slug,
        dc.from_snapshot_id,
        dc.to_snapshot_id,
        dc.added_sections,
        dc.removed_sections,
        dc.modified_sections,
        dc.normalizer_version,
        dc.created_at
      from document_changes dc
      join companies c on c.id = dc.company_id
      where dc.id = ${id}
      limit 1
  `;
  return rows[0] ?? null;
}

export type PublishedClaimRow = {
  claim_key: string;
  category: string;
  attribute: string;
  polarity: string;
  quote: string;
  snapshot_id: string;
  revision_id: string;
  revision_n: number;
};

export async function listPublishedClaims(
  companyId: string,
): Promise<PublishedClaimRow[]> {
  if (!sql) return [];
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(companyId)) {
    return [];
  }
  return sql<PublishedClaimRow[]>`
    select
      pc.claim_key,
      pc.category,
      pc.attribute,
      pc.polarity,
      pc.quote,
      pc.snapshot_id,
      pr.id as revision_id,
      pr.revision_n
    from published_claims pc
    join publication_revisions pr on pr.id = pc.revision_id
    where pr.company_id = ${companyId}::uuid
      and pr.state = 'published'
      and not exists (
        select 1 from publication_revisions rb where rb.rolls_back_id = pr.id
      )
      and pr.revision_n = (
        select coalesce(max(pr2.revision_n), 0)
        from publication_revisions pr2
        where pr2.company_id = ${companyId}::uuid
          and pr2.state = 'published'
          and not exists (
            select 1 from publication_revisions rb where rb.rolls_back_id = pr2.id
          )
      )
  `;
}

export async function listCompanies(): Promise<CompanyRow[]> {
  try {
    return await queryCompanies();
  } catch {
    return [];
  }
}

export async function getCompany(slug: string) {
  try {
    return await queryCompany(slug);
  } catch {
    return null;
  }
}
