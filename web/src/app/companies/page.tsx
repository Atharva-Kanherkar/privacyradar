import Link from "next/link";
import { listCompanies } from "@/lib/db";

export const dynamic = "force-dynamic";

export default async function CompaniesPage() {
  const companies = await listCompanies();

  return (
    <main className="mx-auto max-w-5xl px-6 py-12">
      <h1 className="font-serif text-4xl tracking-tight">Catalog</h1>
      <p className="mt-3 max-w-xl text-[var(--muted)]">
        Hand-picked properties. Each row is a known privacy-policy URL, not a
        guessed sitemap crawl.
      </p>
      <table className="mt-10 w-full border-collapse text-left text-sm">
        <thead>
          <tr className="border-b border-[var(--rule)] text-[var(--muted)]">
            <th className="py-2 font-normal">Company</th>
            <th className="py-2 font-normal">Category</th>
            <th className="py-2 font-normal">Last fetch</th>
            <th className="py-2 font-normal">Status</th>
          </tr>
        </thead>
        <tbody>
          {companies.map((c) => (
            <tr key={c.id} className="border-b border-[var(--rule)]">
              <td className="py-3">
                <Link href={`/companies/${c.slug}`} className="hover:underline">
                  {c.name}
                </Link>
              </td>
              <td className="py-3 text-[var(--muted)]">{c.category}</td>
              <td className="py-3 font-mono text-xs text-[var(--muted)]">
                {c.last_fetched
                  ? new Date(c.last_fetched).toLocaleDateString()
                  : "never"}
              </td>
              <td className="py-3 text-[var(--muted)]">
                {c.last_error ? c.last_error : c.last_hash ? "hashed" : "queued"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {companies.length === 0 && (
        <p className="mt-8 text-[var(--muted)]">
          Database empty. Run <code className="mono text-[13px]">docker compose up -d</code>{" "}
          then <code className="mono text-[13px]">privacyradar seed</code>.
        </p>
      )}
    </main>
  );
}
