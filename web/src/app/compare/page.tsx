import type { Metadata } from "next";
import Link from "next/link";
import { FreshnessLabel } from "@/components/FreshnessLabel";
import { StatePanel } from "@/components/StatePanel";
import {
  canonicalComparePath,
  loadComparison,
  parseCompanySlugs,
  recordCompareEvent,
  type CompareCell,
  type ComparisonPayload,
} from "@/lib/compare";
import { loadCompanies } from "@/lib/db";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Compare companies",
  description:
    "Side-by-side published privacy disclosures. Not a score. Unknown stays unknown.",
};

function cellCopy(cell: CompareCell): string {
  if (cell.state === "not_found_in_evidence") {
    return "Not found in evidence. That is not a claim that the company does not do this.";
  }
  return `${cell.attribute.replaceAll("_", " ")} (${cell.polarity})`;
}

function ComparisonMatrix({
  comparison,
  slugs,
}: {
  comparison: ComparisonPayload;
  slugs: string[];
}) {
  return (
    <>
      <div className="mt-8 hidden md:block overflow-x-auto">
        <table className="w-full border-collapse text-left text-sm">
          <caption className="sr-only">
            Published disclosures by dimension and company. Not a privacy score.
          </caption>
          <thead>
            <tr className="border-b border-[var(--rule)]">
              <th scope="col" className="py-2 font-normal text-[var(--muted)]">
                Dimension
              </th>
              {comparison.companies.map((company) => (
                <th key={company.slug} scope="col" className="py-2 font-normal">
                  <Link href={`/companies/${company.slug}`} className="underline">
                    {company.name}
                  </Link>
                  <p className="mt-1 font-sans text-xs text-[var(--muted)]">
                    source region {company.region ?? "not labeled"}
                    {company.corrected ? " · corrected" : ""}
                  </p>
                  <FreshnessLabel
                    lastCheckedAt={company.last_verified_at}
                    health={
                      company.health as
                        | "pending"
                        | "healthy"
                        | "degraded"
                        | "quarantined"
                        | null
                    }
                  />
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {comparison.dimensions.map((row) => (
              <tr key={row.category} className="border-b border-[var(--rule)] align-top">
                <th scope="row" className="py-3 font-normal">
                  {row.category.replaceAll("_", " ")}
                </th>
                {row.cells.map((cell) => (
                  <td key={cell.slug} className="py-3 pr-4">
                    <p>{cellCopy(cell)}</p>
                    {cell.state === "found" ? (
                      <p className="mt-2">
                        <a
                          className="font-sans text-sm underline"
                          href={`/compare/evidence?slug=${cell.slug}&claim=${cell.claim_key}&companies=${slugs.join(",")}`}
                        >
                          Open evidence
                        </a>
                      </p>
                    ) : null}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="mt-8 space-y-8 md:hidden">
        {comparison.dimensions.map((row) => (
          <section key={row.category}>
            <h2 className="font-serif text-xl">{row.category.replaceAll("_", " ")}</h2>
            <dl className="mt-3 space-y-4">
              {row.cells.map((cell) => {
                const company = comparison.companies.find((item) => item.slug === cell.slug);
                return (
                  <div key={cell.slug} className="border border-[var(--rule)] p-4">
                    <dt className="font-sans text-sm">{company?.name ?? cell.slug}</dt>
                    <dd className="mt-2">
                      {cellCopy(cell)}
                      {cell.state === "found" ? (
                        <p className="mt-2">
                          <a
                            className="font-sans text-sm underline"
                            href={`/compare/evidence?slug=${cell.slug}&claim=${cell.claim_key}&companies=${slugs.join(",")}`}
                          >
                            Open evidence
                          </a>
                        </p>
                      ) : null}
                    </dd>
                  </div>
                );
              })}
            </dl>
          </section>
        ))}
      </div>
    </>
  );
}

export default async function ComparePage({
  searchParams,
}: {
  searchParams: Promise<{ companies?: string; c?: string | string[] }>;
}) {
  const query = await searchParams;
  const { slugs, truncated } = parseCompanySlugs(query.companies ?? query.c);
  const catalog = await loadCompanies();
  const comparison = await loadComparison(slugs, truncated);
  if (slugs.length >= 2) {
    await recordCompareEvent("compare_start");
    if (comparison.status === "comparable") {
      await recordCompareEvent("compare_complete");
    }
  }

  return (
    <main id="main" className="mx-auto max-w-5xl px-6 py-12">
      <h1 className="font-serif text-4xl tracking-tight">Compare companies</h1>
      <p className="mt-3 max-w-2xl text-[var(--muted)]">
        Side-by-side published disclosures. This is not a privacy score and not
        legal advice. Unknown stays unknown.
      </p>
      <form action="/compare/select" method="post" className="mt-8">
        <fieldset>
          <legend className="font-sans text-sm">Select 2 to 4 companies</legend>
          {!catalog.ok ? (
            <StatePanel title="Catalog unavailable">
              We could not load companies to compare.
            </StatePanel>
          ) : (
            <ul className="mt-3 columns-1 gap-4 sm:columns-2">
              {catalog.data.map((company) => (
                <li key={company.slug} className="break-inside-avoid">
                  <label className="inline-flex min-h-11 items-center gap-2 font-sans text-sm">
                    <input
                      type="checkbox"
                      name="c"
                      value={company.slug}
                      defaultChecked={slugs.includes(company.slug)}
                    />
                    {company.name}
                  </label>
                </li>
              ))}
            </ul>
          )}
        </fieldset>
        <button
          type="submit"
          className="mt-4 min-h-11 border border-[var(--ink)] px-4 font-sans text-sm"
        >
          Compare
        </button>
      </form>
      {truncated ? (
        <p className="mt-4" role="status">
          Comparisons use at most four companies. Extra selections were dropped.
        </p>
      ) : null}
      {comparison.status === "need_selection" ? (
        <p className="mt-8 text-[var(--muted)]">
          Choose at least two companies. An empty comparison is not a finding.
        </p>
      ) : null}
      {comparison.region_mismatch ? (
        <p className="mt-6 border border-[var(--warning)] p-4" role="status">
          These sources use different regions. That is not a like-for-like
          comparison.
        </p>
      ) : null}
      {comparison.status === "not_comparable" ? (
        <StatePanel title="Not comparable">
          These companies were published under different taxonomy versions. We
          do not blend them into one matrix.
        </StatePanel>
      ) : null}
      {comparison.status === "comparable" ? (
        <>
          <p className="mt-6 font-sans text-sm text-[var(--muted)]">
            Shareable URL: {canonicalComparePath(slugs)}
          </p>
          <ComparisonMatrix comparison={comparison} slugs={slugs} />
        </>
      ) : null}
    </main>
  );
}
