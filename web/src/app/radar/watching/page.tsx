import { redirect } from "next/navigation";
import Link from "next/link";
import { WatchButton } from "@/components/WatchButton";
import { getSessionFromCookies } from "@/lib/session";
import { listWatchedCompanies } from "@/lib/watches";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export default async function WatchingPage() {
  const session = await getSessionFromCookies();
  if (!session?.user) {
    redirect("/login?next=/radar/watching");
  }
  const watching = await listWatchedCompanies(session.user.id);

  return (
    <main id="main" className="mx-auto max-w-3xl px-6 py-12">
      <p className="font-sans text-sm">
        <Link href="/radar" className="underline">
          My Radar
        </Link>
      </p>
      <h1 className="mt-2 font-serif text-4xl tracking-tight">Watching</h1>
      {watching.length === 0 ? (
        <p className="mt-6 text-muted-foreground">
          You are not watching any companies.{" "}
          <Link href="/companies" className="underline">
            Browse the catalog
          </Link>
          .
        </p>
      ) : (
        <ul className="mt-8 space-y-4">
          {watching.map((company) => (
            <li
              key={company.slug}
              className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-4"
            >
              <div>
                <Link href={`/companies/${company.slug}`} className="underline">
                  {company.name}
                </Link>
                <p className="font-sans text-sm text-muted-foreground">
                  {company.category}
                </p>
              </div>
              <WatchButton slug={company.slug} signedIn watching />
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
