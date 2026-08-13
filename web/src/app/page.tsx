import Link from "next/link";
import { listCompanies, listEvents } from "@/lib/db";

export const dynamic = "force-dynamic";

function formatWhen(iso: string) {
  return new Date(iso).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default async function Home() {
  const [events, companies] = await Promise.all([listEvents(), listCompanies()]);
  const watching = companies.filter((c) => c.last_hash);

  return (
    <main className="mx-auto max-w-5xl px-6 py-12">
      <p className="text-sm uppercase tracking-[0.18em] text-[var(--muted)]">
        Live change feed
      </p>
      <h1 className="mt-2 max-w-2xl font-serif text-4xl leading-tight tracking-tight">
        What they take. What just changed.
      </h1>
      <p className="mt-4 max-w-xl text-[var(--muted)]">
        privacyradar watches a fixed catalog of company privacy policies, hashes
        the cleaned text, and only then asks a model what data moved. Cosmetic
        date-stamp emails never make this page.
      </p>

      {events.length === 0 ? (
        <p className="mt-12 text-sm text-[var(--muted)]">
          No material diffs yet. Baselines below are the current inventory.
          This feed fills when a later crawl finds a real change.
        </p>
      ) : (
        <ol className="mt-12 divide-y divide-[var(--rule)] border-y border-[var(--rule)]">
          {events.map((event) => (
            <li key={event.id} className="py-8">
              <div className="flex flex-wrap items-baseline justify-between gap-3 text-sm text-[var(--muted)]">
                <Link href={`/companies/${event.slug}`} className="hover:underline">
                  {event.name}
                </Link>
                <time dateTime={event.published_at}>{formatWhen(event.published_at)}</time>
              </div>
              <h2 className="mt-2 text-2xl leading-snug">
                <Link href={`/companies/${event.slug}`}>{event.headline}</Link>
              </h2>
              <p className="mt-3 max-w-2xl text-[var(--muted)]">{event.summary}</p>
              {(event.data_types_added.length > 0 ||
                event.data_types_removed.length > 0) && (
                <p className="mt-3 font-mono text-xs text-[var(--material)]">
                  {event.data_types_added.length > 0 && (
                    <span>+ {event.data_types_added.join(", ")}</span>
                  )}
                  {event.data_types_removed.length > 0 && (
                    <span className="ml-3">− {event.data_types_removed.join(", ")}</span>
                  )}
                </p>
              )}
            </li>
          ))}
        </ol>
      )}

      {watching.length > 0 && (
        <section className="mt-16">
          <h2 className="text-xl">Currently watching</h2>
          <ol className="mt-4 divide-y divide-[var(--rule)] border-y border-[var(--rule)]">
            {watching.map((c) => (
              <li key={c.id} className="py-5">
                <div className="flex flex-wrap items-baseline justify-between gap-3">
                  <Link href={`/companies/${c.slug}`} className="text-lg hover:underline">
                    {c.name}
                  </Link>
                  <span className="font-mono text-xs text-[var(--muted)]">
                    {c.last_verified_at
                      ? formatWhen(c.last_verified_at)
                      : "queued"}
                  </span>
                </div>
                <p className="mt-2 text-sm text-[var(--muted)]">
                  {c.data_types.length > 0
                    ? c.data_types.join(" · ")
                    : c.current_snapshot_id
                      ? "Hashed. Extraction pending."
                      : "Not yet verified."}
                </p>
                {(c.source_health === "degraded" ||
                  c.source_health === "quarantined") && (
                  <p className="mt-1 text-sm text-[var(--muted)]">
                    Check delayed. Last verified observation is unchanged.
                  </p>
                )}
              </li>
            ))}
          </ol>
        </section>
      )}
    </main>
  );
}
