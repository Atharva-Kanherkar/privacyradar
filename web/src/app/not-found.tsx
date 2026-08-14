import Link from "next/link";

export default function NotFound() {
  return (
    <main id="main" className="mx-auto max-w-5xl px-6 py-12">
      <h1 className="font-serif text-4xl tracking-tight">Not found</h1>
      <p className="mt-4 text-[var(--muted)]">
        That page is not in the public catalog. It may be unpublished, or the
        address may be wrong.
      </p>
      <p className="mt-6">
        <Link href="/companies" className="underline">
          Back to the catalog
        </Link>
      </p>
    </main>
  );
}
