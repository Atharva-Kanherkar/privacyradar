import { redirect } from "next/navigation";
import Link from "next/link";
import { ChangeCard } from "@/components/ChangeCard";
import { StatePanel } from "@/components/StatePanel";
import { getSessionFromCookies } from "@/lib/session";
import {
  catalogSuggestions,
  listRadarEvents,
  listWatchedCompanies,
  recordRadarView,
} from "@/lib/watches";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export default async function RadarPage() {
  const session = await getSessionFromCookies();
  if (!session?.user) {
    redirect("/login?next=/radar");
  }
  await recordRadarView(session.user.id);
  const [events, watching, suggestions] = await Promise.all([
    listRadarEvents(session.user.id),
    listWatchedCompanies(session.user.id),
    catalogSuggestions(),
  ]);

  return (
    <main id="main" className="mx-auto max-w-5xl px-6 py-12">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <h1 className="font-serif text-4xl tracking-tight">My Radar</h1>
        <p className="font-sans text-sm">
          <Link href="/radar/watching" className="underline">
            Companies you watch
          </Link>
          <span className="mx-2" aria-hidden="true">
            ·
          </span>
          <Link href="/radar/settings" className="underline">
            Alert settings
          </Link>
          <span className="mx-2" aria-hidden="true">
            ·
          </span>
          <Link href="/companies" className="underline">
            Add companies
          </Link>
        </p>
      </div>
      <p className="mt-3 text-[var(--muted)]">
        {watching.length} watched. Only published material changes appear here.
      </p>
      {events.length === 0 ? (
        <StatePanel title="No published changes on your radar yet">
          Watch companies from the catalog. Suggestions below are grouped by
          public category, not by inferred interest.
        </StatePanel>
      ) : (
        <ol className="mt-8 divide-y divide-[var(--rule)] border-y border-[var(--rule)]">
          {events.map((event) => (
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
      {watching.length === 0 ? (
        <section className="mt-12">
          <h2 className="font-serif text-xl">Suggested companies</h2>
          <ul className="mt-4 space-y-2 font-sans text-sm">
            {suggestions.map((company) => (
              <li key={company.slug}>
                <Link href={`/companies/${company.slug}`} className="underline">
                  {company.name}
                </Link>
                <span className="text-[var(--muted)]"> · {company.category}</span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </main>
  );
}
