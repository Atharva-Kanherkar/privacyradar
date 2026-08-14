import Link from "next/link";
import { CompanyCard } from "@/components/CompanyCard";
import { SearchForm } from "@/components/SearchForm";
import { StatePanel } from "@/components/StatePanel";
import { loadCompanies, mapCompanyDataTypes } from "@/lib/db";

export const dynamic = "force-dynamic";

export default async function CompaniesPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string }>;
}) {
  const { q } = await searchParams;
  const [result, dataTypes] = await Promise.all([
    loadCompanies(q),
    // null = lookup failed; cards must say "unavailable", not "nothing found".
    mapCompanyDataTypes().catch(() => null),
  ]);

  return (
    <main id="main" className="mx-auto max-w-6xl px-6 py-12">
      <h1 className="text-4xl font-semibold tracking-tight">Catalog</h1>
      <p className="mt-3 max-w-xl text-[var(--muted)]">
        Hand-picked services. Each card shows what the company&rsquo;s own
        privacy policy discloses it collects about you.{" "}
        <Link href="/companies/request" className="underline">
          Request a company
        </Link>
        .
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
        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {result.data.map((company) => (
            <CompanyCard
              key={company.id}
              company={company}
              dataTypes={dataTypes ? (dataTypes.get(company.id) ?? []) : null}
            />
          ))}
        </div>
      )}
    </main>
  );
}
