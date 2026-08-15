import Link from "next/link";

export const dynamic = "force-dynamic";

export default async function CompanyRequestPage({
  searchParams,
}: {
  searchParams: Promise<{ status?: string }>;
}) {
  const { status } = await searchParams;
  const received = status === "received";
  const duplicate = status === "duplicate";

  return (
    <main id="main" className="mx-auto max-w-xl px-6 py-12">
      <p className="font-sans text-sm">
        <Link href="/companies" className="underline">
          Catalog
        </Link>
      </p>
      <h1 className="mt-2 font-serif text-4xl tracking-tight">Request a company</h1>
      <p className="mt-3 text-muted-foreground">
        A nomination is <strong>requested, not monitored</strong>. We do not
        fetch the URL you submit, and we do not promise a date.
      </p>
      {received ? (
        <p className="mt-6" role="status">
          We recorded your request. It is not monitored yet.
        </p>
      ) : null}
      {duplicate ? (
        <p className="mt-6" role="status">
          That website is already in the catalog or the request queue. It is
          still not a promise that we monitor it.
        </p>
      ) : null}
      <form action="/companies/request/submit" method="post" className="mt-8 space-y-4">
        <div>
          <label htmlFor="name" className="font-sans text-sm">
            Company name
          </label>
          <input
            id="name"
            name="name"
            required
            className="mt-1 min-h-11 w-full border border-border bg-card px-3"
          />
        </div>
        <div>
          <label htmlFor="website" className="font-sans text-sm">
            Official website
          </label>
          <input
            id="website"
            name="website"
            required
            placeholder="https://example.com"
            className="mt-1 min-h-11 w-full border border-border bg-card px-3"
          />
        </div>
        <div>
          <label htmlFor="category" className="font-sans text-sm">
            Category
          </label>
          <input
            id="category"
            name="category"
            defaultValue="consumer"
            className="mt-1 min-h-11 w-full border border-border bg-card px-3"
          />
        </div>
        <button
          type="submit"
          className="min-h-11 border border-foreground px-4 font-sans text-sm"
        >
          Submit request
        </button>
      </form>
    </main>
  );
}
