import Link from "next/link";
import { ChangeCard } from "@/components/ChangeCard";
import { SearchForm } from "@/components/SearchForm";
import { StatePanel } from "@/components/StatePanel";
import { loadCompanies, loadEvents } from "@/lib/db";

export const dynamic = "force-dynamic";

export default async function Home() {
  const [events, companies] = await Promise.all([loadEvents(), loadCompanies()]);

  return (
    <main id="main" className="mx-auto max-w-5xl overflow-x-hidden px-6 py-12">
      <p className="font-sans text-sm uppercase tracking-[0.18em] text-[var(--muted)]">
        Evidence-backed policy watch
      </p>
      <h1 className="mt-2 max-w-2xl font-serif text-4xl leading-tight tracking-tight">
        What do the services you use disclose about your data?
      </h1>
      <p className="mt-4 max-w-xl text-[var(--muted)]">
        Search a company, read disclosed practices with quotes, and see what
        just changed. Dated. Correctable. Not a privacy score.
      </p>
      <SearchForm label="Search a company" />

      <h2 className="mt-14 font-serif text-2xl">Important recent changes</h2>
      {!events.ok ? (
        <StatePanel title="Change feed unavailable">
          We could not load published changes. This is not an empty policy catalog.
        </StatePanel>
      ) : events.data.length === 0 ? (
        <p className="mt-4 font-sans text-sm text-[var(--muted)]">
          No published material changes yet. The catalog below is the current
          inventory.
        </p>
      ) : (
        <ol className="mt-4 divide-y divide-[var(--rule)] border-y border-[var(--rule)]">
          {events.data.map((event) => (
            <li key={event.id}>
              <ChangeCard
                id={event.id}
                companyName={event.name}
                companySlug={event.slug}
                headline={event.headline}
                summary={event.summary}
                materiality={event.materiality}
                publishedAt={event.published_at}
              />
            </li>
          ))}
        </ol>
      )}

      <h2 className="mt-14 font-serif text-2xl">Catalog</h2>
      {!companies.ok ? (
        <StatePanel title="Catalog unavailable">
          We could not load companies. A missing database is not an empty catalog.
        </StatePanel>
      ) : (
        <ul className="mt-4 divide-y divide-[var(--rule)] border-y border-[var(--rule)]">
          {companies.data.map((c) => (
            <li key={c.id} className="flex flex-wrap items-baseline justify-between gap-3 py-4">
              <Link href={`/companies/${c.slug}`} className="text-lg hover:underline">
                {c.name}
              </Link>
              <span className="font-sans text-sm text-[var(--muted)]">{c.category}</span>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
