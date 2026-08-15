import Link from "next/link";
import { ArrowRight, BellRing, FileSearch, Quote } from "lucide-react";
import { ChangeCard } from "@/components/ChangeCard";
import { CompanyCard } from "@/components/CompanyCard";
import { CompanyLogo } from "@/components/CompanyLogo";
import { DataTypeIcon } from "@/components/DataTypeIcon";
import { SearchForm } from "@/components/SearchForm";
import { StatePanel } from "@/components/StatePanel";
import { attributeMeta, SENSITIVE } from "@/lib/data-categories";
import {
  getCatalogStats,
  getSpotlightClaim,
  loadCompanies,
  loadEvents,
  mapCompanyDataTypes,
} from "@/lib/db";

export const dynamic = "force-dynamic";

const STEPS = [
  {
    icon: FileSearch,
    title: "We read the policies",
    text: "PrivacyRadar captures each company's privacy policy and checks it for changes several times a day.",
  },
  {
    icon: Quote,
    title: "Every claim has a receipt",
    text: "Nothing is published without the exact quote from the policy. No scores, no guesses.",
  },
  {
    icon: BellRing,
    title: "You hear when it changes",
    text: "Watch a company and get alerted the moment its policy materially changes.",
  },
];

const QUICK_SLUGS = ["google", "meta", "amazon", "spotify"];

export default async function Home() {
  const [events, companies, dataTypes, spotlight, stats] = await Promise.all([
    loadEvents(6),
    loadCompanies(),
    // null = lookup failed; cards must say "unavailable", not "nothing found".
    mapCompanyDataTypes().catch(() => null),
    getSpotlightClaim(),
    getCatalogStats(),
  ]);

  const quickLinks = companies.ok
    ? QUICK_SLUGS.map((slug) =>
        companies.data.find((company) => company.slug === slug),
      ).filter((company) => company !== undefined)
    : [];
  const spotlightMeta = spotlight
    ? attributeMeta(
        spotlight.attribute in SENSITIVE ? "sensitive" : "data_collected",
        spotlight.attribute,
      )
    : null;

  return (
    <main id="main" className="mx-auto max-w-6xl overflow-x-hidden px-6 py-14">
      <section className="grid items-center gap-10 lg:grid-cols-[1.15fr_1fr]">
        <div>
          <h1 className="text-[clamp(2.25rem,1.4rem+2.8vw,3.4rem)] font-semibold leading-[1.08] tracking-tight">
            What do the services you use disclose about your data?
          </h1>
          <p className="mt-4 max-w-xl text-lg text-[var(--muted)]">
            Your voice. Your location. Your messages. See exactly what each
            company says it takes, straight from its own privacy policy.
          </p>
          <SearchForm label="Search a company" />
          {quickLinks.length > 0 ? (
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <span className="text-sm text-[var(--muted)]">Try:</span>
              {quickLinks.map((company) => (
                <Link
                  key={company.slug}
                  href={`/companies/${company.slug}`}
                  className="inline-flex min-h-10 items-center gap-2 rounded-full border border-[var(--rule)] bg-[var(--surface)] py-1 pl-1.5 pr-3.5 text-sm font-medium transition-colors hover:border-[var(--accent)]"
                >
                  <CompanyLogo
                    name={company.name}
                    website={company.website}
                    size={28}
                    className="rounded-full"
                  />
                  {company.name}
                </Link>
              ))}
            </div>
          ) : null}
          {stats ? (
            <p className="tabular mt-6 text-sm text-[var(--muted)]">
              <strong className="font-semibold text-[var(--ink)]">
                {stats.companies} companies
              </strong>{" "}
              watched ·{" "}
              <strong className="font-semibold text-[var(--ink)]">
                {stats.claims} disclosures
              </strong>{" "}
              published, every one backed by a quote
            </p>
          ) : null}
        </div>

        {spotlight && spotlightMeta ? (
          <Link
            href={`/companies/${spotlight.slug}`}
            className="group relative rounded-2xl border border-[var(--rule)] bg-[var(--surface)] p-6 transition-all hover:-translate-y-0.5 hover:border-[var(--accent)]"
          >
            <div className="flex items-center gap-3">
              <CompanyLogo
                name={spotlight.name}
                website={spotlight.website}
                size={44}
              />
              <div>
                <p className="text-lg font-semibold leading-tight">
                  {spotlight.name}
                </p>
                <p className="flex items-center gap-1.5 text-sm text-[var(--danger)]">
                  <DataTypeIcon attribute={spotlight.attribute} size={14} />
                  {spotlightMeta.label}
                </p>
              </div>
            </div>
            <figure className="mt-4">
              <blockquote className="border-l border-[var(--accent)] pl-3 text-sm italic leading-relaxed text-[var(--muted)]">
                &ldquo;{spotlight.quote}&rdquo;
              </blockquote>
              <figcaption className="mt-2 pl-3 text-xs text-[var(--muted)]">
                From {spotlight.name}&rsquo;s captured privacy policy, word for word
              </figcaption>
            </figure>
            <p className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-[var(--accent)]">
              See everything {spotlight.name} takes
              <ArrowRight
                size={15}
                aria-hidden="true"
                className="transition-transform group-hover:translate-x-0.5"
              />
            </p>
          </Link>
        ) : null}
      </section>

      <section className="mt-16">
        <div className="flex items-baseline justify-between">
          <h2 className="text-2xl font-semibold tracking-tight">
            Companies we watch
          </h2>
          <Link
            href="/companies"
            className="text-sm font-medium text-[var(--accent)] hover:underline"
          >
            See all
          </Link>
        </div>
        {!companies.ok ? (
          <StatePanel title="Catalog unavailable">
            We could not load companies. A missing database is not an empty catalog.
          </StatePanel>
        ) : (
          <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {companies.data.map((company) => (
              <CompanyCard
                key={company.id}
                company={company}
                dataTypes={dataTypes ? (dataTypes.get(company.id) ?? []) : null}
              />
            ))}
          </div>
        )}
      </section>

      <section className="mt-16">
        <h2 className="text-2xl font-semibold tracking-tight">
          Important recent changes
        </h2>
        {!events.ok ? (
          <StatePanel title="Change feed unavailable">
            We could not load published changes. This is not an empty policy catalog.
          </StatePanel>
        ) : events.data.length === 0 ? (
          <p className="mt-4 text-sm text-[var(--muted)]">
            No published material changes yet. The companies above are the
            current inventory.
          </p>
        ) : (
          <ol className="mt-5 space-y-4">
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
      </section>

      <section
        aria-label="How it works"
        className="mt-16 grid gap-8 border-t border-[var(--rule)] pt-8 sm:grid-cols-3"
      >
        {STEPS.map((step) => (
          <div key={step.title}>
            <h2 className="flex items-center gap-2 text-base font-semibold">
              <step.icon
                size={16}
                aria-hidden="true"
                className="text-[var(--accent)]"
              />
              {step.title}
            </h2>
            <p className="mt-1.5 text-sm text-[var(--muted)]">{step.text}</p>
          </div>
        ))}
      </section>
    </main>
  );
}
