import Link from "next/link";
import { BellRing, FileSearch, Quote } from "lucide-react";
import { ChangeCard } from "@/components/ChangeCard";
import { CompanyCard } from "@/components/CompanyCard";
import { SearchForm } from "@/components/SearchForm";
import { StatePanel } from "@/components/StatePanel";
import { loadCompanies, loadEvents, mapCompanyDataTypes } from "@/lib/db";

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

export default async function Home() {
  const [events, companies, dataTypes] = await Promise.all([
    loadEvents(6),
    loadCompanies(),
    mapCompanyDataTypes().catch(() => new Map<string, string[]>()),
  ]);

  return (
    <main id="main" className="mx-auto max-w-6xl overflow-x-hidden px-6 py-14">
      <section className="mx-auto max-w-3xl text-center">
        <p className="inline-flex items-center rounded-full bg-[var(--accent-soft)] px-3 py-1 text-xs font-semibold uppercase tracking-wide text-[var(--accent)]">
          Evidence-backed policy watch
        </p>
        <h1 className="mt-4 text-4xl font-semibold leading-tight tracking-tight sm:text-5xl">
          What do the services you use disclose about your data?
        </h1>
        <p className="mx-auto mt-4 max-w-xl text-lg text-[var(--muted)]">
          Your voice. Your location. Your messages. See exactly what each
          company says it takes, with the receipts, and get told when it
          changes.
        </p>
        <div className="mx-auto mt-6 flex max-w-xl justify-center">
          <SearchForm label="Search a company" />
        </div>
      </section>

      <section aria-label="How it works" className="mt-16 grid gap-4 sm:grid-cols-3">
        {STEPS.map((step) => (
          <div
            key={step.title}
            className="rounded-2xl border border-[var(--rule)] bg-[var(--surface)] p-5"
          >
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-[var(--accent-soft)] text-[var(--accent)]">
              <step.icon size={18} aria-hidden="true" />
            </span>
            <h2 className="mt-3 text-base font-semibold">{step.title}</h2>
            <p className="mt-1 text-sm text-[var(--muted)]">{step.text}</p>
          </div>
        ))}
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
                dataTypes={dataTypes.get(company.id) ?? []}
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
    </main>
  );
}
