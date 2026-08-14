import Link from "next/link";
import { FreshnessLabel } from "@/components/FreshnessLabel";
import { SearchForm } from "@/components/SearchForm";
import { StatePanel } from "@/components/StatePanel";
import { loadCompanies } from "@/lib/db";

export const dynamic = "force-dynamic";

export default async function CompaniesPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string }>;
}) {
  const { q } = await searchParams;
  const result = await loadCompanies(q);

  return (
    <main id="main" className="mx-auto max-w-5xl px-6 py-12">
      <h1 className="font-serif text-4xl tracking-tight">Catalog</h1>
      <p className="mt-3 max-w-xl text-[var(--muted)]">
        Hand-picked properties. Each row is a known privacy-policy URL, not a
        guessed sitemap crawl.{" "}
        <Link href="/companies/request" className="underline">
          Request a company
        </Link>
        — nominations are requested, not monitored.
      </p>
      <SearchForm defaultQuery={q ?? ""} label="Filter companies" />
      {!result.ok ? (
        <StatePanel title="Catalog unavailable">
          We could not load companies. This is not an empty catalog.
        </StatePanel>
      ) : result.data.length === 0 ? (
        <p className="mt-8 text-[var(--muted)]">
          We have not found a matching company. Try another name, or browse from
          the home page.
        </p>
      ) : (
        <table className="mt-10 w-full border-collapse text-left text-sm">
          <thead>
            <tr className="border-b border-[var(--rule)] text-[var(--muted)]">
              <th className="py-2 font-normal">Company</th>
              <th className="py-2 font-normal">Category</th>
              <th className="py-2 font-normal">Region</th>
              <th className="py-2 font-normal">Freshness</th>
            </tr>
          </thead>
          <tbody>
            {result.data.map((c) => (
              <tr key={c.id} className="border-b border-[var(--rule)]">
                <td className="py-3">
                  <Link href={`/companies/${c.slug}`} className="hover:underline">
                    {c.name}
                  </Link>
                </td>
                <td className="py-3 text-[var(--muted)]">{c.category}</td>
                <td className="py-3 text-[var(--muted)]">{c.region ?? "not labeled"}</td>
                <td className="py-3">
                  <FreshnessLabel
                    lastCheckedAt={c.last_verified_at}
                    health={c.source_health}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
}
