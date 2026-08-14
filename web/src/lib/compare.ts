import { listPublishedClaims, sql } from "@/lib/db";

export const COMPARE_DIMENSIONS = [
  "sensitive",
  "sharing",
  "purpose",
  "retention",
  "control",
  "data_collected",
] as const;

export const MAX_COMPANIES = 4;

export type CompareCell =
  | { slug: string; state: "not_found_in_evidence"; favorable: false }
  | {
      slug: string;
      state: "found";
      attribute: string;
      polarity: string;
      quote: string;
      claim_key: string;
      revision_n: number;
      snapshot_id: string;
    };

export type ComparisonPayload = {
  status: "need_selection" | "comparable" | "not_comparable";
  region_mismatch: boolean;
  taxonomy_version: string | null;
  truncated: boolean;
  companies: Array<{
    slug: string;
    name: string;
    region: string | null;
    health: string | null;
    last_verified_at: string | null;
    corrected: boolean;
    has_publication: boolean;
    taxonomy_version: string | null;
  }>;
  dimensions: Array<{ category: string; cells: CompareCell[] }>;
};

export function parseCompanySlugs(raw: string | string[] | undefined): {
  slugs: string[];
  truncated: boolean;
} {
  const parts = (Array.isArray(raw) ? raw : raw ? [raw] : []).flatMap((item) =>
    item.split(","),
  );
  const seen: string[] = [];
  for (const part of parts) {
    const slug = part.trim().toLowerCase();
    if (slug && !seen.includes(slug)) seen.push(slug);
  }
  return { slugs: seen.slice(0, MAX_COMPANIES), truncated: seen.length > MAX_COMPANIES };
}

export function canonicalComparePath(slugs: string[]): string {
  return slugs.length ? `/compare?companies=${slugs.join(",")}` : "/compare";
}

export async function loadComparison(
  slugs: string[],
  truncated = false,
): Promise<ComparisonPayload> {
  if (slugs.length < 2) {
    return {
      status: "need_selection",
      region_mismatch: false,
      taxonomy_version: null,
      truncated,
      companies: [],
      dimensions: [],
    };
  }
  const rows = sql
    ? await sql<
        {
          id: string;
          slug: string;
          name: string;
          region: string | null;
          health: string | null;
          last_verified_at: string | null;
        }[]
      >`
        select distinct on (c.id)
          c.id,
          c.slug,
          c.name,
          s.region,
          s.health_status as health,
          s.last_success_at as last_verified_at
        from companies c
        left join policy_sources s on s.company_id = c.id and s.kind = 'privacy'
        where c.slug = any(${slugs})
        order by c.id, s.region
      `
    : [];
  const bySlug = new Map(rows.map((row) => [row.slug, row]));
  const companies = [];
  const taxonomies = new Set<string>();
  const regions = new Set<string>();
  const claimsBySlug = new Map<string, Awaited<ReturnType<typeof listPublishedClaims>>>();
  for (const slug of slugs) {
    const row = bySlug.get(slug);
    if (!row) {
      companies.push({
        slug,
        name: slug,
        region: null,
        health: null,
        last_verified_at: null,
        corrected: false,
        has_publication: false,
        taxonomy_version: null,
      });
      claimsBySlug.set(slug, []);
      continue;
    }
    const claims = await listPublishedClaims(row.id);
    const taxonomy = claims[0]?.taxonomy_version ?? null;
    if (taxonomy) taxonomies.add(taxonomy);
    if (row.region) regions.add(row.region);
    claimsBySlug.set(slug, claims);
    companies.push({
      slug: row.slug,
      name: row.name,
      region: row.region,
      health: row.health,
      last_verified_at: row.last_verified_at,
      corrected: false,
      has_publication: claims.length > 0,
      taxonomy_version: taxonomy,
    });
  }
  if (sql) {
    const corrected = await sql<{ slug: string }[]>`
      select c.slug
      from companies c
      join change_events e on e.company_id = c.id
      where c.slug = any(${slugs})
        and e.publication_state = 'corrected'
    `;
    const hit = new Set(corrected.map((row) => row.slug));
    for (const company of companies) {
      if (hit.has(company.slug)) company.corrected = true;
    }
  }
  const region_mismatch = regions.size > 1;
  if (taxonomies.size > 1) {
    return {
      status: "not_comparable",
      region_mismatch,
      taxonomy_version: null,
      truncated,
      companies,
      dimensions: [],
    };
  }
  const dimensions = COMPARE_DIMENSIONS.map((category) => ({
    category,
    cells: slugs.map((slug) => {
      const match = (claimsBySlug.get(slug) ?? []).find((claim) => claim.category === category);
      if (!match) {
        return { slug, state: "not_found_in_evidence" as const, favorable: false as const };
      }
      return {
        slug,
        state: "found" as const,
        attribute: match.attribute,
        polarity: match.polarity,
        quote: match.quote,
        claim_key: match.claim_key,
        revision_n: match.revision_n,
        snapshot_id: match.snapshot_id,
      };
    }),
  }));
  return {
    status: "comparable",
    region_mismatch,
    taxonomy_version: taxonomies.values().next().value ?? null,
    truncated,
    companies,
    dimensions,
  };
}

export async function recordCompareEvent(
  name: "compare_start" | "compare_complete" | "compare_evidence",
): Promise<void> {
  if (!sql) return;
  await sql`insert into product_events (name) values (${name})`;
}
