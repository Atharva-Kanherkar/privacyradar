import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { StatePanel } from "@/components/StatePanel";
import { loadPublishedChange } from "@/lib/db";

export const dynamic = "force-dynamic";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  const result = await loadPublishedChange(id);
  if (!result.ok || !result.data) return { title: "Change" };
  return {
    title: result.data.headline,
    description: result.data.summary,
    alternates: { canonical: `/changes/${id}` },
  };
}

export default async function ChangePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const result = await loadPublishedChange(id);
  if (!result.ok) {
    return (
      <main id="main" className="mx-auto max-w-5xl px-6 py-12">
        <StatePanel title="Change unavailable">
          We could not load this change.
        </StatePanel>
      </main>
    );
  }
  if (!result.data) notFound();
  const event = result.data;
  const quotes = Array.isArray(event.quotes) ? event.quotes : [];

  return (
    <main id="main" className="mx-auto max-w-5xl px-6 py-12">
      <p className="font-sans text-sm text-muted-foreground">
        <Link href={`/companies/${event.slug}`} className="hover:underline">
          {event.name}
        </Link>
        <span className="mx-2">/</span>
        {event.publication_state === "corrected" ? "Corrected change" : "Change"}
      </p>
      <h1 className="mt-2 font-serif text-4xl tracking-tight">{event.headline}</h1>
      <p className="mt-3 font-mono text-xs text-muted-foreground">
        {event.materiality} ·{" "}
        <time dateTime={event.published_at}>
          {new Date(event.published_at).toLocaleString("en-US")}
        </time>
      </p>
      <p className="mt-6 max-w-2xl">{event.summary}</p>
      <h2 className="mt-10 font-serif text-xl">Evidence</h2>
      {quotes.length === 0 ? (
        <p className="mt-3 text-muted-foreground">
          We have not found quotes on this published change.
        </p>
      ) : (
        <ul className="mt-4 space-y-4">
          {quotes.map((quote) => (
            <li key={quote.text}>
              <figure className="border-l border-[var(--important)] pl-3">
                <blockquote className="text-sm italic text-muted-foreground">
                  “{quote.text}”
                </blockquote>
                {quote.section ? (
                  <figcaption className="mt-2 font-mono text-xs text-muted-foreground">
                    {quote.section}
                  </figcaption>
                ) : null}
              </figure>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
