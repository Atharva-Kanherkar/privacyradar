import type { Metadata } from "next";
import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { ChangeCard } from "@/components/ChangeCard";
import { DisclosureRow } from "@/components/DisclosureRow";
import { FreshnessLabel } from "@/components/FreshnessLabel";
import { StatePanel } from "@/components/StatePanel";
import { WatchButton } from "@/components/WatchButton";
import { loadCompany } from "@/lib/db";
import { getSessionFromCookies } from "@/lib/session";
import { followCompany, isWatching } from "@/lib/watches";

export const dynamic = "force-dynamic";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const result = await loadCompany(slug);
  if (!result.ok || !result.data) {
    return { title: "Company" };
  }
  return {
    title: result.data.company.name,
    description: `Disclosed privacy practices for ${result.data.company.name}, with captured quotes.`,
    alternates: { canonical: `/companies/${slug}` },
  };
}

export default async function CompanyPage({
  params,
  searchParams,
}: {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ watch?: string }>;
}) {
  const { slug } = await params;
  const query = await searchParams;
  const result = await loadCompany(slug);
  if (!result.ok) {
    return (
      <main id="main" className="mx-auto max-w-5xl px-6 py-12">
        <StatePanel title="Company page unavailable">
          We could not load this company. A failed fetch is not an empty policy.
        </StatePanel>
      </main>
    );
  }
  if (!result.data) notFound();

  const session = await getSessionFromCookies();
  if (query.watch === "1" && session?.user) {
    await followCompany(session.user.id, result.data.company.id, "resume");
    redirect(`/companies/${slug}`);
  }
  const watching = session?.user
    ? await isWatching(session.user.id, result.data.company.id)
    : false;

  const { company, events, claims } = result.data;
  const glance = ["sensitive", "sharing", "purpose", "retention", "control"];
  const glanceClaims = glance
    .map((category) => claims.find((claim) => claim.category === category))
    .filter((claim) => claim !== undefined);

  return (
    <main id="main" className="mx-auto max-w-5xl px-6 py-12">
      <p className="font-sans text-sm text-[var(--muted)]">
        <Link href="/companies" className="hover:underline">
          Catalog
        </Link>
        <span className="mx-2">/</span>
        {company.category}
      </p>
      <h1 className="mt-2 font-serif text-4xl tracking-tight">{company.name}</h1>
      <div className="mt-4 flex flex-wrap gap-3">
        <WatchButton
          slug={company.slug}
          signedIn={Boolean(session?.user)}
          watching={watching}
        />
        <Link
          href={`/compare?companies=${company.slug}`}
          className="inline-flex min-h-11 items-center border border-[var(--rule)] px-4 font-sans text-sm"
        >
          Compare
        </Link>
      </div>
      <p className="mt-3 font-sans text-sm text-[var(--muted)]">
        {company.privacy_url ? (
          <a href={company.privacy_url} className="underline" rel="noreferrer">
            Current privacy policy
          </a>
        ) : (
          "No privacy URL"
        )}
        <span className="mx-2" aria-hidden="true">
          ·
        </span>
        <span>source region {company.region ?? "not labeled"}</span>
        <span className="mx-2" aria-hidden="true">
          ·
        </span>
        <FreshnessLabel
          lastCheckedAt={company.last_verified_at}
          health={company.source_health}
        />
      </p>

      <h2 className="mt-12 font-serif text-xl">At a glance</h2>
      {glanceClaims.length === 0 ? (
        <p className="mt-3 text-[var(--muted)]">
          We have not found published evidence for the five decision dimensions
          yet. That is not a claim that the company discloses nothing.
        </p>
      ) : (
        <ul className="mt-3 font-sans text-sm">
          {glanceClaims.map((claim) => (
            <li key={claim.claim_key}>
              {claim.category.replaceAll("_", " ")}: {claim.attribute.replaceAll("_", " ")}{" "}
              ({claim.polarity})
            </li>
          ))}
        </ul>
      )}

      <h2 className="mt-12 font-serif text-xl">What the company discloses</h2>
      {claims.length === 0 ? (
        <p className="mt-3 text-[var(--muted)]">
          {company.current_snapshot_id
            ? "We have not found published evidence yet. Unpublished model output is not shown."
            : "Not yet checked. A missing or failed fetch is not an empty policy."}
        </p>
      ) : (
        <ul className="mt-4 space-y-4">
          {claims.map((claim) => (
            <DisclosureRow
              key={claim.claim_key}
              claimKey={claim.claim_key}
              category={claim.category}
              attribute={claim.attribute}
              polarity={claim.polarity}
              quote={claim.quote}
              snapshotId={claim.snapshot_id}
              revisionN={claim.revision_n}
              region={company.region}
            />
          ))}
        </ul>
      )}

      <h2 className="mt-12 font-serif text-xl">What changed</h2>
      {events.length === 0 ? (
        <p className="mt-3 text-[var(--muted)]">No published changes yet.</p>
      ) : (
        <ol className="mt-4 divide-y divide-[var(--rule)] border-y border-[var(--rule)]">
          {events.map((event) => (
            <li key={event.id}>
              <ChangeCard
                id={event.id}
                companyName={company.name}
                companySlug={company.slug}
                headline={event.headline}
                summary={event.summary}
                materiality={event.materiality}
                publishedAt={event.published_at}
                corrected={event.publication_state === "corrected"}
              />
            </li>
          ))}
        </ol>
      )}

      <p className="mt-10 font-sans text-sm">
        <Link href="/corrections" className="underline">
          Public correction history
        </Link>
      </p>
    </main>
  );
}
