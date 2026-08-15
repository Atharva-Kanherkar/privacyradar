import { ChangeCard } from "@/components/ChangeCard";
import { StatePanel } from "@/components/StatePanel";
import { loadEvents } from "@/lib/db";

export const dynamic = "force-dynamic";

export default async function ChangesPage() {
  const events = await loadEvents(50);
  return (
    <main id="main" className="mx-auto max-w-5xl px-6 py-12">
      <h1 className="font-serif text-4xl tracking-tight">Changes</h1>
      <p className="mt-3 max-w-xl text-muted-foreground">
        Published material changes only. Review-pending and cosmetic events stay
        off this list.
      </p>
      {!events.ok ? (
        <StatePanel title="Changes unavailable">
          We could not load the change feed.
        </StatePanel>
      ) : events.data.length === 0 ? (
        <p className="mt-8 text-muted-foreground">No published material changes yet.</p>
      ) : (
        <ol className="mt-8 divide-y divide-border border-y border-border">
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
    </main>
  );
}
