import type { Metadata } from "next";
import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { ChangeCard } from "@/components/ChangeCard";
import { ChatAssistant } from "@/components/ChatAssistant";
import { ClaimCard } from "@/components/ClaimCard";
import { CompanyLogo } from "@/components/CompanyLogo";
import { DisclosureRow } from "@/components/DisclosureRow";
import { FreshnessLabel } from "@/components/FreshnessLabel";
import { StatePanel } from "@/components/StatePanel";
import { WatchButton } from "@/components/WatchButton";
import { assistantEnabled } from "@/lib/assistant";
import { loadCompany, type PublishedClaimRow } from "@/lib/db";
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
    title: `What data ${result.data.company.name} collects`,
    description: `See exactly what ${result.data.company.name} says it collects about you, with the exact policy quotes.`,
    alternates: { canonical: `/companies/${slug}` },
  };
}

function bySeverity(a: PublishedClaimRow, b: PublishedClaimRow): number {
  const rank = (claim: PublishedClaimRow) =>
    claim.category === "sensitive" ? 0 : claim.polarity === "disclosed" ? 1 : 2;
  const diff = rank(a) - rank(b);
  return diff !== 0 ? diff : a.attribute.localeCompare(b.attribute);
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
      <main id="main" className="mx-auto max-w-6xl px-6 py-12">
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

  const collectionClaims = claims.filter(
    (claim) =>
      (claim.category === "data_collected" || claim.category === "sensitive") &&
      claim.attribute !== "none_disclosed",
  );
  const collected = collectionClaims
    .filter((claim) => claim.polarity === "disclosed")
    .sort(bySeverity);
  // "We do not collect X" and unclear claims must not sit under a heading
  // that says the company takes them.
  const notCollected = collectionClaims
    .filter((claim) => claim.polarity !== "disclosed")
    .sort(bySeverity);
  const purposes = claims
    .filter((claim) => claim.category === "purpose" && claim.polarity === "disclosed")
    .sort(bySeverity);
  const practices = claims
    .filter(
      (claim) =>
        claim.category === "sharing" ||
        claim.category === "retention" ||
        claim.category === "control",
    )
    .sort(bySeverity);
  const chatOn = assistantEnabled();

  return (
    <main id="main" className="mx-auto max-w-6xl px-6 py-12">
      <p className="text-sm text-[var(--muted)]">
        <Link href="/companies" className="hover:underline">
          Companies
        </Link>
        <span className="mx-2">/</span>
        {company.category}
      </p>
      <div className="mt-3 flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-start gap-4">
          <CompanyLogo
            name={company.name}
            website={company.website}
            size={56}
            className="mt-1"
          />
          <div>
            <h1 className="text-4xl font-semibold tracking-tight">{company.name}</h1>
            <p className="mt-2 text-sm text-[var(--muted)]">
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
            <FreshnessLabel
              lastCheckedAt={company.last_verified_at}
              health={company.source_health}
            />
            </p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <WatchButton
            slug={company.slug}
            signedIn={Boolean(session?.user)}
            watching={watching}
          />
          <Link
            href={`/compare?companies=${company.slug}`}
            className="inline-flex min-h-11 items-center rounded-full border border-[var(--rule)] bg-[var(--surface)] px-5 text-sm font-medium hover:border-[var(--accent)]"
          >
            Compare
          </Link>
        </div>
      </div>

      <section className="mt-12">
        <h2 className="max-w-3xl text-[1.75rem] font-semibold leading-snug tracking-tight">
          What {company.name} takes from you.{" "}
          <span className="lede-muted font-medium">
            Straight from the captured policy. Tap any row for the exact quote.
          </span>
        </h2>
        {collected.length === 0 ? (
          <p className="mt-4 max-w-xl text-[var(--muted)]">
            {company.current_snapshot_id
              ? "We have not found published evidence yet. Unpublished model output is not shown."
              : "Not yet checked. A missing or failed fetch is not an empty policy."}
          </p>
        ) : (
          <div className="mt-5 grid gap-3 sm:grid-cols-2">
            {collected.map((claim) => (
              <ClaimCard key={claim.claim_key} claim={claim} />
            ))}
          </div>
        )}
      </section>

      {notCollected.length > 0 ? (
        <section className="mt-12">
          <h2 className="max-w-3xl text-[1.75rem] font-semibold leading-snug tracking-tight">
            What the policy denies or leaves unclear.
          </h2>
          <div className="mt-5 grid gap-3 sm:grid-cols-2">
            {notCollected.map((claim) => (
              <ClaimCard key={claim.claim_key} claim={claim} />
            ))}
          </div>
        </section>
      ) : null}

      {purposes.length > 0 ? (
        <section className="mt-12">
          <h2 className="max-w-3xl text-[1.75rem] font-semibold leading-snug tracking-tight">
            Why they use your data.
          </h2>
          <div className="mt-5 grid gap-3 sm:grid-cols-2">
            {purposes.map((claim) => (
              <ClaimCard key={claim.claim_key} claim={claim} />
            ))}
          </div>
        </section>
      ) : null}

      {practices.length > 0 ? (
        <section className="mt-12">
          <h2 className="max-w-3xl text-[1.75rem] font-semibold leading-snug tracking-tight">
            Sharing, retention &amp; your controls.
          </h2>
          <div className="mt-5 grid gap-3 sm:grid-cols-2">
            {practices.map((claim) => (
              <ClaimCard key={claim.claim_key} claim={claim} />
            ))}
          </div>
        </section>
      ) : null}

      <section className="mt-12">
        <h2 className="max-w-3xl text-[1.75rem] font-semibold leading-snug tracking-tight">
          What changed.
        </h2>
        {events.length === 0 ? (
          <p className="mt-3 text-[var(--muted)]">No published changes yet.</p>
        ) : (
          <ol className="mt-5 space-y-4">
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
      </section>

      {claims.length > 0 ? (
        <details className="mt-12 rounded-2xl border border-[var(--rule)] bg-[var(--surface)] p-5">
          <summary className="min-h-11 cursor-pointer text-sm font-medium">
            Full evidence record ({claims.length} published claims)
          </summary>
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
        </details>
      ) : null}

      <p className="mt-8 text-sm">
        <Link href="/corrections" className="underline">
          Public correction history
        </Link>
      </p>

      {chatOn ? (
        <ChatAssistant slug={company.slug} companyName={company.name} />
      ) : (
        <section className="mt-12 rounded-2xl border border-[var(--rule)] bg-[var(--surface)] p-5">
          <h2 className="text-base font-semibold">Ask about this policy</h2>
          <p className="mt-2 text-sm text-[var(--muted)]">
            The cited assistant is off. Read the published disclosures above.
            This is not legal advice.
          </p>
        </section>
      )}
    </main>
  );
}
