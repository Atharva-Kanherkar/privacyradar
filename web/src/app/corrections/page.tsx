import Link from "next/link";
import { StatePanel } from "@/components/StatePanel";
import { loadPublicCorrections } from "@/lib/db";

export const dynamic = "force-dynamic";

export default async function CorrectionsPage() {
  const result = await loadPublicCorrections();
  return (
    <main id="main" className="mx-auto max-w-5xl px-6 py-12">
      <h1 className="font-serif text-4xl tracking-tight">Corrections</h1>
      <p className="mt-3 max-w-xl text-[var(--muted)]">
        Public history of corrected or declined reports. Prior publication
        revisions are not deleted.
      </p>
      {!result.ok ? (
        <StatePanel title="Corrections unavailable">
          We could not load correction history.
        </StatePanel>
      ) : result.data.length === 0 ? (
        <p className="mt-8 text-[var(--muted)]">No public corrections yet.</p>
      ) : (
        <ol className="mt-8 divide-y divide-[var(--rule)] border-y border-[var(--rule)]">
          {result.data.map((row) => (
            <li key={row.id} className="py-5">
              <p className="font-sans text-sm text-[var(--muted)]">
                <Link href={`/companies/${row.company_slug}`} className="hover:underline">
                  {row.company_name}
                </Link>
                <span className="mx-2">·</span>
                {row.state}
              </p>
              <p className="mt-2">{row.public_note}</p>
            </li>
          ))}
        </ol>
      )}
    </main>
  );
}
