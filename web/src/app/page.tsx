import Link from "next/link";
import { ArrowRight, BellRing, FileSearch, Quote } from "lucide-react";
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
  const [companies, dataTypes, spotlight, stats] = await Promise.all([
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
    <main id="main" className="relative mx-auto max-w-6xl overflow-x-clip px-6 py-20">
      <section className="grid items-center gap-12 lg:grid-cols-[1.2fr_1fr]">
        <div>
          <h1 className="max-w-2xl text-[clamp(2.5rem,1.6rem+3.4vw,4.25rem)] font-semibold leading-[1.06] tracking-[-0.03em]">
            What do the services you use{" "}
            <span className="lede-muted">disclose about your data?</span>
          </h1>
          <p className="mt-6 max-w-xl text-xl leading-relaxed text-muted-foreground">
            Your voice. Your location. Your messages. See exactly what each
            company says it takes, straight from its own privacy policy.
          </p>
          <SearchForm label="Search a company" />
          {quickLinks.length > 0 ? (
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <span className="text-sm text-muted-foreground">Try:</span>
              {quickLinks.map((company) => (
                <Link
                  key={company.slug}
                  href={`/companies/${company.slug}`}
                  className="inline-flex min-h-10 items-center gap-2 rounded-md border border-border bg-card py-1 pl-1.5 pr-3.5 text-sm font-medium transition-colors hover:border-foreground"
                >
                  <CompanyLogo
                    name={company.name}
                    website={company.website}
                    size={28}
                    className="rounded-sm"
                  />
                  {company.name}
                </Link>
              ))}
            </div>
          ) : null}
        </div>

        {spotlight && spotlightMeta ? (
          <Link
            href={`/companies/${spotlight.slug}`}
            className="group relative rounded-xl border border-border bg-card p-6 transition-all hover:-translate-y-0.5 hover:border-foreground"
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
              <blockquote className="border-l border-foreground pl-3 text-sm italic leading-relaxed text-muted-foreground">
                &ldquo;{spotlight.quote}&rdquo;
              </blockquote>
              <figcaption className="mt-2 pl-3 text-xs text-muted-foreground">
                From {spotlight.name}&rsquo;s captured privacy policy, word for word
              </figcaption>
            </figure>
            <p className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-foreground">
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

      {stats ? (
        <section
          aria-label="Coverage"
          className="tabular mt-20 grid grid-cols-2 gap-x-8 gap-y-10 border-y border-border py-12 lg:grid-cols-4"
        >
          <div>
            <p className="text-4xl font-light tracking-tight text-foreground">
              {stats.companies}
            </p>
            <p className="mt-2 text-sm text-muted-foreground">
              companies under continuous watch
            </p>
          </div>
          <div>
            <p className="text-4xl font-light tracking-tight text-foreground">
              {stats.claims}
            </p>
            <p className="mt-2 text-sm text-muted-foreground">
              disclosures published from captured policies
            </p>
          </div>
          <div>
            <p className="text-4xl font-light tracking-tight text-foreground">
              4<span className="text-2xl">×</span>
            </p>
            <p className="mt-2 text-sm text-muted-foreground">
              policy checks per day, every company
            </p>
          </div>
          <div>
            <p className="text-4xl font-light tracking-tight text-foreground">
              100%
            </p>
            <p className="mt-2 text-sm text-muted-foreground">
              of claims carry the exact policy quote
            </p>
          </div>
        </section>
      ) : null}

      <section className="mt-20">
        <div className="flex items-end justify-between gap-6">
          <h2 className="max-w-3xl text-[1.75rem] font-semibold leading-snug tracking-tight">
            Companies we watch.{" "}
            <span className="lede-muted font-medium">
              Each card shows what the policy discloses it collects.
            </span>
          </h2>
          <Link
            href="/companies"
            className="shrink-0 text-sm font-medium text-foreground hover:underline"
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


      <section
        aria-label="How it works"
        className="mt-20 grid gap-8 border-t border-border pt-10 sm:grid-cols-3"
      >
        {STEPS.map((step) => (
          <div key={step.title}>
            <h2 className="flex items-center gap-2 text-base font-semibold">
              <step.icon
                size={16}
                aria-hidden="true"
                className="text-foreground"
              />
              {step.title}
            </h2>
            <p className="mt-1.5 text-sm text-muted-foreground">{step.text}</p>
          </div>
        ))}
      </section>
    </main>
  );
}
