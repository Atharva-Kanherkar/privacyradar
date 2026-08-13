import Link from "next/link";
import { notFound } from "next/navigation";
import { getCompany } from "@/lib/db";

export const dynamic = "force-dynamic";

type Practice = {
  party: string;
  data_types: string[];
  purposes: string[];
  third_parties: string[];
  retention: string;
  user_control: string;
  quotes: { text: string; section: string }[];
};

export default async function CompanyPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const data = await getCompany(slug);
  if (!data) notFound();

  const { company, events, extraction } = data;
  const practices = (extraction?.practices as { practices?: Practice[] } | null)
    ?.practices;

  return (
    <main className="mx-auto max-w-5xl px-6 py-12">
      <p className="text-sm text-[var(--muted)]">
        <Link href="/companies" className="hover:underline">
          Catalog
        </Link>
        <span className="mx-2">/</span>
        {company.category}
      </p>
      <h1 className="mt-2 font-serif text-4xl tracking-tight">{company.name}</h1>
      <p className="mt-3 text-sm text-[var(--muted)]">
        {company.privacy_url ? (
          <a href={company.privacy_url} className="underline" rel="noreferrer">
            Current privacy policy
          </a>
        ) : (
          "No privacy URL"
        )}
        {company.last_verified_at && (
          <span className="ml-3 font-mono text-xs">
            last verified {new Date(company.last_verified_at).toLocaleString()}
          </span>
        )}
      </p>

      <h2 className="mt-12 text-xl">What they take</h2>
      {!practices?.length ? (
        <p className="mt-3 text-[var(--muted)]">
          No extraction yet. The next successful analysis crawl fills this.
        </p>
      ) : (
        <ul className="mt-4 space-y-6">
          {practices.map((p, i) => (
            <li key={i} className="border border-[var(--rule)] bg-[var(--card)] p-5">
              <p className="font-mono text-xs uppercase tracking-wide text-[var(--muted)]">
                {p.party}-party · {p.purposes.join(", ")}
              </p>
              <p className="mt-2 text-lg">{p.data_types.join(", ")}</p>
              {p.third_parties.length > 0 && (
                <p className="mt-1 text-sm text-[var(--muted)]">
                  Shared with {p.third_parties.join(", ")}
                </p>
              )}
              <p className="mt-1 text-sm text-[var(--muted)]">
                Retention: {p.retention}. Control: {p.user_control}.
              </p>
              {p.quotes[0] && (
                <blockquote className="mt-3 border-l-2 border-[var(--material)] pl-3 text-sm italic text-[var(--muted)]">
                  “{p.quotes[0].text}”
                  <span className="not-italic"> - {p.quotes[0].section}</span>
                </blockquote>
              )}
            </li>
          ))}
        </ul>
      )}

      <h2 className="mt-12 text-xl">Changes</h2>
      {events.length === 0 ? (
        <p className="mt-3 text-[var(--muted)]">No diffs recorded yet.</p>
      ) : (
        <ol className="mt-4 divide-y divide-[var(--rule)] border-y border-[var(--rule)]">
          {events.map((event) => (
            <li key={event.id} className="py-5">
              <p className="text-xs font-mono text-[var(--muted)]">
                {event.materiality} · {new Date(event.published_at).toLocaleString()}
              </p>
              <p className="mt-1 text-lg">{event.headline}</p>
              <p className="mt-2 text-sm text-[var(--muted)]">{event.summary}</p>
            </li>
          ))}
        </ol>
      )}
    </main>
  );
}
